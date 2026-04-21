TRACKED_SYMBOLS = ("btcusdt",)

BINANCE_WS_URL_TEMPLATE = "wss://stream.binance.com:9443/ws/{symbol}@bookTicker"
OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

DEFAULT_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 60

VENUE_FEES_BPS = {
    "binance": 1.0,
    "okx": 1.0,
    "coinbase": 2.0,
}

SLIPPAGE_BPS = 0.5
MIN_NET_SPREAD_BPS = 0.5

# Deduplicate identical opportunities for a short tick window.
OPPORTUNITY_DEDUP_TTL_TICKS = 10
PRICE_BUCKET_SCALE = 100

# In-process emitted opportunity history for warm-load.
OPPORTUNITY_HISTORY_CAPACITY = 500
OPPORTUNITY_WARMLOAD_DEFAULT_LIMIT = 80
OPPORTUNITY_WARMLOAD_MAX_LIMIT = 500

VENUE_SYMBOL_MAPS = {
    "binance": {
        "btcusdt": "btcusdt",
    },
    "okx": {
        "btcusdt": "BTC-USDT",
    },
    "coinbase": {
        "btcusdt": "BTC-USD",
    },
}


def get_venue_symbol(venue, symbol):
    return VENUE_SYMBOL_MAPS[venue][symbol.lower()]
