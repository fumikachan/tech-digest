import argparse
import logging
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from tech_digest import storage
from tech_digest.archive import DailyDigest, export_day, load_days
from tech_digest.config import Settings, today_jst
from tech_digest.render import render_markdown
from tech_digest.site import build_site
from tech_digest.sources import SOURCES

logger = logging.getLogger("tech_digest")

USER_AGENT = "tech-digest/0.1"
DEFAULT_LIMIT = 20


def fetch(settings: Settings, digest_date: date) -> list[str]:
    """全取得元から記事を集めて保存する。失敗した取得元の名前を返す。

    1 つの取得元が失敗しても、ほかの取得元は続けて処理する。
    """
    failed = []
    with (
        httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as client,
        closing(storage.connect(settings)) as db,
    ):
        for source in SOURCES:
            try:
                articles = source.fetch(client, digest_date, settings)
            except (httpx.HTTPError, ValueError) as e:
                logger.error("%s: 取得に失敗しました: %s", source.title, e)
                failed.append(source.name)
                continue
            db.save(articles, digest_date, now=datetime.now(UTC))
            logger.info("%s: %d 件を保存しました", source.title, len(articles))
    return failed


def build(settings: Settings, digest_date: date, limit: int) -> Path:
    with closing(storage.connect(settings)) as db:
        articles = db.load(digest_date)
    markdown = render_markdown(digest_date, articles, SOURCES, limit)

    path = settings.output_dir / f"{digest_date.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    logger.info("ダイジェストを出力しました: %s", path)
    return path


def export(settings: Settings, digest_date: date, out_dir: Path) -> Path:
    with closing(storage.connect(settings)) as db:
        articles = db.load(digest_date)
    path = export_day(DailyDigest(digest_date, articles), out_dir)
    logger.info("%d 件を書き出しました: %s", len(articles), path)
    return path


def site(data_dir: Path, out_dir: Path) -> None:
    days = load_days(data_dir)
    build_site(days, out_dir)
    logger.info("サイトを作りました: %s（%d 日分）", out_dir, len(days))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tech-digest", description="技術ブログの新着記事を集めてダイジェストにまとめる"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="記事を取得して DB に保存する（今日のダイジェスト分）")
    build_parser = sub.add_parser("build", help="DB からダイジェストの Markdown を生成する")
    build_parser.add_argument(
        "--date", type=date.fromisoformat, help="ダイジェストの日付 YYYY-MM-DD（省略時は今日）"
    )
    run_parser = sub.add_parser("run", help="fetch と build を続けて実行する")
    for p in (build_parser, run_parser):
        p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="取得元ごとの表示件数")
    export_parser = sub.add_parser("export", help="DB から 1 日分の記事を JSON に書き出す")
    export_parser.add_argument(
        "--date", type=date.fromisoformat, help="ダイジェストの日付 YYYY-MM-DD（省略時は今日）"
    )
    export_parser.add_argument("--out", type=Path, default=Path("archive"), help="出力先")
    site_parser = sub.add_parser("site", help="JSON の記録から静的サイトを作る")
    site_parser.add_argument("--data", type=Path, default=Path("archive"), help="JSON の置き場所")
    site_parser.add_argument("--out", type=Path, default=Path("site"), help="サイトの出力先")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()

    if args.command == "fetch":
        return 1 if fetch(settings, today_jst()) else 0
    if args.command == "build":
        build(settings, args.date or today_jst(), args.limit)
        return 0
    if args.command == "export":
        export(settings, args.date or today_jst(), args.out)
        return 0
    if args.command == "site":
        site(args.data, args.out)
        return 0

    digest_date = today_jst()
    failed = fetch(settings, digest_date)
    build(settings, digest_date, args.limit)
    return 1 if failed else 0
