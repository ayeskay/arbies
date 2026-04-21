import asyncio
from config.settings import (
    TRACKED_SYMBOLS,
    OPPORTUNITY_DEDUP_TTL_TICKS,
    OPPORTUNITY_HASH_PRICE_DECIMALS,
    OPPORTUNITY_DEDUP_MAX_CACHE_SIZE,
    get_venue_symbol,
)
from core.queue import market_queue
from core.state import update_state, get_state
from signals.spread import get_best_opportunity
from data_ingestion.binance_ws import binance_stream
from data_ingestion.coinbase_ws import coinbase_stream
from data_ingestion.okx_ws import okx_stream
from api.server import start_api_server, broadcast_data

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


def _build_opportunity_key(symbol, opportunity):
    decimals = OPPORTUNITY_HASH_PRICE_DECIMALS
    return (
        symbol,
        opportunity["buy_exchange"],
        opportunity["sell_exchange"],
        round(float(opportunity["sell_bid"]), decimals),
        round(float(opportunity["buy_ask"]), decimals),
    )


def _tick_dedup_cache(dedup_cache):
    expired = []
    for key, entry in dedup_cache.items():
        entry["ttl_counter"] -= 1
        if entry["ttl_counter"] <= 0:
            expired.append(key)

    for key in expired:
        dedup_cache.pop(key, None)


def _ensure_cache_bound(dedup_cache):
    overflow = len(dedup_cache) - OPPORTUNITY_DEDUP_MAX_CACHE_SIZE
    if overflow <= 0:
        return
    # Trim oldest entries by last_seen_tick to keep cache memory bounded.
    oldest = sorted(dedup_cache.items(), key=lambda item: item[1]["last_seen_tick"])[:overflow]
    for key, _ in oldest:
        dedup_cache.pop(key, None)

async def consumer_loop():
    dedup_cache = {}
    tick = 0
    while True:
        data = await market_queue.get()
        tick += 1
        try:
            _tick_dedup_cache(dedup_cache)
            update_state(data)
            symbol_state = get_state(data["symbol"])
            opportunity = get_best_opportunity(symbol_state)
            if opportunity:
                opportunity['symbol'] = data['symbol']
                key = _build_opportunity_key(data["symbol"], opportunity)
                existing = dedup_cache.get(key)
                if existing:
                    existing["last_seen_tick"] = tick
                    existing["ttl_counter"] = OPPORTUNITY_DEDUP_TTL_TICKS
                else:
                    dedup_cache[key] = {
                        "last_seen_tick": tick,
                        "ttl_counter": OPPORTUNITY_DEDUP_TTL_TICKS,
                    }
                    _ensure_cache_bound(dedup_cache)
                    await broadcast_data(opportunity)
                    print(
                        "ARB | "
                        f"{data['symbol']} | "
                        f"BUY {opportunity['buy_exchange']} @ {opportunity['buy_ask']:.2f} | "
                        f"SELL {opportunity['sell_exchange']} @ {opportunity['sell_bid']:.2f} | "
                        f"Gross: {opportunity['gross_spread']:.2f} "
                        f"Net: {opportunity['net_spread']:.2f} | "
                        f"Net Bps: {opportunity['net_spread_bps']:.2f}"
                    )
        except Exception as exc:
            print(f"CONS | {data.get('symbol', '?')} | {type(exc).__name__}: {exc}")
        finally:
            market_queue.task_done()

async def main():
    producers = []
    for symbol in TRACKED_SYMBOLS:
        producers.append(
            binance_stream(market_queue, symbol, get_venue_symbol("binance", symbol))
        )
        producers.append(
            okx_stream(market_queue, symbol, get_venue_symbol("okx", symbol))
        )
        producers.append(
            coinbase_stream(market_queue, symbol, get_venue_symbol("coinbase", symbol))
        )

    producers.append(start_api_server())

    await asyncio.gather(*producers, consumer_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
