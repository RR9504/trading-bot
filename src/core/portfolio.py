from dataclasses import dataclass, field
from datetime import datetime

from src.brokers.base import OrderSide


@dataclass
class TradeRecord:
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    pnl: float = 0.0


class Portfolio:

    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.trade_records: list[TradeRecord] = []

    def record_trade(self, symbol: str, side: OrderSide, quantity: float, price: float, pnl: float = 0.0):
        self.trade_records.append(TradeRecord(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            pnl=pnl,
        ))

    def get_total_pnl(self) -> float:
        return sum(t.pnl for t in self.trade_records)

    def get_daily_pnl(self) -> float:
        today = datetime.now().date()
        return sum(t.pnl for t in self.trade_records if t.timestamp.date() == today)

    def get_trade_count(self) -> int:
        return len(self.trade_records)

    def get_win_rate(self) -> float:
        sells = [t for t in self.trade_records if t.side == OrderSide.SELL]
        if not sells:
            return 0.0
        wins = sum(1 for t in sells if t.pnl > 0)
        return wins / len(sells)
