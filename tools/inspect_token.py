#!/usr/bin/env python3
"""Inspect a BSC token before trading it.

Run this ON YOUR SERVER (where the BSC RPC is reachable). It prints the token
symbol/decimals, finds a price route against WBNB/USDT, does a quick
buy-then-sell round-trip simulation to flag possible honeypots, and suggests a
grid band around the current price.

Usage:
    python tools/inspect_token.py 0xTOKEN_ADDRESS
    BSC_RPC_URL=https://your-rpc python tools/inspect_token.py 0xTOKEN
"""

import os
import sys

# Make the project root importable when run as `python tools/inspect_token.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

from bot.constants import ERC20_ABI, ROUTER_ABI, PANCAKE_ROUTER, WBNB

USDT = "0x55d398326f99059fF775485246999027B3197955"   # BSC-USD (USDT)
OFFICIAL_BTCB = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python tools/inspect_token.py 0xTOKEN_ADDRESS")
        return 1

    token = Web3.to_checksum_address(sys.argv[1])
    rpc = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
    if not w3.is_connected():
        print(f"Cannot connect to RPC: {rpc}")
        return 1

    wbnb = Web3.to_checksum_address(WBNB)
    usdt = Web3.to_checksum_address(USDT)
    router = w3.eth.contract(address=Web3.to_checksum_address(PANCAKE_ROUTER),
                             abi=ROUTER_ABI)
    erc = w3.eth.contract(address=token, abi=ERC20_ABI)

    # --- identity ---------------------------------------------------------
    try:
        sym = erc.functions.symbol().call()
        dec = erc.functions.decimals().call()
    except Exception as exc:
        print(f"Could not read token (is it an ERC-20?): {exc}")
        return 1

    print(f"Token   : {token}")
    print(f"Symbol  : {sym}")
    print(f"Decimals: {dec}")
    if token.lower() == OFFICIAL_BTCB.lower():
        print("Note    : this IS the official Binance-Peg BTCB. ✅")
    else:
        print("Note    : this is NOT the official BTCB "
              f"({OFFICIAL_BTCB}). Verify it is legit. ⚠️")

    one = 10 ** dec

    # --- price route ------------------------------------------------------
    def quote(path, out_dec):
        try:
            amts = router.functions.getAmountsOut(one, path).call()
            return amts[-1] / (10 ** out_dec)
        except Exception:
            return None

    price_wbnb = quote([token, wbnb], 18)
    price_usdt = quote([token, wbnb, usdt], 18) if price_wbnb else None
    direct_usdt = quote([token, usdt], 18)

    print("\n--- Price ---")
    if price_wbnb:
        print(f"1 {sym} = {price_wbnb:.10g} WBNB")
    if direct_usdt:
        print(f"1 {sym} = {direct_usdt:.6g} USDT (direct pair)")
    elif price_usdt:
        print(f"1 {sym} = {price_usdt:.6g} USDT (via WBNB)")
    if not price_wbnb and not direct_usdt:
        print("No WBNB/USDT route found — illiquid or non-standard. Do NOT trade. ⚠️")
        return 1

    # --- honeypot smoke test (read-only) ----------------------------------
    # Simulate buying ~0.01 WBNB of the token, then selling it straight back.
    print("\n--- Round-trip check (buy then sell 0.01 WBNB worth) ---")
    test_in = w3.to_wei(0.01, "ether")
    try:
        got = router.functions.getAmountsOut(test_in, [wbnb, token]).call()[-1]
        back = router.functions.getAmountsOut(got, [token, wbnb]).call()[-1]
        kept = back / test_in
        print(f"0.01 WBNB -> {got/one:.8g} {sym} -> {back/1e18:.8g} WBNB "
              f"({kept*100:.1f}% kept)")
        if kept < 0.80:
            print("High round-trip loss — likely heavy tax or honeypot. ⚠️")
        else:
            print("Round-trip looks reasonable (quote-only; not a sell guarantee).")
    except Exception as exc:
        print(f"Could not simulate sell route — suspicious: {exc} ⚠️")

    # --- suggested grid ---------------------------------------------------
    p = price_wbnb if price_wbnb else None
    if p:
        lo, hi = p * 0.85, p * 1.15  # +/-15% band around current price
        print("\n--- Suggested grid (quote = WBNB) ---")
        print(f"lower_price: {lo:.10g}")
        print(f"upper_price: {hi:.10g}")
        print("levels: 11")
        print("Adjust the band to the token's real volatility before going live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
