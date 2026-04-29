"""
Vectorized backtesting engine.
Takes price series + signal array → equity curve, trades log, stats.
Under 150 lines.
"""

import numpy as np
import pandas as pd


def backtest(
    prices: pd.Series | np.ndarray,
    signals: np.ndarray,
    initial_capital: float = 100_000.0,
    commission: float = 0.001,  # 0.1% per trade
    slippage: float = 0.0005,  # 0.05% slippage
) -> dict:
    """
    Vectorized backtest.

    Parameters
    ----------
    prices : array-like of close prices
    signals : array-like of ints (-1, 0, 1) for short, flat, long
    initial_capital : float
    commission : float, fractional cost per trade
    slippage : float, fractional slippage per trade

    Returns
    -------
    dict with keys: equity_curve, trades, total_return, annual_return,
                    volatility, sharpe, max_drawdown, n_trades, win_rate
    """
    prices = np.asarray(prices, dtype=float)
    signals = np.asarray(signals, dtype=int)
    n = len(prices)

    # 1. Position changes (only when signal changes)
    prev_signal = np.roll(signals, 1)
    prev_signal[0] = 0
    position_changes = signals - prev_signal

    # 2. Daily returns from price moves
    daily_returns = np.zeros(n)
    daily_returns[1:] = np.diff(prices) / prices[:-1]

    # 3. Strategy returns: position * daily_return
    strategy_returns = signals * daily_returns

    # 4. Transaction costs at each change
    trade_cost = np.abs(position_changes) * (commission + slippage)
    net_returns = strategy_returns - trade_cost

    # 5. Equity curve
    equity = initial_capital * np.cumprod(1 + net_returns)
    equity_curve = pd.Series(equity, name="equity")

    # 6. Trades log
    trade_dates = np.where(position_changes != 0)[0]
    trades = []
    for i, idx in enumerate(trade_dates):
        direction = int(position_changes[idx])
        entry_price = prices[idx]
        # Find exit: next trade change or end
        exit_idx = trade_dates[i + 1] if i + 1 < len(trade_dates) else n - 1
        exit_price = prices[exit_idx]
        ret = (exit_price / entry_price - 1) * (
            1 if signals[idx] > 0 else -1
        )
        ret -= (commission + slippage) * 2  # entry + exit cost
        trades.append(
            {
                "entry": int(idx),
                "exit": int(exit_idx),
                "direction": "long" if direction > 0 else "short",
                "entry_price": round(float(entry_price), 2),
                "exit_price": round(float(exit_price), 2),
                "return": round(float(ret), 4),
            }
        )

    # 7. Performance stats
    total_return = equity[-1] / equity[0] - 1
    trading_days = n
    ann_factor = 252
    ann_return = (1 + total_return) ** (ann_factor / trading_days) - 1

    # Sharpe ratio (annualized)
    nonzero = net_returns[net_returns != 0]
    if len(nonzero) > 1:
        sharpe = float(np.mean(net_returns) / np.std(net_returns) * np.sqrt(ann_factor))
        volatility = float(np.std(net_returns) * np.sqrt(ann_factor))
    else:
        sharpe = 0.0
        volatility = 0.0

    # Max drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = float(np.min(drawdown))

    # Win rate
    trade_returns = [t["return"] for t in trades if t["return"] != 0]
    win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns) if trade_returns else 0.0

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "total_return": round(float(total_return), 4),
        "ann_return": round(float(ann_return), 4),
        "volatility": round(volatility, 4),
        "sharpe": round(float(sharpe), 4),
        "max_drawdown": round(max_dd, 4),
        "n_trades": len(trades),
        "win_rate": round(float(win_rate), 4),
    }
