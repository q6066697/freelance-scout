"""Сохранение и загрузка собранных вакансий в CSV и JSON."""

import os
import csv
import json

from scout import config

FIELDS = [
    "id", "name", "employer", "area", "salary",
    "job_type", "tags", "requirement",
    "published_at", "url", "source", "matched_query",
]


def save(vacancies: list[dict]) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(vacancies)
    with open(config.JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(vacancies, f, ensure_ascii=False, indent=2)


def load() -> list[dict]:
    if not os.path.exists(config.JSON_PATH):
        return []
    with open(config.JSON_PATH, encoding="utf-8") as f:
        return json.load(f)
