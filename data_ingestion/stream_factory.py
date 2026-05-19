from data_ingestion.binance_ws import binance_stream
from data_ingestion.bitget_ws import bitget_stream
from data_ingestion.bybit_ws import bybit_stream
from data_ingestion.coinbase_ws import coinbase_stream
from data_ingestion.kraken_ws import kraken_stream
from data_ingestion.okx_ws import okx_stream

STREAM_BUILDERS = {
    "binance": binance_stream,
    "coinbase": coinbase_stream,
    "kraken": kraken_stream,
    "bybit": bybit_stream,
    "bitget": bitget_stream,
    "okx": okx_stream,
}
