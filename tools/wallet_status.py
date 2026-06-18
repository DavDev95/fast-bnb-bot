#!/usr/bin/env python3
"""Show which wallet the bot will use and its balances — WITHOUT printing the key.

Reads PRIVATE_KEY/BSC_RPC_URL from .env and the token from the given config.
Run on your server:

    .venv/bin/python tools/wallet_status.py -c config.btc.yaml
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

from bot.config import load_config
from bot.chain import Chain


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default="config.btc.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not cfg.private_key:
        print("No PRIVATE_KEY found in .env — nothing to check.")
        return 1

    chain = Chain(cfg)
    addr = chain.account.address
    bnb = chain.native_balance()
    quote_bal = chain.quote_balance()
    base_bal = chain.balance(chain.base, chain.base_decimals)

    print(f"Bot wallet address : {addr}")
    if chain.native_quote:
        print(f"  BNB (gas + buys) : {bnb:.6f} BNB   (native, used to buy)")
    else:
        print(f"  BNB (for gas)    : {bnb:.6f} BNB")
        print(f"  {cfg.quote.symbol:<14} : {quote_bal:.6f}   (used to buy)")
    print(f"  {cfg.base.symbol:<14} : {base_bal:.6f}   (the token traded)")

    print("\nChecklist:")
    print(f"  - This address ({addr}) is the one you funded?  <- verify in your wallet")
    print(f"  - BNB > 0 for gas? {'YES' if bnb > 0 else 'NO  <-- add a little BNB'}")
    print(f"  - Funds to trade ({cfg.quote.symbol})? "
          f"{'YES' if quote_bal > 0 else 'NO  <-- add some ' + cfg.quote.symbol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
