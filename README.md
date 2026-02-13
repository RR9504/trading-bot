# Trading Bot

Automatiserad trading-bot med stöd för svenska börsen (Avanza), US-aktier (Alpaca) och krypto (Binance).

## Features

- Pluginbaserat strategisystem (RSI, MACD, Bollinger Bands, Momentum)
- Paper trading för riskfri testning
- Riskhantering med stop-loss och positionslimiter
- Stöd för flera marknader och brokers
- Loggning av alla trades och signaler
- Web dashboard med realtidsövervakning

## Kom igång

```bash
pip install -r requirements.txt
cp config/settings.yaml.example config/settings.yaml
# Redigera settings.yaml med dina API-nycklar
python src/main.py
```

## Strategier

| Strategi | Beskrivning |
|----------|-------------|
| RSI | Köp vid översålt (RSI < 30), sälj vid överköpt (RSI > 70) |
| MACD | Köp/sälj vid MACD crossover |
| Bollinger Bands | Mean reversion vid band-kontakt |
| Momentum | Trendföljande baserat på prismomentum |

## Dashboard

Starta dashboarden:

```bash
python src/dashboard/app.py
```

Öppna `http://localhost:5000` i din webbläsare. Dashboarden visar:
- Equity-kurva i realtid
- Öppna positioner med P&L
- Trade-historik
- Starta/stoppa boten direkt från UI:t

## Byggt med Claude
