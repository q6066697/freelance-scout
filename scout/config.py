"""Настройки разведчика заказов.

Источник данных переключается: по умолчанию Remotive (международные
удалённые вакансии, работает из-под VPN), опционально hh.ru.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Источник данных ---
# "hh"       — hh.ru, рынок РФ (нужен доступ к рунету: без VPN или с РФ-нодой)
# "trudvsem" — «Работа России» (trudvsem.ru), гос-портал РФ, открытый API без ключа
# "remotive" — международные удалёнки, англоязычные, доступен из-под VPN
DEFAULT_SOURCE = os.getenv("SOURCE", "hh")

HH_API_URL = "https://api.hh.ru/vacancies"
TRUDVSEM_API_URL = "https://opendata.trudvsem.ru/api/v1/vacancies"
REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

# Регион для hh.ru: 113=Россия, 1=Москва, 2=СПб. Справочник: https://api.hh.ru/areas
DEFAULT_AREA = os.getenv("HH_AREA", "113")

# Сколько вакансий тянуть на один запрос.
DEFAULT_LIMIT = int(os.getenv("FETCH_LIMIT", "50"))

# Поисковые запросы по умолчанию — свои под каждый источник.
# Remotive — англоязычная международная площадка: точнее ловит английские термины.
DEFAULT_QUERIES_REMOTIVE = [
    "prompt engineer",
    "AI engineer",
    "machine learning engineer",
    "AI automation",
    "python developer",
    "AI agent",
    "chatbot",
]

# hh.ru — рунет: лучше работают русские формулировки.
DEFAULT_QUERIES_HH = [
    "промпт инженер",
    "AI разработчик",
    "автоматизация",
    "Telegram бот",
    "n8n",
    "python разработчик",
]

# «Работа России» — русские запросы, рынок РФ целиком.
DEFAULT_QUERIES_TRUDVSEM = [
    "разработчик python",
    "автоматизация",
    "искусственный интеллект",
    "чат-бот",
    "аналитик данных",
]


def queries_for(source: str) -> list[str]:
    """Возвращает дефолтный набор запросов под выбранный источник."""
    return {
        "hh": DEFAULT_QUERIES_HH,
        "trudvsem": DEFAULT_QUERIES_TRUDVSEM,
        "remotive": DEFAULT_QUERIES_REMOTIVE,
    }.get(source, DEFAULT_QUERIES_REMOTIVE)

# --- LLM-анализ ---
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# --- Хранилище ---
DATA_DIR = os.getenv("DATA_DIR", "data")
CSV_PATH = os.path.join(DATA_DIR, "vacancies.csv")
JSON_PATH = os.path.join(DATA_DIR, "vacancies.json")
