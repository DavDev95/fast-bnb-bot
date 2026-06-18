"""Main bot loop: poll price, run the grid, execute (or simulate) swaps."""

import json
import os
import time
from typing import Optional

from .chain import Chain
from .config import Config
from .grid import GridState, Order, Side, build_levels, evaluate
from .logger import get_logger

log = get_logger()
STATE_FILE = "state.json"


class GridBot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.chain = Chain(cfg)
        self.levels = build_levels(
            cfg.grid.lower_price, cfg.grid.upper_price, cfg.grid.levels
        )
        self.state = self._load_state()
        # Simulated holdings used in dry-run accounting.
        self.sim_base = 0.0
        self.sim_quote = 0.0

    # --- persistence ------------------------------------------------------
    def _load_state(self) -> GridState:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            inv = {int(k): v for k, v in raw.get("inventory", {}).items()}
            return GridState(last_band=raw.get("last_band", -1), inventory=inv)
        return GridState()

    def _save_state(self) -> None:
        with open(STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(
                {"last_band": self.state.last_band, "inventory": self.state.inventory},
                fh,
            )

    # --- risk -------------------------------------------------------------
    def _risk_halt(self, price: float) -> Optional[str]:
        r = self.cfg.risk
        if r.stop_below_price is not None and price < r.stop_below_price:
            return f"price {price:.6g} below stop {r.stop_below_price}"
        if r.stop_above_price is not None and price > r.stop_above_price:
            return f"price {price:.6g} above stop {r.stop_above_price}"
        return None

    def _exposure_ok(self, price: float) -> bool:
        max_exp = self.cfg.risk.max_quote_exposure
        if max_exp is None:
            return True
        held_base = self.sim_base if self.cfg.dry_run else self.chain.balance(
            self.chain.base, self.chain.base_decimals
        )
        return held_base * price <= max_exp

    # --- execution --------------------------------------------------------
    def _execute(self, order: Order, price: float) -> None:
        tag = "DRY" if self.cfg.dry_run else "LIVE"
        if order.side is Side.BUY:
            if not self._exposure_ok(price):
                log.warning("[%s] BUY skipped — max exposure reached", tag)
                return
            log.info("[%s] BUY  %.6g %s @ %.6g (level %.6g)", tag,
                     order.quote_amount, self.cfg.quote.symbol, price, order.level_price)
            if self.cfg.dry_run:
                self.sim_quote -= order.quote_amount
                self.sim_base += order.quote_amount / price
            else:
                raw = self.chain.to_raw(order.quote_amount, self.chain.quote_decimals)
                self.chain.swap(self.chain.quote, self.chain.base, raw)
        else:  # SELL: order.quote_amount is the quote we originally spent at the level
            base_amount = order.quote_amount / order.level_price
            log.info("[%s] SELL %.6g %s @ %.6g (level %.6g)", tag,
                     base_amount, self.cfg.base.symbol, price, order.level_price)
            if self.cfg.dry_run:
                self.sim_base -= base_amount
                self.sim_quote += base_amount * price
            else:
                raw = self.chain.to_raw(base_amount, self.chain.base_decimals)
                self.chain.swap(self.chain.base, self.chain.quote, raw)

    # --- main loop --------------------------------------------------------
    def run(self) -> None:
        mode = "DRY-RUN (no real trades)" if self.cfg.dry_run else "LIVE TRADING"
        log.info("Starting Fast BNB Bot — %s", mode)
        log.info("Pair %s/%s | grid %.6g..%.6g x%d | order %.6g %s",
                 self.cfg.base.symbol, self.cfg.quote.symbol,
                 self.cfg.grid.lower_price, self.cfg.grid.upper_price,
                 self.cfg.grid.levels, self.cfg.grid.order_size_quote,
                 self.cfg.quote.symbol)

        while True:
            try:
                price = self.chain.get_price()
                halt = self._risk_halt(price)
                if halt:
                    log.error("Risk halt: %s — stopping.", halt)
                    break

                orders = evaluate(
                    price, self.levels, self.cfg.grid.order_size_quote, self.state
                )
                for order in orders:
                    self._execute(order, price)
                if orders:
                    self._save_state()
                    if self.cfg.dry_run:
                        log.info("  sim PnL: base=%.6g quote=%.6g",
                                 self.sim_base, self.sim_quote)
                else:
                    log.debug("price %.6g — no action", price)

            except Exception as exc:  # keep the loop alive on transient RPC errors
                log.error("tick error: %s", exc)

            time.sleep(self.cfg.execution.poll_interval_sec)
