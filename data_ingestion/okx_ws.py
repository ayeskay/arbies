import asyncio
import time

import orjson
import websockets

from config.settings import DEFAULT_RECONNECT_DELAY, MAX_RECONNECT_DELAY, OKX_WS_URL


async def okx_stream(queue, symbol, venue_symbol):
    delay = DEFAULT_RECONNECT_DELAY
    inst_id = venue_symbol
    subscribe = {
        "op": "subscribe",
        "args": [{"channel": "tickers", "instId": inst_id}],
    }

    while True:
        try:
            async with websockets.connect(OKX_WS_URL, ping_interval=20, close_timeout=5) as ws:
                delay = DEFAULT_RECONNECT_DELAY
                await ws.send(orjson.dumps(subscribe))
                while True:
                    msg = await ws.recv()
                    payload = orjson.loads(msg)
                    for item in payload.get("data", []):
                        normalized = {
                            "exchange": "okx",
                            "symbol": symbol.lower(),
                            "bid": float(item["bidPx"]),
                            "ask": float(item["askPx"]),
                            "bid_size": float(item["bidSz"]),
                            "ask_size": float(item["askSz"]),
                            "timestamp": time.time(),
                        }
                        await queue.put(normalized)
        except Exception as exc:
            print(f"WS | okx | {symbol} | {type(exc).__name__}: {exc}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)
