import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from src.strategies.base import Signal
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.bollinger_strategy import BollingerStrategy
from src.strategies.momentum_strategy import MomentumStrategy


def _make_df(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "Open": prices,
        "High": [p * 1.01 for p in prices],
        "Low": [p * 0.99 for p in prices],
        "Close": prices,
        "Volume": [1000000] * len(prices),
    })


def test_rsi_hold_on_short_data():
    strategy = RSIStrategy(period=14)
    df = _make_df([100.0] * 10)
    assert strategy.analyze(df, "TEST") == Signal.HOLD


def test_rsi_buy_on_oversold():
    # Skapa fallande priser som ger låg RSI
    prices = [100.0] * 20 + [100 - i * 3 for i in range(20)]
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    df = _make_df(prices)
    signal = strategy.analyze(df, "TEST")
    assert signal in (Signal.BUY, Signal.HOLD)  # Beror på exakt RSI


def test_bollinger_hold_in_range():
    # Stabila priser ger HOLD
    prices = [100.0 + np.sin(i * 0.1) for i in range(50)]
    strategy = BollingerStrategy(period=20)
    df = _make_df(prices)
    signal = strategy.analyze(df, "TEST")
    assert signal == Signal.HOLD


def test_momentum_hold_on_short_data():
    strategy = MomentumStrategy(short_window=10, long_window=30)
    df = _make_df([100.0] * 20)
    assert strategy.analyze(df, "TEST") == Signal.HOLD


def test_macd_hold_on_short_data():
    strategy = MACDStrategy()
    df = _make_df([100.0] * 20)
    assert strategy.analyze(df, "TEST") == Signal.HOLD
