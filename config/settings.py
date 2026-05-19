EXCHANGES = [
    "binance",
    "coinbase",
    "kraken",
    "bybit",
    "bitget",
    "okx",
]

DEFAULT_SYMBOL = "btcusdt"
TOP_TRADED_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
)

BINANCE_WS_URL_TEMPLATE = "wss://stream.binance.com:9443/ws/{symbol}@bookTicker"
OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"
KRAKEN_WS_URL = "wss://ws.kraken.com/v2"
BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/spot"
BITGET_WS_URL = "wss://ws.bitget.com/v2/ws/public"

DEFAULT_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 60

VENUE_FEES_BPS = {
    "binance": 1.0,
    "okx": 1.0,
    "coinbase": 2.0,
    "kraken": 2.6,
    "bybit": 1.0,
    "bitget": 1.0,
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
        "ethusdt": "ethusdt",
        "solusdt": "solusdt",
        "xrpusdt": "xrpusdt",
        "adausdt": "adausdt",
        "dogeusdt": "dogeusdt",
    },
    "okx": {
        "btcusdt": "BTC-USDT",
        "ethusdt": "ETH-USDT",
        "solusdt": "SOL-USDT",
        "xrpusdt": "XRP-USDT",
        "adausdt": "ADA-USDT",
        "dogeusdt": "DOGE-USDT",
    },
    "coinbase": {
        "btcusdt": "BTC-USD",
        "ethusdt": "ETH-USD",
        "solusdt": "SOL-USD",
        "xrpusdt": "XRP-USD",
        "adausdt": "ADA-USD",
        "dogeusdt": "DOGE-USD",
    },
    "kraken": {
        "btcusdt": "BTC/USD",
        "ethusdt": "ETH/USD",
        "solusdt": "SOL/USD",
        "xrpusdt": "XRP/USD",
        "adausdt": "ADA/USD",
        "dogeusdt": "DOGE/USD",
    },
    "bybit": {
        "btcusdt": "BTCUSDT",
        "ethusdt": "ETHUSDT",
        "solusdt": "SOLUSDT",
        "xrpusdt": "XRPUSDT",
        "adausdt": "ADAUSDT",
        "dogeusdt": "DOGEUSDT",
    },
    "bitget": {
        "btcusdt": "BTCUSDT",
        "ethusdt": "ETHUSDT",
        "solusdt": "SOLUSDT",
        "xrpusdt": "XRPUSDT",
        "adausdt": "ADAUSDT",
        "dogeusdt": "DOGEUSDT",
    },
}


def get_venue_symbol(venue, symbol):
    return VENUE_SYMBOL_MAPS[venue][symbol.lower()]


def normalize_symbol(symbol):
    value = str(symbol or "").strip().replace("-", "").replace("/", "").upper()
    if not value:
        return DEFAULT_SYMBOL
    if value.endswith("USD") and not value.endswith("USDT"):
        value = f"{value}T"
    return value.lower()


def get_supported_symbols():
    return sorted({symbol for venue_map in VENUE_SYMBOL_MAPS.values() for symbol in venue_map.keys()})
