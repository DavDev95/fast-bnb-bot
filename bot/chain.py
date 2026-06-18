"""BSC connection + PancakeSwap price reads and swap execution."""

import time
from typing import List, Optional

from web3 import Web3

from .constants import ERC20_ABI, PANCAKE_ROUTER, ROUTER_ABI, WBNB
from .config import Config
from .logger import get_logger

log = get_logger()


class Chain:
    """Wraps a web3 connection to BSC and the PancakeSwap router."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.w3 = Web3(Web3.HTTPProvider(cfg.rpc_url, request_kwargs={"timeout": 10}))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to BSC RPC at {cfg.rpc_url}")

        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(PANCAKE_ROUTER), abi=ROUTER_ABI
        )

        self.base = Web3.to_checksum_address(cfg.base.address)
        self.quote = Web3.to_checksum_address(cfg.quote.address)
        self.base_decimals = self._decimals(self.base)
        self.quote_decimals = self._decimals(self.quote)

        # When the quote token is WBNB we trade with NATIVE BNB directly
        # (no wrapping needed): pay BNB on buys, receive BNB on sells.
        self.native_quote = self.quote == Web3.to_checksum_address(WBNB)

        self.account = None
        if cfg.private_key:
            self.account = self.w3.eth.account.from_key(cfg.private_key)
            log.info("Wallet loaded: %s", self.account.address)

    # --- token helpers ----------------------------------------------------
    def _erc20(self, address: str):
        return self.w3.eth.contract(address=address, abi=ERC20_ABI)

    def _decimals(self, address: str) -> int:
        return self._erc20(address).functions.decimals().call()

    def balance(self, token: str, decimals: int) -> float:
        if not self.account:
            return 0.0
        return self.balance_raw(token) / (10 ** decimals)

    def balance_raw(self, token: str) -> int:
        """Raw on-chain token balance (integer) — exact, no float rounding."""
        if not self.account:
            return 0
        return self._erc20(token).functions.balanceOf(self.account.address).call()

    def native_balance(self) -> float:
        """Native BNB balance of the bot wallet."""
        if not self.account:
            return 0.0
        return self.w3.eth.get_balance(self.account.address) / 1e18

    def quote_balance(self) -> float:
        """How much 'quote' the wallet holds — native BNB if trading natively."""
        if self.native_quote:
            return self.native_balance()
        return self.balance(self.quote, self.quote_decimals)

    # --- price ------------------------------------------------------------
    def get_price(self) -> float:
        """Quote amount received for selling 1 base — i.e. quote per base."""
        one_base = 10 ** self.base_decimals
        path = self._path(self.base, self.quote)
        amounts = self.router.functions.getAmountsOut(one_base, path).call()
        out = amounts[-1]
        return out / (10 ** self.quote_decimals)

    def _path(self, src: str, dst: str) -> List[str]:
        """Swap path, routing through WBNB when neither side is WBNB."""
        wbnb = Web3.to_checksum_address(WBNB)
        if src == wbnb or dst == wbnb:
            return [src, dst]
        return [src, wbnb, dst]

    # --- swaps ------------------------------------------------------------
    def _min_out(self, amount_out: int) -> int:
        return amount_out * (10_000 - self.cfg.execution.slippage_bps) // 10_000

    def _gas_params(self) -> dict:
        params = {
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": self.cfg.execution.max_gas_limit,
        }
        gp = self.cfg.execution.gas_price_gwei
        params["gasPrice"] = (
            self.w3.to_wei(gp, "gwei") if gp is not None else self.w3.eth.gas_price
        )
        return params

    def ensure_allowance(self, token: str, amount: int) -> None:
        """Approve the router to spend `token` if the current allowance is short."""
        erc20 = self._erc20(token)
        current = erc20.functions.allowance(
            self.account.address, self.router.address
        ).call()
        if current >= amount:
            return
        log.info("Approving router to spend %s ...", token)
        tx = erc20.functions.approve(self.router.address, 2 ** 256 - 1).build_transaction(
            self._gas_params()
        )
        self._sign_send(tx)

    def swap(self, src: str, dst: str, amount_in_raw: int) -> Optional[str]:
        """Swap `amount_in_raw` of src for dst. Returns the tx hash hex.

        When trading natively (quote == WBNB), buys spend native BNB and sells
        receive native BNB, so no wrapping is ever needed.
        """
        wbnb = Web3.to_checksum_address(WBNB)
        path = self._path(src, dst)
        amounts = self.router.functions.getAmountsOut(amount_in_raw, path).call()
        min_out = self._min_out(amounts[-1])
        deadline = int(time.time()) + self.cfg.execution.deadline_sec
        to = self.account.address

        # BUY token with native BNB.
        if self.native_quote and src == wbnb:
            fn = self.router.functions.swapExactETHForTokens(
                min_out, path, to, deadline
            )
            params = self._gas_params()
            params["value"] = amount_in_raw
            return self._sign_send(fn.build_transaction(params))

        # SELL token for native BNB.
        if self.native_quote and dst == wbnb:
            self.ensure_allowance(src, amount_in_raw)
            fn = self.router.functions.swapExactTokensForETH(
                amount_in_raw, min_out, path, to, deadline
            )
            return self._sign_send(fn.build_transaction(self._gas_params()))

        # Plain token-for-token (non-native quote).
        self.ensure_allowance(src, amount_in_raw)
        fn = self.router.functions.swapExactTokensForTokens(
            amount_in_raw, min_out, path, to, deadline
        )
        return self._sign_send(fn.build_transaction(self._gas_params()))

    def _sign_send(self, tx: dict) -> str:
        signed = self.w3.eth.account.sign_transaction(tx, self.cfg.private_key)
        # eth-account renamed this attribute across versions; support both.
        raw = getattr(signed, "raw_transaction", None)
        if raw is None:
            raw = signed.rawTransaction
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        h = tx_hash.hex()
        log.info("Sent tx %s — waiting for receipt ...", h)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise RuntimeError(f"Transaction reverted: {h}")
        return h

    def to_raw(self, amount: float, decimals: int) -> int:
        return int(amount * (10 ** decimals))
