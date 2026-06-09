"""ИИ-разведчик фриланс-заказов — командный интерфейс.

Команды:
  python main.py fetch                 собрать вакансии (источник hh по умолчанию, рынок РФ)
  python main.py fetch -s trudvsem     собрать с «Работы России» (РФ, запасной вариант)
  python main.py fetch -s remotive     собрать международные удалёнки (англоязычные)
  python main.py fetch -q "n8n"        собрать по своим запросам
  python main.py list                  показать собранные вакансии таблицей
  python main.py summary               сводка по рынку (Claude)
  python main.py ask "вопрос..."       задать вопрос по собранным данным (Claude)
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import argparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scout import fetcher, storage, analyzer, config

console = Console()


def cmd_fetch(args):
    source = args.source or config.DEFAULT_SOURCE
    queries = args.query or config.queries_for(source)
    console.print(f"[bold cyan]Собираю вакансии[/] из '{source}' по {len(queries)} запросам...")
    vacancies = fetcher.fetch_all(queries=queries, source=source, limit=args.limit)
    storage.save(vacancies)
    console.print(
        f"\n[bold green]Готово.[/] Собрано [bold]{len(vacancies)}[/] вакансий.\n"
        f"Сохранено в {config.CSV_PATH} и {config.JSON_PATH}"
    )


def cmd_list(args):
    vacancies = storage.load()
    if not vacancies:
        console.print("[yellow]Нет данных. Сначала запусти: python main.py fetch[/]")
        return

    table = Table(title=f"Собрано вакансий: {len(vacancies)}", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Вакансия", style="bold")
    table.add_column("Компания")
    table.add_column("Локация")
    table.add_column("З/п", justify="right")
    table.add_column("Источник", style="dim")

    for i, v in enumerate(vacancies[: args.limit], 1):
        table.add_row(
            str(i), v.get("name", ""), v.get("employer", ""),
            v.get("area", ""), v.get("salary") or "—", v.get("source", ""),
        )

    console.print(table)


def cmd_summary(args):
    vacancies = storage.load()
    if not vacancies:
        console.print("[yellow]Нет данных. Сначала запусти: python main.py fetch[/]")
        return
    console.print("[cyan]Анализирую рынок через Claude...[/]")
    result = analyzer.summarize(vacancies)
    console.print(Panel(result, title="Сводка по рынку", border_style="green"))


def cmd_ask(args):
    vacancies = storage.load()
    if not vacancies:
        console.print("[yellow]Нет данных. Сначала запусти: python main.py fetch[/]")
        return
    console.print(f"[cyan]Думаю над вопросом:[/] {args.question}")
    result = analyzer.answer(vacancies, args.question)
    console.print(Panel(result, title="Ответ", border_style="blue"))


def build_parser():
    parser = argparse.ArgumentParser(description="ИИ-разведчик фриланс-заказов")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="собрать вакансии")
    p_fetch.add_argument("-q", "--query", action="append", help="поисковый запрос (можно несколько)")
    p_fetch.add_argument("-s", "--source", choices=["hh", "trudvsem", "remotive"], help="источник данных (по умолчанию hh)")
    p_fetch.add_argument("-l", "--limit", type=int, help="сколько вакансий тянуть на запрос")
    p_fetch.set_defaults(func=cmd_fetch)

    p_list = sub.add_parser("list", help="показать собранные вакансии")
    p_list.add_argument("-l", "--limit", type=int, default=20, help="сколько строк показать")
    p_list.set_defaults(func=cmd_list)

    p_sum = sub.add_parser("summary", help="сводка по рынку через Claude")
    p_sum.set_defaults(func=cmd_summary)

    p_ask = sub.add_parser("ask", help="вопрос по собранным данным через Claude")
    p_ask.add_argument("question", help="текст вопроса")
    p_ask.set_defaults(func=cmd_ask)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
