import logging

import yfinance as yf
import pandas as pd

logger = logging.getLogger("trading-bot")


class DataFetcher:

    def get_historical(self, symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"Ingen data hittades för {symbol}")
        return df

    def get_current_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if data.empty:
            raise ValueError(f"Kunde inte hämta pris för {symbol}")
        return float(data["Close"].iloc[-1])

    def get_prices_bulk(self, symbols: list[str]) -> dict[str, float]:
        prices = {}
        for symbol in symbols:
            try:
                prices[symbol] = self.get_current_price(symbol)
            except ValueError:
                logger.warning(f"Ingen data för {symbol}")
            except Exception as e:
                logger.error(f"Fel vid hämtning av {symbol}: {e}")
        return prices
