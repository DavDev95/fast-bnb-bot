#!/usr/bin/env python3
"""Entry point for the Fast BNB grid-trading bot."""

import argparse
import sys

from bot.bot import GridBot
from bot.config import load_config
from bot.logger import get_logger

log = get_logger()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fast BNB grid-trading bot")
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="path to the YAML config"
    )
    parser.add_argument(
        "--live", action="store_true",
        help="force live trading (overrides dry_run; still requires PRIVATE_KEY)",
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        log.error("Config '%s' not found. Copy config.example.yaml first.", args.config)
        return 1
    except Exception as exc:
        log.error("Invalid config: %s", exc)
        return 1

    if args.live:
        if not cfg.private_key:
            log.error("--live requires PRIVATE_KEY in your .env")
            return 1
        cfg.dry_run = False

    if not cfg.dry_run:
        log.warning("LIVE MODE — real funds at risk. Ctrl+C within 5s to abort.")
        import time
        time.sleep(5)

    try:
        GridBot(cfg).run()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
