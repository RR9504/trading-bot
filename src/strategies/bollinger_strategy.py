import logging

import pandas as pd
import ta

from .base import BaseStrategy, Signal

logger = logging.getLogger("trading-bot")


class BollingerStrategy(BaseStrategy):

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def analyze(self, df: pd.DataFrame, symbol: str) -> Signal:
        if len(df) < self.period + 1:
            return Signal.HOLD

        bb = ta.volatility.BollingerBands(df["Close"], window=self.period, window_dev=self.std_dev)
        current_price = df["Close"].iloc[-1]
        lower_band = bb.bollinger_lband().iloc[-1]
        upper_band = bb.bollinger_hband().iloc[-1]

        logger.debug(f"{symbol} Pris: {current_price:.2f} | BB: [{lower_band:.2f} - {upper_band:.2f}]")

        # Pris under undre bandet → överssålt, köp
        if current_price < lower_band:
            logger.info(f"{symbol} under Bollinger undre band → KÖP-signal")
            return Signal.BUY

        # Pris över övre bandet → överköpt, sälj
        if current_price > upper_band:
            logger.info(f"{symbol} över Bollinger övre band → SÄLJ-signal")
            return Signal.SELL

        return Signal.HOLD
