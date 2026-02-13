import logging
import os


def setup_logger(level: str = "INFO", trade_log: str = "logs/trades.log",
                 signal_log: str = "logs/signals.log"):
    os.makedirs(os.path.dirname(trade_log), exist_ok=True)

    logger = logging.getLogger("trading-bot")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    # Console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(console)

    # Trade log
    trade_handler = logging.FileHandler(trade_log)
    trade_handler.setLevel(logging.INFO)
    trade_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(trade_handler)

    return logger
