"""Pure grid-trading logic — no network, fully unit-testable.

A grid splits a price band into evenly spaced levels. As the price moves down
across a level we BUY base; as it moves up across a level we SELL base. This
captures profit from oscillation inside the band.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    side: Side
    # Quote amount to spend (BUY) or quote value targeted (SELL), informational.
    quote_amount: float
    # Grid level (price) that triggered this order.
    level_price: float


@dataclass
class GridState:
    """Mutable state the bot persists between ticks."""
    last_band: int = -1   # which band the price was in on the previous tick
    # base inventory bought at each level index (so SELL knows how much to unwind)
    inventory: dict = field(default_factory=dict)


def build_levels(lower: float, upper: float, levels: int) -> List[float]:
    """Evenly spaced grid prices from lower to upper (inclusive)."""
    step = (upper - lower) / (levels - 1)
    return [lower + step * i for i in range(levels)]


def _band_of(price: float, grid_levels: List[float]) -> int:
    """Index of the highest level that is <= price.

    Returns -1 if price is below the whole grid, len-1 if at/above the top.
    """
    band = -1
    for i, lvl in enumerate(grid_levels):
        if price >= lvl:
            band = i
        else:
            break
    return band


def evaluate(
    price: float,
    grid_levels: List[float],
    order_size_quote: float,
    state: GridState,
) -> List[Order]:
    """Decide which orders to emit given the current price and prior state.

    On first observation we only record the band (no trade). Afterwards every
    crossed level produces one order in the direction of travel.
    """
    band = _band_of(price, grid_levels)

    # Clamp into the tradable range [0, len-1] for crossing math.
    clamped = max(0, min(band, len(grid_levels) - 1))

    if state.last_band == -1:
        state.last_band = clamped
        return []

    orders: List[Order] = []

    if clamped < state.last_band:
        # Price fell: BUY at each level we dropped through.
        for lvl_idx in range(state.last_band, clamped, -1):
            level_price = grid_levels[lvl_idx]
            orders.append(Order(Side.BUY, order_size_quote, level_price))
            state.inventory[lvl_idx] = state.inventory.get(lvl_idx, 0.0) + order_size_quote
    elif clamped > state.last_band:
        # Price rose: SELL the inventory we bought at the levels we climbed past.
        for lvl_idx in range(state.last_band + 1, clamped + 1):
            held = state.inventory.get(lvl_idx, 0.0)
            if held > 0:
                level_price = grid_levels[lvl_idx]
                orders.append(Order(Side.SELL, held, level_price))
                state.inventory[lvl_idx] = 0.0

    state.last_band = clamped
    return orders
