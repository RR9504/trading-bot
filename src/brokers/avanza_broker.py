import logging
from datetime import datetime

from avanza import Avanza

from .base import BaseBroker, Order, OrderSide, OrderStatus, Position

logger = logging.getLogger("trading-bot")


class AvanzaBroker(BaseBroker):

    def __init__(self, username: str, password: str, totp_secret: str):
        self.username = username
        self.password = password
        self.totp_secret = totp_secret
        self.client = None
        self.account_id = None

    def connect(self) -> bool:
        try:
            self.client = Avanza({
                "username": self.username,
                "password": self.password,
                "totpSecret": self.totp_secret,
            })
            overview = self.client.get_overview()
            accounts = overview.get("accounts", [])
            if accounts:
                self.account_id = accounts[0]["accountId"]
                total = sum(float(a.get("totalBalance", 0)) for a in accounts)
                logger.info(f"Avanza ansluten | Konto: {self.account_id} | Totalt: {total:,.0f} SEK")
            return True
        except Exception as e:
            logger.error(f"Kunde inte ansluta till Avanza: {e}")
            return False

    def get_balance(self) -> float:
        try:
            overview = self.client.get_overview()
            for account in overview.get("accounts", []):
                if account["accountId"] == self.account_id:
                    return float(account.get("buyingPower", 0))
        except Exception as e:
            logger.error(f"Kunde inte hämta saldo: {e}")
        return 0.0

    def get_positions(self) -> dict[str, Position]:
        positions = {}
        try:
            overview = self.client.get_overview()
            for pos in overview.get("positions", []):
                symbol = pos.get("instrument", {}).get("ticker", "")
                if not symbol:
                    continue
                positions[symbol] = Position(
                    symbol=symbol,
                    quantity=float(pos.get("volume", 0)),
                    avg_price=float(pos.get("acquiredPrice", 0)),
                    current_price=float(pos.get("lastPrice", 0)),
                )
        except Exception as e:
            logger.error(f"Kunde inte hämta positioner: {e}")
        return positions

    def place_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> Order:
        try:
            # Sök instrument-ID baserat på ticker
            search = self.client.search_for_stock(symbol)
            if not search.get("hits"):
                raise ValueError(f"Hittade inte instrument: {symbol}")

            instrument_id = search["hits"][0]["topHits"][0]["id"]
            order_type = "BUY" if side == OrderSide.BUY else "SELL"

            result = self.client.place_order(
                account_id=self.account_id,
                order_body={
                    "orderbookId": instrument_id,
                    "orderType": order_type,
                    "price": price,
                    "validUntil": datetime.now().strftime("%Y-%m-%d"),
                    "volume": int(quantity),
                }
            )

            order_id = str(result.get("orderId", ""))
            status = OrderStatus.PENDING if result.get("status") == "SUCCESS" else OrderStatus.REJECTED
            logger.info(f"Avanza order: {side.value} {int(quantity)} {symbol} @ {price:.2f} → {status.value}")

            return Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                status=status,
                timestamp=datetime.now(),
                order_id=order_id,
            )
        except Exception as e:
            logger.error(f"Avanza order misslyckades: {e}")
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
            deals = self.client.get_deals_and_orders()
            for order in deals.get("orders", []):
                if str(order.get("orderId")) == order_id:
                    avanza_status = order.get("orderState", "")
                    return self._map_status(avanza_status)
        except Exception:
            pass
        return OrderStatus.PENDING

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.client.delete_order(account_id=self.account_id, order_id=order_id)
            return True
        except Exception:
            return False

    def _map_status(self, avanza_status: str) -> OrderStatus:
        mapping = {
            "Utförd": OrderStatus.FILLED,
            "Makulerad": OrderStatus.CANCELLED,
            "Aktiv": OrderStatus.PENDING,
            "Avvisad": OrderStatus.REJECTED,
        }
        return mapping.get(avanza_status, OrderStatus.PENDING)
