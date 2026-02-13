import logging

import pandas as pd
import ta

from .base import BaseStrategy, Signal

logger = logging.getLogger("trading-bot")


class MACDStrategy(BaseStrategy):

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def analyze(self, df: pd.DataFrame, symbol: str) -> Signal:
        if len(df) < self.slow + self.signal_period:
            return Signal.HOLD

        macd_indicator = ta.trend.MACD(df["Close"], window_slow=self.slow,
                                        window_fast=self.fast, window_sign=self.signal_period)
        macd_line = macd_indicator.macd()
        signal_line = macd_indicator.macd_signal()

        current_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        current_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]

        # Bullish crossover: MACD korsar uppåt genom signallinjen
        if prev_macd <= prev_signal and current_macd > current_signal:
            logger.info(f"{symbol} MACD bullish crossover → KÖP-signal")
            return Signal.BUY

        # Bearish crossover: MACD korsar nedåt genom signallinjen
        if prev_macd >= prev_signal and current_macd < current_signal:
            logger.info(f"{symbol} MACD bearish crossover → SÄLJ-signal")
            return Signal.SELL

        return Signal.HOLD
