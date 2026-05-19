import asyncio
import time

import orjson
import websockets

from config.settings import COINBASE_WS_URL, DEFAULT_RECONNECT_DELAY, MAX_RECONNECT_DELAY


async def coinbase_stream(queue, symbol, venue_symbol):
    delay = DEFAULT_RECONNECT_DELAY
    subscribe = {
        "type": "subscribe",
        "channels": [
            {
                "name": "ticker",
                "product_ids": [venue_symbol],
            }
        ],
    }

    while True:
        try:
            async with websockets.connect(COINBASE_WS_URL, ping_interval=20, close_timeout=5) as ws:
                delay = DEFAULT_RECONNECT_DELAY
                await ws.send(orjson.dumps(subscribe))
                while True:
                    msg = await ws.recv()
                    payload = orjson.loads(msg)
                    if payload.get("type") != "ticker":
                        continue
                    if payload.get("product_id") != venue_symbol:
                        continue

                    normalized = {
                        "exchange": "coinbase",
                        "symbol": symbol.lower(),
                        "bid": float(payload["best_bid"]),
                        "ask": float(payload["best_ask"]),
                        "bid_size": float(payload.get("best_bid_size", 0.0)),
                        "ask_size": float(payload.get("best_ask_size", 0.0)),
                        "timestamp": time.time(),
                    }
                    await queue.put(normalized)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"WS | coinbase | {symbol} | {type(exc).__name__}: {exc}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)
