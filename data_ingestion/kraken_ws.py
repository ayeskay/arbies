import asyncio
import time

import orjson
import websockets

from config.settings import DEFAULT_RECONNECT_DELAY, KRAKEN_WS_URL, MAX_RECONNECT_DELAY


def _extract_price(level):
    if isinstance(level, list) and level:
        return float(level[0] or 0.0)
    if isinstance(level, dict):
        return float(level.get("price", 0.0) or 0.0)
    return 0.0


def _extract_size(level):
    if isinstance(level, list) and len(level) > 1:
        return float(level[1] or 0.0)
    if isinstance(level, dict):
        return float(level.get("qty", 0.0) or 0.0)
    return 0.0


async def kraken_stream(queue, symbol, venue_symbol):
    delay = DEFAULT_RECONNECT_DELAY
    subscribe = {
        "method": "subscribe",
        "params": {
            "channel": "ticker",
            "symbol": [venue_symbol],
        },
    }

    while True:
        try:
            async with websockets.connect(KRAKEN_WS_URL, ping_interval=20, close_timeout=5) as ws:
                delay = DEFAULT_RECONNECT_DELAY
                await ws.send(orjson.dumps(subscribe))
                while True:
                    msg = await ws.recv()
                    payload = orjson.loads(msg)
                    if payload.get("channel") != "ticker":
                        continue

                    for row in payload.get("data", []):
                        bid = _extract_price(row.get("bid"))
                        ask = _extract_price(row.get("ask"))
                        if bid <= 0 or ask <= 0:
                            continue

                        normalized = {
                            "exchange": "kraken",
                            "symbol": symbol.lower(),
                            "bid": bid,
                            "ask": ask,
                            "bid_size": _extract_size(row.get("bid")),
                            "ask_size": _extract_size(row.get("ask")),
                            "timestamp": time.time(),
                        }
                        await queue.put(normalized)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"WS | kraken | {symbol} | {type(exc).__name__}: {exc}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)
