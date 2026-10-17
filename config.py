STOCKS = {
    'VICI': {'name': 'VICI Properties',   'sector': 'REIT',             'weight': 0.08},
    'O':    {'name': 'Realty Income',      'sector': 'REIT',             'weight': 0.08},
    'KO':   {'name': 'Coca-Cola',          'sector': 'Consumer Staples', 'weight': 0.09},
    'NEE':  {'name': 'NextEra Energy',     'sector': 'Utilities',        'weight': 0.08},
    'PEP':  {'name': 'PepsiCo',            'sector': 'Consumer Staples', 'weight': 0.08},
    'JNJ':  {'name': 'Johnson & Johnson',  'sector': 'Healthcare',       'weight': 0.09},
    'CVX':  {'name': 'Chevron',            'sector': 'Energy',           'weight': 0.08},
    'PG':   {'name': 'Procter & Gamble',   'sector': 'Consumer Staples', 'weight': 0.08},
    'ABBV': {'name': 'AbbVie',             'sector': 'Healthcare',       'weight': 0.08},
    'JPM':  {'name': 'JPMorgan Chase',     'sector': 'Financials',       'weight': 0.08},
    'V':    {'name': 'Visa',               'sector': 'Payments',         'weight': 0.09},
    'MSFT': {'name': 'Microsoft',          'sector': 'Technology',       'weight': 0.09},
}

MONTHLY_INVEST  = 150
DEFAULT_GOAL    = 500
REFRESH_SECONDS = 300       # 5-minute auto-refresh
DB_FILE         = "dividend_tracker.db"
EUR_TICKER      = "EURUSD=X"

SECTOR_COLORS = {
    'Consumer Staples': '#1D9E75',
    'Healthcare':       '#378ADD',
    'Energy':           '#EF9F27',
    'REIT':             '#7F77DD',
    'Technology':       '#D85A30',
    'Utilities':        '#639922',
    'Financials':       '#888780',
    'Payments':         '#D4537E',
}
