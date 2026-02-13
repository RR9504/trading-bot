import logging
from datetime import datetime

from alpaca_trade_api import REST as AlpacaREST

from .base import BaseBroker, Order, OrderSide, OrderStatus, Position

logger = logging.getLogger("trading-bot")


class AlpacaBroker(BaseBroker):

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.api = None

    def connect(self) -> bool:
        try:
            self.api = AlpacaREST(self.api_key, self.api_secret, self.base_url)
            account = self.api.get_account()
            logger.info(f"Alpaca ansluten: {account.status} | Kapital: ${float(account.equity):,.2f}")
            return True
        except Exception as e:
            logger.error(f"Kunde inte ansluta till Alpaca: {e}")
            return False

    def get_balance(self) -> float:
        account = self.api.get_account()
        return float(account.cash)

    def get_positions(self) -> dict[str, Position]:
        positions = {}
        for p in self.api.list_positions():
            positions[p.symbol] = Position(
                symbol=p.symbol,
                quantity=float(p.qty),
                avg_price=float(p.avg_entry_price),
                current_price=float(p.current_price),
            )
        return positions

    def place_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> Order:
        try:
            alpaca_order = self.api.submit_order(
                symbol=symbol,
                qty=int(quantity),
                side=side.value,
                type="market",
                time_in_force="day",
            )
            status = self._map_status(alpaca_order.status)
            logger.info(f"Alpaca order: {side.value} {int(quantity)} {symbol} → {status.value}")
            return Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                status=status,
                timestamp=datetime.now(),
                order_id=alpaca_order.id,
            )
        except Exception as e:
            logger.error(f"Alpaca order misslyckades: {e}")
            return Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                status=OrderStatus.REJECTED,
                timestamp=datetime.now(),
            )

    def get_order_status(self, order_id: str) -> OrderStatus:
        try:
            order = self.api.get_order(order_id)
            return self._map_status(order.status)
        except Exception:
            return OrderStatus.CANCELLED

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.api.cancel_order(order_id)
            return True
        except Exception:
            return False

    def _map_status(self, alpaca_status: str) -> OrderStatus:
        mapping = {
            "new": OrderStatus.PENDING,
            "accepted": OrderStatus.PENDING,
            "partially_filled": OrderStatus.PENDING,
            "filled": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "expired": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
        }
        return mapping.get(alpaca_status, OrderStatus.PENDING)
