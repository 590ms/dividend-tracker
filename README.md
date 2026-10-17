# Dividend Tracker

A desktop app for tracking a dividend stock portfolio. It shows live portfolio value and dividend income, logs monthly purchases, and projects future income. Built with Python and CustomTkinter, with live market data from Yahoo Finance (yfinance).

## Features

- **Dashboard:** live portfolio value, dividend income and progress toward a monthly income goal
- **Purchases:** add buys manually, or log a monthly AutoInvest split across the portfolio at today's live prices (similar to Trading 212's feature)
- **Projections:** estimated future income at 6 months, 1, 2, 3, 5 and 10 years, with dividends reinvested or paid out as cash
- **Settings:** change the monthly income goal
- Prices refresh automatically every 5 minutes
- macOS notification when a stock has an ex-dividend date within 7 days
- Prices come in USD from Yahoo Finance and are converted to EUR automatically

## Tech stack

- Python 3
- CustomTkinter
- yfinance
- SQLite (local database)

## Setup

```bash
git clone https://github.com/590ms/dividend-tracker.git
cd dividend-tracker
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The first run creates a local `dividend_tracker.db` file in the project folder. Your data stays on your computer and is not part of this repository.

## Configuration

Edit `config.py` to change the stocks in the portfolio, their weights, the monthly investment amount, the default income goal and the refresh interval.

## Project structure

```
main.py       interface: dashboard, purchases, projections and settings
config.py     portfolio, weights and app settings
database.py   local SQLite storage
fetcher.py    market data from yfinance and ex-dividend notifications
```

## Notes

The ex-dividend notifications use macOS, so they are not available on other systems.
