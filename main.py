"""SentinelScrape CLI entrypoint.

Commands:
    scrape   Run a configured target, encrypt and store the results.
    export   Decrypt stored records and export them to CSV or JSON.
    targets  List configured targets.

Examples:
    python main.py scrape --target books_demo --pages 2
    python main.py export --target books_demo --format csv --out exports/books.csv
    python main.py targets
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml

from core.scraper_engine import Pagination, ScraperEngine, Target
from core.stealth_manager import StealthManager
from exporters.csv_exporter import export_csv
from exporters.json_exporter import export_json
from security.encryptor import AESGCMEncryptor, Encryptor
from security.key_vault import KeyVault
from storage.db_manager import DBManager

CONFIG_DIR = Path(__file__).parent / "config"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def build_targets(targets_cfg: dict[str, Any]) -> dict[str, Target]:
    targets: dict[str, Target] = {}
    for entry in targets_cfg.get("targets", []):
        pag = entry.get("pagination", {}) or {}
        targets[entry["name"]] = Target(
            name=entry["name"],
            url=entry["url"],
            selectors=entry["selectors"],
            item_selector=entry.get("item_selector"),
            pagination=Pagination(
                type=pag.get("type", "none"),
                selector=pag.get("selector"),
                max_pages=int(pag.get("max_pages", 1)),
            ),
        )
    return targets


def build_encryptor(settings: dict[str, Any]) -> Any:
    enc_cfg = settings.get("encryption", {})
    algo = enc_cfg.get("algorithm", "fernet")
    key_path = enc_cfg.get("key_path", ".secrets/key.key")
    if algo == "aes256gcm":
        # A separate 32-byte key file for the GCM engine.
        gcm_path = Path(key_path).with_suffix(".gcm.key")
        if gcm_path.exists():
            key = gcm_path.read_bytes()
        else:
            key = AESGCMEncryptor.generate_key()
            gcm_path.parent.mkdir(parents=True, exist_ok=True)
            gcm_path.write_bytes(key)
        return AESGCMEncryptor(key)
    key = KeyVault(key_path).load_or_create()
    return Encryptor(key)


def cmd_scrape(args: argparse.Namespace, settings: dict[str, Any], targets: dict[str, Target]) -> int:
    if args.target not in targets:
        print(f"unknown target: {args.target}", file=sys.stderr)
        return 2
    target = targets[args.target]
    if args.pages is not None:
        target.pagination.max_pages = args.pages

    stealth_cfg = settings.get("stealth", {})
    stealth = StealthManager(
        proxies=settings.get("proxies", []) if stealth_cfg.get("proxy_rotation", True) else [],
        jitter_min_ms=stealth_cfg.get("jitter_min_ms", 800),
        jitter_max_ms=stealth_cfg.get("jitter_max_ms", 3500),
    )
    engine = ScraperEngine(
        stealth,
        respect_robots=stealth_cfg.get("respect_robots", True),
        max_retries=stealth_cfg.get("max_retries", 3),
    )

    print(f"[SentinelScrape] scraping target '{target.name}' ...")
    records = engine.scrape(target)

    encryptor = build_encryptor(settings)
    db_path = settings.get("database", {}).get("path", "./data/sentinel.db")
    session_id = uuid.uuid4().hex[:12]
    with DBManager(db_path, encryptor) as db:
        inserted, duplicates = db.insert_many(session_id, target.url, records)
        total = db.count()

    print(
        f"[SentinelScrape] session {session_id}: {len(records)} scraped | "
        f"{inserted} stored | {duplicates} duplicates | {total} total in db"
    )
    return 0


def cmd_export(args: argparse.Namespace, settings: dict[str, Any], _targets: dict[str, Target]) -> int:
    encryptor = build_encryptor(settings)
    db_path = settings.get("database", {}).get("path", "./data/sentinel.db")
    with DBManager(db_path, encryptor) as db:
        records = db.fetch_decrypted()

    if args.format == "csv":
        n = export_csv(records, args.out)
    else:
        n = export_json(records, args.out)
    print(f"[SentinelScrape] exported {n} records -> {args.out}")
    return 0


def cmd_targets(_args: argparse.Namespace, _settings: dict[str, Any], targets: dict[str, Target]) -> int:
    if not targets:
        print("no targets configured")
        return 0
    for name, target in targets.items():
        print(f"- {name}: {target.url} (max_pages={target.pagination.max_pages})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinelscrape", description="Stealth scraper & market intelligence pipeline")
    parser.add_argument("--settings", default=str(CONFIG_DIR / "settings.yaml"))
    parser.add_argument("--targets-file", default=str(CONFIG_DIR / "targets.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_scrape = sub.add_parser("scrape", help="run a target and store encrypted results")
    p_scrape.add_argument("--target", required=True)
    p_scrape.add_argument("--pages", type=int, default=None)
    p_scrape.set_defaults(func=cmd_scrape)

    p_export = sub.add_parser("export", help="decrypt and export stored records")
    p_export.add_argument("--format", choices=["csv", "json"], default="csv")
    p_export.add_argument("--out", required=True)
    p_export.set_defaults(func=cmd_export)

    p_targets = sub.add_parser("targets", help="list configured targets")
    p_targets.set_defaults(func=cmd_targets)

    args = parser.parse_args(argv)
    settings = load_yaml(Path(args.settings))
    targets = build_targets(load_yaml(Path(args.targets_file)))
    return args.func(args, settings, targets)


if __name__ == "__main__":
    raise SystemExit(main())
