"""Unit tests for the pure grid logic (no network needed)."""

from bot.grid import GridState, Side, build_levels, evaluate


def test_build_levels_evenly_spaced():
    levels = build_levels(1.0, 2.0, 5)
    assert levels == [1.0, 1.25, 1.5, 1.75, 2.0]


def test_first_tick_records_band_no_order():
    levels = build_levels(1.0, 2.0, 5)
    state = GridState()
    orders = evaluate(1.5, levels, 10.0, state)
    assert orders == []
    assert state.last_band == 2  # 1.5 sits on level index 2


def test_price_drop_triggers_buys():
    levels = build_levels(1.0, 2.0, 5)  # [1.0,1.25,1.5,1.75,2.0]
    state = GridState()
    evaluate(2.0, levels, 10.0, state)      # band 4, no order
    orders = evaluate(1.5, levels, 10.0, state)  # crosses down to band 2
    assert [o.side for o in orders] == [Side.BUY, Side.BUY]
    assert all(o.quote_amount == 10.0 for o in orders)
    # inventory recorded at the two crossed levels (4 and 3)
    assert state.inventory.get(4) == 10.0
    assert state.inventory.get(3) == 10.0


def test_price_rise_sells_inventory():
    levels = build_levels(1.0, 2.0, 5)
    state = GridState()
    evaluate(2.0, levels, 10.0, state)   # band 4
    evaluate(1.5, levels, 10.0, state)   # buys at levels 4,3 -> band 2
    orders = evaluate(2.0, levels, 10.0, state)  # rise back -> sell levels 3,4
    sides = [o.side for o in orders]
    assert sides == [Side.SELL, Side.SELL]
    assert state.inventory.get(3) == 0.0
    assert state.inventory.get(4) == 0.0


def test_no_sell_without_inventory():
    levels = build_levels(1.0, 2.0, 5)
    state = GridState()
    evaluate(1.0, levels, 10.0, state)   # band 0
    orders = evaluate(2.0, levels, 10.0, state)  # rise but nothing bought yet
    assert orders == []


def test_price_below_grid_clamps():
    levels = build_levels(1.0, 2.0, 5)
    state = GridState()
    evaluate(1.5, levels, 10.0, state)        # band 2
    orders = evaluate(0.5, levels, 10.0, state)  # below grid -> clamp to band 0
    assert [o.side for o in orders] == [Side.BUY, Side.BUY]
    assert state.last_band == 0
