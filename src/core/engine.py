import logging
import time

from src.brokers.base import BaseBroker, OrderSide
from src.core.portfolio import Portfolio
from src.core.risk import RiskManager
from src.data.fetcher import DataFetcher
from src.strategies.base import BaseStrategy, Signal

logger = logging.getLogger("trading-bot")


class TradingEngine:

    def __init__(self, broker: BaseBroker, strategy: BaseStrategy, risk_manager: RiskManager,
                 data_fetcher: DataFetcher, symbols: list[str]):
        self.broker = broker
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.data_fetcher = data_fetcher
        self.symbols = symbols
        self.portfolio = Portfolio()
        self.running = False

    def run_once(self):
        logger.info("=== Kör analyscykel ===")

        # Uppdatera priser
        prices = self.data_fetcher.get_prices_bulk(self.symbols)
        if hasattr(self.broker, "update_prices"):
            self.broker.update_prices(prices)

        # Kolla stop-loss
        stop_loss_symbols = self.risk_manager.check_stop_loss(self.broker)
        for symbol in stop_loss_symbols:
            pos = self.broker.get_positions().get(symbol)
            if pos:
                logger.warning(f"STOP-LOSS: Säljer {symbol} (förlust: {pos.unrealized_pnl_pct:.1%})")
                order = self.broker.place_order(symbol, OrderSide.SELL, pos.quantity, prices.get(symbol, pos.current_price))
                if order.status.value == "filled":
                    pnl = (prices.get(symbol, pos.current_price) - pos.avg_price) * pos.quantity
                    self.portfolio.record_trade(symbol, OrderSide.SELL, pos.quantity, prices.get(symbol, pos.current_price), pnl)

        # Analysera varje symbol
        for symbol in self.symbols:
            try:
                df = self.data_fetcher.get_historical(symbol)
                signal = self.strategy.analyze(df, symbol)
                self._execute_signal(signal, symbol, prices.get(symbol, 0))
            except Exception as e:
                logger.error(f"Fel vid analys av {symbol}: {e}")

        self._log_status()

    def _execute_signal(self, signal: Signal, symbol: str, current_price: float):
        if current_price <= 0:
            return

        if signal == Signal.BUY:
            positions = self.broker.get_positions()
            if symbol in positions:
                return  # Redan i position

            quantity = self.risk_manager.calculate_position_size(self.broker, current_price)
            if quantity <= 0:
                return

            can_buy, reason = self.risk_manager.can_open_position(self.broker, symbol, current_price, quantity)
            if not can_buy:
                logger.info(f"Riskhantering blockerade köp av {symbol}: {reason}")
                return

            order = self.broker.place_order(symbol, OrderSide.BUY, quantity, current_price)
            if order.status.value == "filled":
                logger.info(f"KÖPT {quantity} st {symbol} @ {current_price:.2f}")
                self.portfolio.record_trade(symbol, OrderSide.BUY, quantity, current_price)

        elif signal == Signal.SELL:
            positions = self.broker.get_positions()
            if symbol not in positions:
                return

            pos = positions[symbol]
            order = self.broker.place_order(symbol, OrderSide.SELL, pos.quantity, current_price)
            if order.status.value == "filled":
                pnl = (current_price - pos.avg_price) * pos.quantity
                logger.info(f"SÅLT {pos.quantity} st {symbol} @ {current_price:.2f} (P&L: {pnl:+.2f})")
                self.portfolio.record_trade(symbol, OrderSide.SELL, pos.quantity, current_price, pnl)

    def _log_status(self):
        total = self.broker.get_balance()
        positions = self.broker.get_positions()
        pos_value = sum(p.market_value for p in positions.values())
        total_value = total + pos_value

        logger.info(f"Kapital: {total:.0f} | Positioner: {pos_value:.0f} | "
                     f"Totalt: {total_value:.0f} | Trades: {self.portfolio.get_trade_count()}")

    def run(self, interval_seconds: int = 60):
        self.running = True
        logger.info(f"Trading-bot startad med strategi: {self.strategy.__class__.__name__}")
        logger.info(f"Bevakar: {', '.join(self.symbols)}")

        while self.running:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Bot stoppad av användaren")
                self.running = False
            except Exception as e:
                logger.error(f"Oväntat fel: {e}")
            time.sleep(interval_seconds)

    def stop(self):
        self.running = False
