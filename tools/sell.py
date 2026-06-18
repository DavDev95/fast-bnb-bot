#!/usr/bin/env python3
"""Sell base tokens back to BNB — in small chunks to limit slippage.

Recovery tool: if churn left tokens unsold, this converts them back to BNB.

Examples:
    .venv/bin/python tools/sell.py -c config.btc.yaml                # sell ALL
    .venv/bin/python tools/sell.py -c config.btc.yaml --keep 1383.41 # keep some
    .venv/bin/python tools/sell.py -c config.btc.yaml --chunk 0.05   # 0.05 BNB/sell
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config
from bot.chain import Chain


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default="config.btc.yaml")
    ap.add_argument("--keep", type=float, default=0.0,
                    help="amount of base tokens to keep (not sell)")
    ap.add_argument("--chunk", type=float, default=0.05,
                    help="approx BNB value to sell per swap (smaller = less slippage)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not cfg.private_key:
        print("No PRIVATE_KEY in .env — cannot sell.")
        return 1

    chain = Chain(cfg)
    dec = chain.base_decimals
    keep_raw = int(args.keep * (10 ** dec))
    balance = chain.balance_raw(chain.base)
    to_sell = balance - keep_raw

    if to_sell <= 0:
        print(f"Nothing to sell (balance {balance/10**dec:.4f}, keep {args.keep}).")
        return 0

    price = chain.get_price()
    chunk_raw = max(1, int((args.chunk / price) * (10 ** dec)))
    print(f"Selling {to_sell/10**dec:.4f} {cfg.base.symbol} for BNB, "
          f"in chunks of ~{args.chunk} BNB ...")

    remaining = to_sell
    while remaining > 0:
        n = min(chunk_raw, remaining)
        try:
            tx = chain.swap(chain.base, chain.quote, n)
            print(f"  sold {n/10**dec:.4f} {cfg.base.symbol}  tx {tx}")
        except Exception as exc:
            print(f"  chunk failed ({exc}); stopping. Re-run to continue / lower --chunk.")
            break
        remaining -= n

    bnb = chain.native_balance()
    print(f"Done. BNB now: {bnb:.6f} | {cfg.base.symbol} left: "
          f"{chain.balance(chain.base, dec):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
