from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    status: OrderStatus
    timestamp: datetime
    order_id: str = ""

    @property
    def value(self) -> float:
        return self.quantity * self.price


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_price == 0:
            return 0.0
        return (self.current_price - self.avg_price) / self.avg_price


class BaseBroker(ABC):

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def get_balance(self) -> float:
        pass

    @abstractmethod
    def get_positions(self) -> dict[str, Position]:
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> Order:
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass
