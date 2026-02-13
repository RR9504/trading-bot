import logging

import pandas as pd

from .base import BaseStrategy, Signal

logger = logging.getLogger("trading-bot")


class MomentumStrategy(BaseStrategy):

    def __init__(self, short_window: int = 10, long_window: int = 30, momentum_threshold: float = 0.02):
        self.short_window = short_window
        self.long_window = long_window
        self.momentum_threshold = momentum_threshold

    def analyze(self, df: pd.DataFrame, symbol: str) -> Signal:
        if len(df) < self.long_window + 1:
            return Signal.HOLD

        short_ma = df["Close"].rolling(window=self.short_window).mean()
        long_ma = df["Close"].rolling(window=self.long_window).mean()

        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]

        # Beräkna momentum som procentuell förändring
        momentum = (current_short - current_long) / current_long

        logger.debug(f"{symbol} Momentum: {momentum:.3f} | SMA{self.short_window}: {current_short:.2f} | SMA{self.long_window}: {current_long:.2f}")

        # Bullish: kort MA korsar uppåt genom lång MA med tillräckligt momentum
        if prev_short <= prev_long and current_short > current_long and momentum > self.momentum_threshold:
            logger.info(f"{symbol} Momentum bullish crossover ({momentum:.1%}) → KÖP-signal")
            return Signal.BUY

        # Bearish: kort MA korsar nedåt genom lång MA
        if prev_short >= prev_long and current_short < current_long:
            logger.info(f"{symbol} Momentum bearish crossover → SÄLJ-signal")
            return Signal.SELL

        return Signal.HOLD
