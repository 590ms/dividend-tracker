import yfinance as yf
import threading
import subprocess
from datetime import datetime, timedelta
from config import EUR_TICKER, STOCKS

class DataFetcher:
    def __init__(self, db):
        self.db      = db
        self.eur_usd = float(db.get('eur_usd', '1.09') or '1.09')

    def _to_eur(self, usd_val):
        rate = self.eur_usd if self.eur_usd else 1.09
        return usd_val / rate

    def fetch_all(self, tickers, on_complete=None):
        def _run():
            # EUR/USD rate first
            try:
                info = yf.Ticker(EUR_TICKER).info
                rate = (info.get('regularMarketPrice') or
                        info.get('bid') or self.eur_usd)
                if rate and 0.5 < float(rate) < 2.0:
                    self.eur_usd = float(rate)
                    self.db.set('eur_usd', rate)
            except Exception as e:
                print(f"[fetcher] EUR/USD: {e}")

            for tk in tickers:
                try:
                    info = yf.Ticker(tk).info
                    if not info or len(info) < 5:
                        continue
                    price = (info.get('regularMarketPrice') or
                             info.get('currentPrice') or
                             info.get('previousClose') or 0)
                    div   = info.get('dividendRate') or 0
                    yld   = info.get('dividendYield') or 0
                    ex_ts = info.get('exDividendDate')
                    ex_dt = (datetime.fromtimestamp(ex_ts).strftime('%Y-%m-%d')
                             if ex_ts else None)
                    self.db.cache_price(tk, float(price), float(div), float(yld), ex_dt)
                    print(f"[fetcher] {tk}: ${price:.2f}  div=${div:.2f}")
                except Exception as e:
                    print(f"[fetcher] {tk}: {e}")

            if on_complete:
                on_complete()

        threading.Thread(target=_run, daemon=True).start()

    def market_data(self):
        """All cached prices converted to EUR."""
        cache = self.db.get_cache()
        out   = {}
        for tk, row in cache.items():
            out[tk] = {
                'price':         self._to_eur(row.get('price_usd') or 0),
                'div_per_share': self._to_eur(row.get('div_usd') or 0),
                'div_yield':     row.get('div_yield') or 0,
                'ex_div_date':   row.get('ex_div_date'),
                'updated_at':    row.get('updated_at'),
            }
        return out


def notify(title: str, body: str):
    try:
        script = f'display notification "{body}" with title "{title}" sound name "Ping"'
        subprocess.run(['osascript', '-e', script], check=False, timeout=3)
    except Exception as e:
        print(f"[notify] {e}")


def upcoming_dividends(market_data: dict) -> list:
    today  = datetime.today().date()
    cutoff = today + timedelta(days=7)
    alerts = []
    for ticker, d in market_data.items():
        ex = d.get('ex_div_date')
        if not ex:
            continue
        try:
            ex_date = datetime.strptime(ex, '%Y-%m-%d').date()
            if today <= ex_date <= cutoff:
                alerts.append({'ticker': ticker, 'ex_date': str(ex_date)})
        except:
            pass
    return alerts
