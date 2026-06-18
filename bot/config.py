"""Configuration loading: YAML for strategy, .env for secrets."""

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class TokenCfg:
    address: str
    symbol: str


@dataclass
class GridCfg:
    lower_price: float
    upper_price: float
    levels: int
    order_size_quote: float

    def __post_init__(self) -> None:
        if self.lower_price <= 0 or self.upper_price <= 0:
            raise ValueError("grid prices must be positive")
        if self.upper_price <= self.lower_price:
            raise ValueError("grid.upper_price must be greater than lower_price")
        if self.levels < 2:
            raise ValueError("grid.levels must be >= 2")
        if self.order_size_quote <= 0:
            raise ValueError("grid.order_size_quote must be positive")


@dataclass
class ExecutionCfg:
    poll_interval_sec: float = 1.0
    slippage_bps: int = 50
    deadline_sec: int = 30
    gas_price_gwei: Optional[float] = None
    max_gas_limit: int = 350_000


@dataclass
class RiskCfg:
    max_quote_exposure: Optional[float] = None
    stop_below_price: Optional[float] = None
    stop_above_price: Optional[float] = None


@dataclass
class ChurnCfg:
    """Buy a fixed quote amount then immediately sell it back, on a timer."""
    trade_size_quote: float = 0.15   # BNB spent per buy
    interval_sec: float = 10.0

    def __post_init__(self) -> None:
        if self.trade_size_quote <= 0:
            raise ValueError("churn.trade_size_quote must be positive")
        if self.interval_sec < 0:
            raise ValueError("churn.interval_sec must be >= 0")


@dataclass
class Config:
    dry_run: bool
    base: TokenCfg
    quote: TokenCfg
    grid: GridCfg
    mode: str = "grid"               # "grid" or "churn"
    execution: ExecutionCfg = field(default_factory=ExecutionCfg)
    risk: RiskCfg = field(default_factory=RiskCfg)
    churn: ChurnCfg = field(default_factory=ChurnCfg)
    # Secrets (from env, not YAML).
    rpc_url: str = "https://bsc-dataseed.binance.org"
    private_key: Optional[str] = None


def load_config(path: str = "config.yaml") -> Config:
    """Load strategy config from YAML and secrets from the environment."""
    load_dotenv()

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    tokens = raw.get("tokens", {})
    base = TokenCfg(**tokens["base"])
    quote = TokenCfg(**tokens["quote"])
    grid = GridCfg(**raw["grid"])
    execution = ExecutionCfg(**raw.get("execution", {}))
    risk = RiskCfg(**raw.get("risk", {}))
    churn = ChurnCfg(**raw.get("churn", {}))
    mode = raw.get("mode", "grid")

    private_key = os.getenv("PRIVATE_KEY") or None
    dry_run = bool(raw.get("dry_run", True))

    # Safety: if no key is configured, force dry-run no matter what the YAML says.
    if not private_key:
        dry_run = True

    return Config(
        dry_run=dry_run,
        base=base,
        quote=quote,
        grid=grid,
        mode=mode,
        execution=execution,
        risk=risk,
        churn=churn,
        rpc_url=os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org"),
        private_key=private_key,
    )
