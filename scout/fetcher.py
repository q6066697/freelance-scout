"""Сбор вакансий из сменных источников.

Поддержаны два источника, оба без ключа:
  - remotive : международные удалённые вакансии (работает из-под VPN)
  - hh       : hh.ru (нужен доступ к рунету)

Оба приводятся к единой схеме полей, на которую опираются storage и analyzer.
"""

import re
import time
import html
import requests

from scout import config

HEADERS = {"User-Agent": "freelance-scout/1.0 (https://n8nmind.site)"}


def _strip_html(text: str) -> str:
    if not text:
        return ""
    # hh.ru подсвечивает совпадения inline-тегами — убираем без пробела
    text = text.replace("<highlighttext>", "").replace("</highlighttext>", "")
    # остальные теги (блочные, как у Remotive) заменяем пробелом
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# --- Remotive ---------------------------------------------------------------

def _normalize_remotive(j: dict) -> dict:
    tags = j.get("tags") or []
    return {
        "id": f"remotive-{j.get('id', '')}",
        "name": j.get("title", ""),
        "employer": j.get("company_name", ""),
        "area": j.get("candidate_required_location", ""),
        "salary": j.get("salary", "") or "",
        "job_type": j.get("job_type", ""),
        "tags": ", ".join(tags) if isinstance(tags, list) else str(tags),
        "requirement": _strip_html(j.get("description", ""))[:300],
        "published_at": j.get("publication_date", ""),
        "url": j.get("url", ""),
        "source": "remotive",
    }


def fetch_remotive(text: str, limit: int = None) -> list[dict]:
    params = {"search": text, "limit": limit or config.DEFAULT_LIMIT}
    resp = requests.get(config.REMOTIVE_API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    return [_normalize_remotive(j) for j in jobs]


# --- «Работа России» (trudvsem.ru) -----------------------------------------
# ВНИМАНИЕ: схема ответа не проверялась вживую (песочница не имеет доступа).
# Поля взяты по документации открытого API и читаются защитно (.get).
# Если после первого реального запроса какие-то поля пустые — сверь имена
# с реальным JSON (data["results"]["vacancies"][0]["vacancy"]) и поправь тут.

def _normalize_trudvsem(wrap: dict) -> dict:
    v = wrap.get("vacancy") or wrap or {}
    region = v.get("region") or {}
    company = v.get("company") or {}
    req = v.get("requirement") or {}
    salary_text = v.get("salary") or ""
    if not salary_text and (v.get("salary_min") or v.get("salary_max")):
        salary_text = (
            f"{v.get('salary_min') or ''}–{v.get('salary_max') or ''} "
            f"{v.get('currency') or 'RUB'}"
        ).strip()
    experience = req.get("experience")
    return {
        "id": f"trudvsem-{v.get('id', '')}",
        "name": v.get("job-name", ""),
        "employer": company.get("name", ""),
        "area": region.get("name", ""),
        "salary": salary_text,
        "job_type": v.get("employment", "") or v.get("schedule", ""),
        "tags": str(experience) if experience not in (None, "") else "",
        "requirement": _strip_html(v.get("duty", ""))[:300],
        "published_at": v.get("creation-date", ""),
        "url": v.get("vac_url", ""),
        "source": "trudvsem",
    }


def fetch_trudvsem(text: str, limit: int = None) -> list[dict]:
    params = {"text": text, "limit": min(limit or config.DEFAULT_LIMIT, 100), "offset": 0}
    resp = requests.get(config.TRUDVSEM_API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    vacancies = (data.get("results") or {}).get("vacancies") or []
    return [_normalize_trudvsem(w) for w in vacancies]


# --- hh.ru ------------------------------------------------------------------

def _normalize_hh(item: dict) -> dict:
    salary = item.get("salary") or {}
    salary_text = ""
    if salary and (salary.get("from") or salary.get("to")):
        salary_text = f"{salary.get('from') or ''}–{salary.get('to') or ''} {salary.get('currency') or ''}".strip()
    snippet = item.get("snippet") or {}
    return {
        "id": f"hh-{item.get('id', '')}",
        "name": item.get("name", ""),
        "employer": (item.get("employer") or {}).get("name", ""),
        "area": (item.get("area") or {}).get("name", ""),
        "salary": salary_text,
        "job_type": (item.get("schedule") or {}).get("name", ""),
        "tags": (item.get("experience") or {}).get("name", ""),
        "requirement": _strip_html(snippet.get("requirement", "")),
        "published_at": item.get("published_at", ""),
        "url": item.get("alternate_url", ""),
        "source": "hh",
    }


def fetch_hh(text: str, limit: int = None) -> list[dict]:
    params = {
        "text": text,
        "area": config.DEFAULT_AREA,
        "per_page": min(limit or config.DEFAULT_LIMIT, 100),
        "order_by": "publication_time",
    }
    resp = requests.get(config.HH_API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return [_normalize_hh(i) for i in resp.json().get("items", [])]


# --- Диспетчер --------------------------------------------------------------

SOURCES = {
    "hh": fetch_hh,
    "trudvsem": fetch_trudvsem,
    "remotive": fetch_remotive,
}


def fetch_all(queries: list[str] = None, source: str = None,
              limit: int = None) -> list[dict]:
    """Проходит по всем запросам выбранного источника, дедуплицирует по id."""
    source = source or config.DEFAULT_SOURCE
    queries = queries or config.queries_for(source)
    if source not in SOURCES:
        raise ValueError(f"Неизвестный источник '{source}'. Доступно: {list(SOURCES)}")
    fetch_one = SOURCES[source]

    seen, result = set(), []
    for q in queries:
        try:
            items = fetch_one(q, limit=limit)
        except requests.RequestException as e:
            print(f"  ! Ошибка по запросу '{q}': {e}")
            continue
        added = 0
        for item in items:
            if item["id"] and item["id"] not in seen:
                seen.add(item["id"])
                item["matched_query"] = q
                result.append(item)
                added += 1
        print(f"  + '{q}': найдено {len(items)}, новых {added}")
        time.sleep(0.3)
    return result
