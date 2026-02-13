import sys
import os
import secrets
import logging
import threading
import time
import functools
from datetime import datetime

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# Rate limiting
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

# Audit logger
audit_log = logging.getLogger("audit")

STRATEGIES = {
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger": BollingerStrategy,
    "momentum": MomentumStrategy,
}

engine = None
bot_thread = None
bot_running = False

DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.environ.get("DASHBOARD_PASS")

if not DASHBOARD_PASS:
    DASHBOARD_PASS = secrets.token_urlsafe(16)
    print(f"\n{'='*50}")
    print(f"  GENERERAT DASHBOARD-LÖSENORD")
    print(f"  Användare: {DASHBOARD_USER}")
    print(f"  Lösenord:  {DASHBOARD_PASS}")
    print(f"  Sätt DASHBOARD_PASS som miljövariabel för permanent lösenord")
    print(f"{'='*50}\n")


# --- Security headers ---

@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# --- Auth ---

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if secrets.compare_digest(username, DASHBOARD_USER) and secrets.compare_digest(password, DASHBOARD_PASS):
            session["authenticated"] = True
            session.permanent = True
            audit_log.warning(f"LOGIN OK från {request.remote_addr}")
            return redirect(url_for("index"))
        audit_log.warning(f"LOGIN MISSLYCKAT från {request.remote_addr} (user={username})")
        return render_template("login.html", error="Fel användarnamn eller lösenord"), 401
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    audit_log.warning(f"LOGOUT från {request.remote_addr}")
    session.clear()
    return redirect(url_for("login"))


# --- Config ---

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
@login_required
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
@login_required
@limiter.limit("30 per minute")
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
@login_required
@limiter.limit("30 per minute")
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
@login_required
@limiter.limit("30 per minute")
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
@login_required
@limiter.limit("30 per minute")
def api_equity():
    if not engine:
        return jsonify([])

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
@login_required
@limiter.limit("5 per minute")
def api_start():
    global engine, bot_thread, bot_running
    if bot_running:
        return jsonify({"status": "already_running"})

    audit_log.warning(f"BOT STARTAD av {request.remote_addr}")
    engine = create_engine()
    bot_running = True

    def run_bot():
        global bot_running
        bot_logger = logging.getLogger("trading-bot")
        while bot_running:
            try:
                engine.run_once()
            except Exception as e:
                bot_logger.error(f"Bot-cykel misslyckades: {e}")
            time.sleep(60)

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def api_stop():
    global bot_running
    audit_log.warning(f"BOT STOPPAD av {request.remote_addr}")
    bot_running = False
    if engine:
        engine.stop()
    return jsonify({"status": "stopped"})


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    engine = create_engine()
    app.run(debug=False, host="127.0.0.1", port=5000)
