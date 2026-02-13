import sys
import os
import json
import threading
from datetime import datetime

from flask import Flask, render_template, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import yaml
from src.brokers.paper_broker import PaperBroker
from src.core.engine import TradingEngine
from src.core.risk import RiskManager
from src.data.fetcher import DataFetcher
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.bollinger_strategy import BollingerStrategy
from src.strategies.momentum_strategy import MomentumStrategy
from src.utils.logger import setup_logger

app = Flask(__name__)

STRATEGIES = {
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger": BollingerStrategy,
    "momentum": MomentumStrategy,
}

engine = None
bot_thread = None
bot_running = False


def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def create_engine():
    config = load_config()
    setup_logger(
        level=config.get("logging", {}).get("level", "INFO"),
        trade_log=config.get("logging", {}).get("trade_log", "logs/trades.log"),
        signal_log=config.get("logging", {}).get("signal_log", "logs/signals.log"),
    )

    symbols = []
    for market_symbols in config.get("symbols", {}).values():
        symbols.extend(market_symbols)

    paper_config = config.get("paper_trading", {})
    broker = PaperBroker(initial_balance=paper_config.get("initial_balance", 100000))

    strategy_name = config.get("strategy", "rsi")
    strategy = STRATEGIES.get(strategy_name, RSIStrategy)()

    risk_config = config.get("risk", {})
    risk_manager = RiskManager(
        max_position_pct=risk_config.get("max_position_pct", 0.10),
        stop_loss_pct=risk_config.get("stop_loss_pct", 0.05),
        daily_loss_limit_pct=risk_config.get("daily_loss_limit_pct", 0.03),
        max_open_positions=risk_config.get("max_open_positions", 10),
    )

    return TradingEngine(
        broker=broker,
        strategy=strategy,
        risk_manager=risk_manager,
        data_fetcher=DataFetcher(),
        symbols=symbols,
    )


# --- Routes ---

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    global engine, bot_running
    if not engine:
        return jsonify({"status": "not_initialized", "bot_running": False})

    broker = engine.broker
    positions = broker.get_positions()
    pos_value = sum(p.market_value for p in positions.values())

    return jsonify({
        "bot_running": bot_running,
        "strategy": engine.strategy.__class__.__name__,
        "cash": round(broker.get_balance(), 2),
        "positions_value": round(pos_value, 2),
        "total_value": round(broker.get_balance() + pos_value, 2),
        "initial_balance": broker.initial_balance,
        "pnl": round(broker.get_balance() + pos_value - broker.initial_balance, 2),
        "pnl_pct": round((broker.get_balance() + pos_value - broker.initial_balance) / broker.initial_balance * 100, 2),
        "num_positions": len(positions),
        "total_trades": engine.portfolio.get_trade_count(),
        "win_rate": round(engine.portfolio.get_win_rate() * 100, 1),
        "symbols": engine.symbols,
    })


@app.route("/api/positions")
def api_positions():
    if not engine:
        return jsonify([])

    positions = []
    for symbol, pos in engine.broker.get_positions().items():
        positions.append({
            "symbol": symbol,
            "quantity": pos.quantity,
            "avg_price": round(pos.avg_price, 2),
            "current_price": round(pos.current_price, 2),
            "market_value": round(pos.market_value, 2),
            "pnl": round(pos.unrealized_pnl, 2),
            "pnl_pct": round(pos.unrealized_pnl_pct * 100, 2),
        })
    return jsonify(positions)


@app.route("/api/trades")
def api_trades():
    if not engine:
        return jsonify([])

    trades = []
    for t in reversed(engine.portfolio.trade_records[-50:]):
        trades.append({
            "symbol": t.symbol,
            "side": t.side.value,
            "quantity": t.quantity,
            "price": round(t.price, 2),
            "pnl": round(t.pnl, 2),
            "timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return jsonify(trades)


@app.route("/api/equity")
def api_equity():
    if not engine:
        return jsonify([])

    # Bygg equity-kurva från trades
    balance = engine.broker.initial_balance
    equity_curve = [{"time": "Start", "value": balance}]
    for t in engine.portfolio.trade_records:
        balance += t.pnl
        equity_curve.append({
            "time": t.timestamp.strftime("%H:%M:%S"),
            "value": round(balance, 2),
        })
    return jsonify(equity_curve)


@app.route("/api/start", methods=["POST"])
def api_start():
    global engine, bot_thread, bot_running
    if bot_running:
        return jsonify({"status": "already_running"})

    engine = create_engine()
    bot_running = True

    def run_bot():
        global bot_running
        while bot_running:
            try:
                engine.run_once()
            except Exception:
                pass
            import time
            time.sleep(60)

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global bot_running
    bot_running = False
    if engine:
        engine.stop()
    return jsonify({"status": "stopped"})


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    engine = create_engine()
    app.run(debug=True, host="0.0.0.0", port=5000)
