import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokers.base import OrderSide
from src.brokers.paper_broker import PaperBroker
from src.core.portfolio import Portfolio
from src.core.risk import RiskManager


def test_risk_manager_blocks_large_position():
    broker = PaperBroker(initial_balance=10000)
    risk = RiskManager(max_position_pct=0.10)
    # Försök köpa för mer än 10%
    can_buy, reason = risk.can_open_position(broker, "AAPL", 150.0, 100)
    assert not can_buy


def test_risk_manager_allows_small_position():
    broker = PaperBroker(initial_balance=100000)
    risk = RiskManager(max_position_pct=0.10)
    can_buy, reason = risk.can_open_position(broker, "AAPL", 150.0, 5)
    assert can_buy


def test_risk_manager_position_size():
    broker = PaperBroker(initial_balance=100000)
    risk = RiskManager(max_position_pct=0.10)
    qty = risk.calculate_position_size(broker, 150.0)
    assert qty == 66  # 10000 / 150 = 66


def test_risk_manager_stop_loss():
    broker = PaperBroker(initial_balance=100000)
    broker.place_order("AAPL", OrderSide.BUY, 10, 100.0)
    broker.update_prices({"AAPL": 90.0})  # -10% förlust
    risk = RiskManager(stop_loss_pct=0.05)
    to_sell = risk.check_stop_loss(broker)
    assert "AAPL" in to_sell


def test_portfolio_trade_recording():
    portfolio = Portfolio()
    portfolio.record_trade("AAPL", OrderSide.BUY, 10, 100.0)
    portfolio.record_trade("AAPL", OrderSide.SELL, 10, 120.0, pnl=200.0)
    assert portfolio.get_trade_count() == 2
    assert portfolio.get_total_pnl() == 200.0


def test_portfolio_win_rate():
    portfolio = Portfolio()
    portfolio.record_trade("AAPL", OrderSide.SELL, 10, 120.0, pnl=200.0)
    portfolio.record_trade("TSLA", OrderSide.SELL, 5, 80.0, pnl=-100.0)
    assert portfolio.get_win_rate() == 0.5
