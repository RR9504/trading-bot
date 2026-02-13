import logging
from datetime import datetime

from binance.client import Client as BinanceClient

from .base import BaseBroker, Order, OrderSide, OrderStatus, Position

logger = logging.getLogger("trading-bot")


class BinanceBroker(BaseBroker):

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = None

    def connect(self) -> bool:
        try:
            self.client = BinanceClient(self.api_key, self.api_secret, testnet=self.testnet)
            account = self.client.get_account()
            logger.info(f"Binance ansluten (testnet={self.testnet}) | Status: {account['status']}")
            return True
        except Exception as e:
            logger.error(f"Kunde inte ansluta till Binance: {e}")
            return False

    def get_balance(self) -> float:
        account = self.client.get_account()
        for balance in account["balances"]:
            if balance["asset"] == "USDT":
                return float(balance["free"])
        return 0.0

    def get_positions(self) -> dict[str, Position]:
        positions = {}
        account = self.client.get_account()
        for balance in account["balances"]:
            qty = float(balance["free"]) + float(balance["locked"])
            if qty > 0 and balance["asset"] not in ("USDT", "USD"):
                symbol = balance["asset"] + "USDT"
                try:
                    ticker = self.client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker["price"])
                except Exception:
                    current_price = 0.0
                positions[symbol] = Position(
                    symbol=symbol,
                    quantity=qty,
                    avg_price=0.0,  # Binance API ger inte avg price direkt
                    current_price=current_price,
                )
        return positions

    def place_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> Order:
        try:
            # Konvertera symbol-format: BTC-USD → BTCUSDT
            binance_symbol = symbol.replace("-USD", "USDT").replace("-", "")

            binance_side = "BUY" if side == OrderSide.BUY else "SELL"
            result = self.client.create_order(
                symbol=binance_symbol,
                side=binance_side,
                type="MARKET",
                quantity=self._format_quantity(binance_symbol, quantity),
            )
            status = self._map_status(result["status"])
            filled_price = float(result.get("fills", [{}])[0].get("price", price)) if result.get("fills") else price
            logger.info(f"Binance order: {side.value} {quantity} {binance_symbol} → {status.value}")
            return Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=filled_price,
                status=status,
                timestamp=datetime.now(),
                order_id=str(result["orderId"]),
            )
        except Exception as e:
            logger.error(f"Binance order misslyckades: {e}")
            return Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                status=OrderStatus.REJECTED,
                timestamp=datetime.now(),
            )

    def get_order_status(self, order_id: str) -> OrderStatus:
        # Binance kräver symbol för att hämta order — förenklad implementation
        return OrderStatus.FILLED

    def cancel_order(self, order_id: str) -> bool:
        try:
            # Kräver symbol — skulle behöva spara symbol per order
            return False
        except Exception:
            return False

    def _format_quantity(self, symbol: str, quantity: float) -> str:
        try:
            info = self.client.get_symbol_info(symbol)
            for f in info["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    step = float(f["stepSize"])
                    precision = len(f["stepSize"].rstrip("0").split(".")[-1]) if "." in f["stepSize"] else 0
                    quantity = round(quantity - (quantity % step), precision)
                    return f"{quantity:.{precision}f}"
        except Exception:
            pass
        return str(quantity)

    def _map_status(self, binance_status: str) -> OrderStatus:
        mapping = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PENDING,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED,
        }
        return mapping.get(binance_status, OrderStatus.PENDING)
