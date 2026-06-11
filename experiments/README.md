# Portfolio experiments

Two trackable ML experiments targeting the **energy market** and **energy trading** JDs.
Each experiment logs runs to the SQLite-backed experiment tracker
(default `~/.hermes/experiments.db`).

---

## What's in here

| File | Maps to JD bullet | What it shows |
|---|---|---|
| `joint_reserve_revenue_stack.py` (exp1) | energy trading: "revenue stacking for BESS" | 4 scenarios on ~30 days BE prices: arbitrage / +FCR / +aFRR / full stack. Total revenue per scenario + revenue split. |
| `strategy_head_to_head.py` (exp2) | energy trading: "3 signal strategies" + "backtesting" | 3 strategies (hour-of-day, solar-duck, calendar-spread) × 4 regimes (all / spring / summer / other). 7-metric risk suite per (strategy, regime). |
| `runner.py` | n/a | Single CLI to run one or all experiments. |
| `__init__.py` | n/a | Package marker so cross-imports between exp1 and exp2 work. |

---

## Quick start (your laptop)

```bash
# 1. Make sure the repo is installed editable.
cd ~/projects/Energy_Algorithms
pip install -e ".[dev]"

# 2. Run both experiments.
python experiments/runner.py all --out experiments/output

# 3. Inspect.
ea-experiments list --name exp1
ea-experiments list --name exp2
ea-experiments compare <run_id_1> <run_id_2> ...
```

Or one at a time:

```bash
python experiments/joint_reserve_revenue_stack.py --out experiments/output
python experiments/strategy_head_to_head.py    --out experiments/output
```

---

## Inputs

### Default: real Belgian ENTSO-E prices

`data/entsoe_30day_prices.csv` (~30 days, quarter-hourly). Both
experiments bucket quarter-hourly → hourly by averaging.

### Fallback: synthetic data

If the CSV is missing, both experiments generate 30 days of synthetic
Belgian profile (sinusoidal intraday curve + noise + occasional spike,
seeded so runs are reproducible). The fallback is identical across
runs and platforms — useful for CI / laptop tests / first runs before
you have the live data.

### Custom data

Pass a different CSV path:

```bash
python experiments/joint_reserve_revenue_stack.py --db /tmp/my_exps.db
```

The expected schema is `date,hour,price_eur_mwh` where `hour` is
quarter-of-day (1..96). The loader buckets into 24 hourly slots by
averaging within each `(date, hour_of_day)` group.

---

## Outputs

### SQLite tracker

Every scenario × day combo is logged as a separate `run` in
`~/.hermes/experiments.db`. Inspect with the `ea-experiments` CLI:

```bash
ea-experiments list --name exp1
ea-experiments show <run_id>
ea-experiments compare <id1> <id2> <id3>
```

### Console summary

Both experiments print a formatted table at the end (revenue split
for exp1, 7-metric + regime for exp2).

### CSV / JSON dumps

If you pass `--out <dir>`, both experiments write per-day results
to CSV plus a scenario-config JSON. Useful for plotting in a
notebook without re-running the experiments.

---

## Configuration knobs

### exp1 — joint reserve

| Knob | Default | What it controls |
|---|---|---|
| FCR price (€/MW/h) | 20.0 | Belgian 2024 typical |
| aFRR up price (€/MW/h) | 15.0 | Belgian 2024 typical |
| aFRR down price (€/MW/h) | 12.0 | Belgian 2024 typical |
| aFRR activation probability | 0.3 | Sweep 0.0 / 0.3 / 0.5 to test sensitivity |
| BESS capacity (MWh) | 100.0 | Matches `institutional_trading_demo` defaults |
| BESS max power (MW) | 50.0 | Matches `institutional_trading_demo` defaults |
| Round-trip efficiency | 0.92 / 0.92 | Li-ion BESS typical |

To change defaults, edit the constants at the top of
`joint_reserve_revenue_stack.py`.

### exp2 — strategy head-to-head

| Knob | Default | What it controls |
|---|---|---|
| `lookback_days` (hour-of-day) | 7 | Strategy parameter — would sweep in production |
| `threshold_pct` (hour-of-day) | 0.05 | Strategy parameter |
| `short_window` / `long_window` (calendar) | 3 / 7 | SMA crossover windows |
| `threshold` (calendar) | 0.02 | Entry threshold |
| Commission | 0.1% | Belgian day-ahead typical |
| Slippage | 0.05% | Flat — production would model queue position |
| Initial capital | €100,000 | Reference for Sharpe scaling |

---

## Caveats (for interview honesty)

These are documented inside each experiment file's docstring. Quick
recap:

**exp1**:
- Single BESS, no portfolio bidding, no prequalification constraints.
- FCR / aFRR prices are held constant — production would forecast
  these from the PICASSO / MARI platforms.
- Activation probability is a known unknown. Sweeping 0.0 / 0.3 / 0.5
  shows sensitivity.
- Real production would model asymmetric FCR (rare) and mFRR.

**exp2**:
- Strategies are vectorized per-day, no walk-forward. Production
  would add an out-of-sample split.
- Slippage is a flat 0.05% — production would model queue position.
- The "all" regime mixes spring + summer. Reading the regime
  columns separately is the real insight.

---

## Time budget

On a laptop, both experiments run in **under 60 seconds total**:

- exp1: 4 scenarios × 30 days = 120 LP solves ≈ 5-10 seconds
- exp2: 3 strategies × 4 regimes = 12 backtest runs ≈ 1-2 seconds

If exp1 takes > 30 s, you have an environment issue (PuLP not
finding the CBC binary). Run `which cbc` to verify.
