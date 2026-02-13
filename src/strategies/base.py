from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class BaseStrategy(ABC):

    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str) -> Signal:
        pass
