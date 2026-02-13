import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokers.paper_broker import PaperBroker
from src.core.engine import TradingEngine
from src.core.risk import RiskManager
from src.data.fetcher import DataFetcher
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.bollinger_strategy import BollingerStrategy
from src.strategies.momentum_strategy import MomentumStrategy
from src.utils.logger import setup_logger

STRATEGIES = {
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger": BollingerStrategy,
    "momentum": MomentumStrategy,
}


def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    logger = setup_logger(
        level=config.get("logging", {}).get("level", "INFO"),
        trade_log=config.get("logging", {}).get("trade_log", "logs/trades.log"),
        signal_log=config.get("logging", {}).get("signal_log", "logs/signals.log"),
    )

    # Samla alla symboler
    symbols_config = config.get("symbols", {})
    symbols = []
    for market_symbols in symbols_config.values():
        symbols.extend(market_symbols)

    logger.info(f"Laddar konfiguration: mode={config['mode']}, strategi={config['strategy']}")

    # Broker
    if config["mode"] == "paper":
        paper_config = config.get("paper_trading", {})
        broker = PaperBroker(initial_balance=paper_config.get("initial_balance", 100000))
        logger.info(f"Paper trading aktiverat med {broker.cash:.0f} {paper_config.get('currency', 'SEK')}")
    else:
        logger.error("Live-trading inte implementerat ännu. Använd mode: paper")
        sys.exit(1)

    # Strategi
    strategy_name = config.get("strategy", "rsi")
    if strategy_name not in STRATEGIES:
        logger.error(f"Okänd strategi: {strategy_name}. Välj: {', '.join(STRATEGIES.keys())}")
        sys.exit(1)
    strategy = STRATEGIES[strategy_name]()

    # Riskhantering
    risk_config = config.get("risk", {})
    risk_manager = RiskManager(
        max_position_pct=risk_config.get("max_position_pct", 0.10),
        stop_loss_pct=risk_config.get("stop_loss_pct", 0.05),
        daily_loss_limit_pct=risk_config.get("daily_loss_limit_pct", 0.03),
        max_open_positions=risk_config.get("max_open_positions", 10),
    )

    # Engine
    data_fetcher = DataFetcher()
    engine = TradingEngine(
        broker=broker,
        strategy=strategy,
        risk_manager=risk_manager,
        data_fetcher=data_fetcher,
        symbols=symbols,
    )

    logger.info("=== Trading Bot Startad ===")
    logger.info(f"Strategi: {strategy_name} | Symboler: {len(symbols)} st")

    try:
        engine.run(interval_seconds=300)  # Kör var 5:e minut
    except KeyboardInterrupt:
        logger.info("Bot stoppad. Slutstatus:")
        engine._log_status()


if __name__ == "__main__":
    main()
