import logging

import pandas as pd
import ta

from .base import BaseStrategy, Signal

logger = logging.getLogger("trading-bot")


class RSIStrategy(BaseStrategy):

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def analyze(self, df: pd.DataFrame, symbol: str) -> Signal:
        if len(df) < self.period + 1:
            return Signal.HOLD

        rsi = ta.momentum.RSIIndicator(df["Close"], window=self.period).rsi()
        current_rsi = rsi.iloc[-1]

        logger.debug(f"{symbol} RSI: {current_rsi:.1f}")

        if current_rsi < self.oversold:
            logger.info(f"{symbol} RSI={current_rsi:.1f} < {self.oversold} → KÖP-signal")
            return Signal.BUY
        elif current_rsi > self.overbought:
            logger.info(f"{symbol} RSI={current_rsi:.1f} > {self.overbought} → SÄLJ-signal")
            return Signal.SELL

        return Signal.HOLD
