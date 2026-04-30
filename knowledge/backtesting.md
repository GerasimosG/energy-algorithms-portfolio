# Backtesting & Risk Metrics

## The Core Problem

You have a trading strategy. You want to know: **would it have made money?** The answer requires backtesting — simulating the strategy on historical data. But there are MANY ways to accidentally cheat.

---

## Look-Ahead Bias: The Silent Killer

**Definition:** Using information at time t that wasn't available at time t.

### The Classic Mistake

```python
# WRONG: signal uses today's price, trade at today's price
signal[t] = compute_signal(prices[t])  # You don't know price[t] yet
position[t] = signal[t]               # Can't trade at price you haven't seen
```

### The Correct Approach

```python
# RIGHT: signal from price[t-1], trade at price[t]
signal[t] = compute_signal(prices[t-1])       # Past info only
position[t] = signal[t]                        # Enter position
return[t] = position[t] * (prices[t+1]/prices[t] - 1)
```

Our `backtester/engine.py`:
```python
signals_shifted = np.roll(signals, 1)  # Shift by 1 bar
signals_shifted[0] = 0                  # No position before first signal
```

### How Bad Is It?

Look-ahead bias can inflate Sharpe ratios by **2-3x**. A strategy with real Sharpe 0.5 backtests at 1.5. If your backtest shows Sharpe > 2.0, it's almost certainly biased.

---

## Other Biases

### Survivorship Bias
Using only stocks that EXIST today. Bankrupt companies are excluded → historical returns look better than real.

### Data Snooping
Testing 100 strategies and picking the best. By chance, one looks great historically but fails out-of-sample.

**Fix:** Walk-forward validation — train to T, test T+1, roll forward.

### Transaction Cost Neglect
Ignoring commissions, spreads, market impact. A strategy making 0.1% per trade with 0.1% commission breaks even.

---

## Risk Metrics (from `backtester/metrics.py`)

### Sharpe Ratio
```
Sharpe = (r_p - r_f) / sigma_p
```
Return per unit of risk. >1.0 good, >2.0 exceptional (or suspicious).

### Sortino Ratio
```
Sortino = (r_p - r_f) / sigma_downside
```
Only penalizes DOWNSIDE volatility. Better than Sharpe for asymmetric returns.

### Maximum Drawdown
```
MaxDD = max((peak - trough) / peak)
```
Worst peak-to-trough decline. "You lost 40% before recovering."

### Calmar Ratio
```
Calmar = annual_return / MaxDD
```
Return per unit of worst-case loss.

### Value at Risk (VaR)
```
VaR_95 = 5th percentile of daily returns
```
"On 95% of days, you won't lose more than X."

**Biggest weakness:** VaR tells you NOTHING about the worst 5% of days.

### Expected Shortfall (CVaR)
```
CVaR_95 = average return in the worst 5% of days
```
"What you actually lose on the really bad days."

### Kelly Criterion
```
f* = (p * b - q) / b
```
Optimal bet size for maximum long-term growth. Full Kelly is very aggressive — use half-Kelly in practice.

---

## Vectorized Backtesting

```python
# Traditional: loop-based (slow Python)
for t in range(len(prices)):
    signal = compute_signal(prices[:t])
    pnl = position * (prices[t+1] - prices[t])

# Vectorized: numpy (fast C-level)
returns = np.diff(prices) / prices[:-1]
strategy_returns = signals_shifted[:-1] * returns[1:]
equity_curve = np.cumprod(1 + strategy_returns)
```

100-1000x faster. No Python loops. Clean, testable.

---

## Edge Cases

### Flat Prices
```python
prices = [100, 100, 100, 100]
Sharpe = 0, VaR = 0, MaxDD = 0  # verified in test_backtest_all_flat
```

### Insufficient Data for VaR
VaR_95 needs >= 20 returns. With less, returns NaN — verified in `test_var_95`.

### Kelly > 1
Formula can return f* > 1. Our code bounds: `kelly = min(kelly_raw, 1.0)`.

---

## Quick Quiz

**Q1:** What's look-ahead bias and how much does it inflate Sharpe?

**Q2:** When is Sortino HIGHER than Sharpe for the same strategy?

**Q3:** What's VaR's biggest weakness?

**Q4:** Why shift signals by 1 bar?

**Q5:** 50 strategies tested, best Sharpe 2.0. Is it real?

---

## Answers

**A1:** Using future information to make past decisions. Inflates Sharpe 2-3x.

**A2:** When the strategy has large positive returns (high upside volatility) that Sharpe penalizes as risk but Sortino identifies as beneficial.

**A3:** VaR tells you the threshold for the best 95% of days, nothing about the worst 5%. CVaR fixes this.

**A4:** To avoid look-ahead bias. Signal from price[t-1] → position at price[t]. You can't know price[t] when computing signal[t].

**A5:** Probably not. Expect 2-3 false positives by chance. Need out-of-sample walk-forward validation to confirm.
