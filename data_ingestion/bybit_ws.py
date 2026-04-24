import asyncio
import time

import orjson
import websockets

from config.settings import BYBIT_WS_URL, DEFAULT_RECONNECT_DELAY, MAX_RECONNECT_DELAY


async def bybit_stream(queue, symbol, venue_symbol):
    delay = DEFAULT_RECONNECT_DELAY
    topic = f"tickers.{venue_symbol.upper()}"
    subscribe = {"op": "subscribe", "args": [topic]}

    while True:
        try:
            async with websockets.connect(BYBIT_WS_URL, ping_interval=20, close_timeout=5) as ws:
                delay = DEFAULT_RECONNECT_DELAY
                await ws.send(orjson.dumps(subscribe))
                while True:
                    msg = await ws.recv()
                    payload = orjson.loads(msg)
                    if payload.get("topic") != topic:
                        continue

                    data = payload.get("data") or {}
                    bid = float(data.get("bid1Price", 0.0) or 0.0)
                    ask = float(data.get("ask1Price", 0.0) or 0.0)
                    if bid <= 0 or ask <= 0:
                        continue

                    normalized = {
                        "exchange": "bybit",
                        "symbol": symbol.lower(),
                        "bid": bid,
                        "ask": ask,
                        "bid_size": float(data.get("bid1Size", 0.0) or 0.0),
                        "ask_size": float(data.get("ask1Size", 0.0) or 0.0),
                        "timestamp": time.time(),
                    }
                    await queue.put(normalized)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"WS | bybit | {symbol} | {type(exc).__name__}: {exc}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)
