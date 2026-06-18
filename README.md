# Fast BNB Bot ⚡

A fast **grid-trading** bot for **PancakeSwap** on **BNB Smart Chain (BSC)**, written in Python.

It splits a price band into evenly spaced levels and trades the oscillation:
**buys** the base token as the price falls through a level, **sells** it as the
price climbs back up. It polls the on-chain price quickly (default every second)
so it reacts fast to moves.

> **Safety first:** the bot runs in **dry-run (paper) mode by default**. It will
> never send a real transaction until you provide a `PRIVATE_KEY` *and* explicitly
> enable live mode. Trade at your own risk — DEX trading can lose money.

## How it works

```
price ──▶ PancakeSwap getAmountsOut ──▶ grid engine ──▶ BUY/SELL ──▶ swap (or simulate)
```

- `bot/chain.py` — connects to BSC, reads price, signs & sends swaps.
- `bot/grid.py` — pure grid strategy (fully unit-tested, no network).
- `bot/bot.py` — main loop, risk limits, dry-run accounting, state persistence.
- `bot/config.py` — YAML strategy config + `.env` secrets.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # leave PRIVATE_KEY empty for dry-run
cp config.example.yaml config.yaml
```

Edit `config.yaml` to set the token pair, grid band, and order size.

## Run

Dry-run / paper mode (safe, default):

```bash
python main.py
```

Live trading (real funds — needs `PRIVATE_KEY` in `.env`):

```bash
python main.py --live
```

It prints the mode on startup and pauses 5s before live trading so you can abort.

## Run 24/7 (always on)

The bot already loops forever — buying as the price falls and selling as it
rises — and survives transient RPC errors. To keep it alive across crashes and
reboots **on your existing server** (no extra hosting, no extra cost), use one
of these:

**Option A — systemd (recommended, needs root):**

```bash
sudo cp deploy/fast-bnb-bot.service /etc/systemd/system/
sudoedit /etc/systemd/system/fast-bnb-bot.service   # set User + paths
sudo systemctl daemon-reload
sudo systemctl enable --now fast-bnb-bot            # starts now + on every boot
journalctl -u fast-bnb-bot -f                       # live logs
```

It restarts automatically if it crashes or the machine reboots.

**Option B — no root (nohup + auto-restart loop):**

```bash
nohup ./deploy/run-forever.sh > bot.out 2>&1 &
tail -f bot.out          # logs
pkill -f main.py         # stop
```

Both keep running after you log out. Start in **dry-run** to watch it trade
24/7 safely before risking real funds.

## Configuration

All strategy settings live in `config.yaml` (see `config.example.yaml` for the
full annotated template). Secrets (`BSC_RPC_URL`, `PRIVATE_KEY`) live in `.env`
and are **gitignored**.

Key knobs:

| Setting | Meaning |
|---|---|
| `grid.lower_price` / `upper_price` | the band the grid trades in (quote per base) |
| `grid.levels` | number of grid lines |
| `grid.order_size_quote` | quote spent per buy step |
| `execution.poll_interval_sec` | how fast it re-checks the price |
| `execution.slippage_bps` | max slippage on swaps (50 = 0.5%) |
| `risk.max_quote_exposure` | cap on base held |
| `risk.stop_below_price` / `stop_above_price` | halt the bot outside this range |

## Tests

```bash
pip install pytest
pytest
```

The grid engine is pure and covered by unit tests — no RPC needed.

## Disclaimer

This software is provided for educational purposes. Automated trading is risky;
you are solely responsible for any funds you put at risk. Start in dry-run,
use a dedicated wallet with limited funds, and never commit your private key.
