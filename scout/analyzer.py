"""LLM-анализ собранных вакансий через Claude (саммари и Q&A)."""

import anthropic

from scout import config

SYSTEM_PROMPT = (
    "Ты — аналитик рынка удалённых заказов и вакансий в сфере ИИ и автоматизации. "
    "Отвечай строго на основе переданного списка вакансий. "
    "Если данных не хватает — честно скажи об этом. "
    "Пиши кратко, структурно, по-деловому, на русском языке."
)


def _build_context(vacancies: list[dict], limit: int = 60) -> str:
    lines = []
    for i, v in enumerate(vacancies[:limit], 1):
        salary = f" | з/п: {v.get('salary')}" if v.get("salary") else ""
        lines.append(
            f"{i}. {v.get('name')} — {v.get('employer')} ({v.get('area')})"
            f"{salary} | {v.get('job_type')} | теги: {v.get('tags')}\n"
            f"   Требования: {v.get('requirement', '')[:200]}\n"
            f"   Ссылка: {v.get('url')}"
        )
    return "\n".join(lines)


def _ask_claude(user_content: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "Не задан ANTHROPIC_API_KEY. Скопируй .env.example в .env и впиши свой ключ."
        )
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def summarize(vacancies: list[dict]) -> str:
    context = _build_context(vacancies)
    prompt = (
        f"Вот {len(vacancies)} собранных вакансий:\n\n{context}\n\n"
        "Сделай сводку по рынку:\n"
        "1. Сколько всего и какие направления преобладают.\n"
        "2. Где указаны — диапазоны зарплат.\n"
        "3. Какие навыки и инструменты встречаются чаще всего.\n"
        "4. 3–5 вакансий, наиболее подходящих фрилансеру по ИИ-автоматизации, "
        "промптингу и Telegram-ботам — с краткой причиной."
    )
    return _ask_claude(prompt)


def answer(vacancies: list[dict], question: str) -> str:
    context = _build_context(vacancies)
    prompt = (
        f"Вот {len(vacancies)} собранных вакансий:\n\n{context}\n\n"
        f"Вопрос пользователя: {question}\n\n"
        "Ответь по данным выше. Где уместно — приводи ссылки на вакансии."
    )
    return _ask_claude(prompt)
