import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokers.base import OrderSide, OrderStatus
from src.brokers.paper_broker import PaperBroker


def test_paper_broker_initial_balance():
    broker = PaperBroker(initial_balance=50000)
    assert broker.get_balance() == 50000


def test_paper_broker_buy():
    broker = PaperBroker(initial_balance=10000)
    order = broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    assert order.status == OrderStatus.FILLED
    assert broker.get_balance() == 10000 - (10 * 150)
    assert "AAPL" in broker.get_positions()
    assert broker.get_positions()["AAPL"].quantity == 10


def test_paper_broker_sell():
    broker = PaperBroker(initial_balance=10000)
    broker.place_order("AAPL", OrderSide.BUY, 10, 100.0)
    order = broker.place_order("AAPL", OrderSide.SELL, 10, 120.0)
    assert order.status == OrderStatus.FILLED
    assert broker.get_balance() == 10000 - 1000 + 1200
    assert "AAPL" not in broker.get_positions()


def test_paper_broker_insufficient_funds():
    broker = PaperBroker(initial_balance=100)
    order = broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    assert order.status == OrderStatus.REJECTED


def test_paper_broker_sell_without_position():
    broker = PaperBroker(initial_balance=10000)
    order = broker.place_order("AAPL", OrderSide.SELL, 10, 150.0)
    assert order.status == OrderStatus.REJECTED


def test_paper_broker_total_value():
    broker = PaperBroker(initial_balance=10000)
    broker.place_order("AAPL", OrderSide.BUY, 10, 100.0)
    broker.update_prices({"AAPL": 120.0})
    assert broker.get_total_value() == 9000 + (10 * 120)
