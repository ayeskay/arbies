import asyncio
import time

import orjson
import websockets

from config.settings import BITGET_WS_URL, DEFAULT_RECONNECT_DELAY, MAX_RECONNECT_DELAY


async def bitget_stream(queue, symbol, venue_symbol):
    delay = DEFAULT_RECONNECT_DELAY
    subscribe = {
        "op": "subscribe",
        "args": [
            {
                "instType": "SPOT",
                "channel": "ticker",
                "instId": venue_symbol.upper(),
            }
        ],
    }

    while True:
        try:
            async with websockets.connect(BITGET_WS_URL, ping_interval=20, close_timeout=5) as ws:
                delay = DEFAULT_RECONNECT_DELAY
                await ws.send(orjson.dumps(subscribe))
                while True:
                    msg = await ws.recv()
                    payload = orjson.loads(msg)
                    data_rows = payload.get("data") or []
                    for row in data_rows:
                        bid = float(row.get("bidPr", 0.0) or 0.0)
                        ask = float(row.get("askPr", 0.0) or 0.0)
                        if bid <= 0 or ask <= 0:
                            continue

                        normalized = {
                            "exchange": "bitget",
                            "symbol": symbol.lower(),
                            "bid": bid,
                            "ask": ask,
                            "bid_size": float(row.get("bidSz", 0.0) or 0.0),
                            "ask_size": float(row.get("askSz", 0.0) or 0.0),
                            "timestamp": time.time(),
                        }
                        await queue.put(normalized)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"WS | bitget | {symbol} | {type(exc).__name__}: {exc}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)
