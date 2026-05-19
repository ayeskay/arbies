import asyncio
import websockets
import orjson
import time
from config.settings import BINANCE_WS_URL_TEMPLATE, DEFAULT_RECONNECT_DELAY, MAX_RECONNECT_DELAY

async def binance_stream(queue, symbol, venue_symbol):
    delay = DEFAULT_RECONNECT_DELAY
    ws_url = BINANCE_WS_URL_TEMPLATE.format(symbol=venue_symbol.lower())
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, close_timeout=5) as ws:
                delay = DEFAULT_RECONNECT_DELAY
                while True:
                    msg = await ws.recv()
                    data = orjson.loads(msg)
                    normalized = {
                        "exchange": "binance",
                        "symbol": data["s"].lower(),
                        "bid": float(data["b"]),
                        "ask": float(data["a"]),
                        "bid_size": float(data["B"]),
                        "ask_size": float(data["A"]),
                        "timestamp": time.time()
                    }
                    await queue.put(normalized)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"WS | binance | {symbol} | {type(exc).__name__}: {exc}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)
