TRACKED_SYMBOLS = ("btcusdt",)

BINANCE_WS_URL_TEMPLATE = "wss://stream.binance.com:9443/ws/{symbol}@bookTicker"
OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

DEFAULT_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 60

VENUE_FEES_BPS = {
    "binance": 10.0,
    "okx": 10.0,
    "coinbase": 15.0,
}

SLIPPAGE_BPS = 5.0
MIN_NET_SPREAD_BPS = 5.0

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
