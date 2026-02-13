import uuid
from datetime import datetime

from .base import BaseBroker, Order, OrderSide, OrderStatus, Position


class PaperBroker(BaseBroker):

    def __init__(self, initial_balance: float = 100000.0):
        self.cash = initial_balance
        self.initial_balance = initial_balance
        self.positions: dict[str, Position] = {}
        self.orders: dict[str, Order] = {}
        self.trade_history: list[Order] = []

    def connect(self) -> bool:
        return True

    def get_balance(self) -> float:
        return self.cash

    def get_total_value(self) -> float:
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value

    def get_positions(self) -> dict[str, Position]:
        return self.positions.copy()

    def place_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> Order:
        order_id = str(uuid.uuid4())[:8]
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
            timestamp=datetime.now(),
            order_id=order_id,
        )

        if side == OrderSide.BUY:
            cost = quantity * price
            if cost > self.cash:
                order.status = OrderStatus.REJECTED
                self.orders[order_id] = order
                return order
            self.cash -= cost
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_qty = pos.quantity + quantity
                pos.avg_price = (pos.avg_price * pos.quantity + price * quantity) / total_qty
                pos.quantity = total_qty
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price,
                    current_price=price,
                )

        elif side == OrderSide.SELL:
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                order.status = OrderStatus.REJECTED
                self.orders[order_id] = order
                return order
            self.cash += quantity * price
            pos = self.positions[symbol]
            pos.quantity -= quantity
            if pos.quantity <= 0:
                del self.positions[symbol]

        order.status = OrderStatus.FILLED
        self.orders[order_id] = order
        self.trade_history.append(order)
        return order

    def get_order_status(self, order_id: str) -> OrderStatus:
        if order_id in self.orders:
            return self.orders[order_id].status
        return OrderStatus.CANCELLED

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders and self.orders[order_id].status == OrderStatus.PENDING:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def update_prices(self, prices: dict[str, float]):
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
