import asyncio
from config.settings import (
    TRACKED_SYMBOLS,
    OPPORTUNITY_DEDUP_TTL_TICKS,
    PRICE_BUCKET_SCALE,
    get_venue_symbol,
)
from core.queue import market_queue
from core.state import update_state, get_state
from signals.spread import get_best_opportunity
from data_ingestion.binance_ws import binance_stream
from data_ingestion.coinbase_ws import coinbase_stream
from data_ingestion.okx_ws import okx_stream
from api.server import start_api_server, broadcast_data, record_opportunity

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

_EXCHANGES = ("binance", "okx", "coinbase")
_SYMBOL_TO_ID = {symbol: index for index, symbol in enumerate(TRACKED_SYMBOLS)}
_ID_TO_SYMBOL = {index: symbol for symbol, index in _SYMBOL_TO_ID.items()}
_EXCHANGE_TO_ID = {exchange: index for index, exchange in enumerate(_EXCHANGES)}
_ID_TO_EXCHANGE = {index: exchange for exchange, index in _EXCHANGE_TO_ID.items()}


def _build_compact_key(symbol_id, opportunity):
    buy_exchange_id = _EXCHANGE_TO_ID[opportunity["buy_exchange"]]
    sell_exchange_id = _EXCHANGE_TO_ID[opportunity["sell_exchange"]]
    mid_price = (opportunity["sell_bid"] + opportunity["buy_ask"]) * 0.5
    price_bucket = int(mid_price * PRICE_BUCKET_SCALE)
    return (symbol_id, buy_exchange_id, sell_exchange_id, price_bucket)


async def consumer_loop():
    ttl = OPPORTUNITY_DEDUP_TTL_TICKS
    dedup_cache = {}
    wheel = [set() for _ in range(ttl)]
    tick = 0

    while True:
        data = await market_queue.get()
        tick += 1
        try:
            expire_slot = tick % ttl
            for expired_key in wheel[expire_slot]:
                dedup_cache.pop(expired_key, None)
            wheel[expire_slot].clear()

            update_state(data)
            symbol_state = get_state(data["symbol"])
            opportunity = get_best_opportunity(symbol_state)
            if opportunity:
                symbol_id = _SYMBOL_TO_ID[data["symbol"]]
                key = _build_compact_key(symbol_id, opportunity)
                existing = dedup_cache.get(key)
                expiry_slot = (tick + ttl) % ttl

                if existing:
                    old_slot = existing[1]
                    wheel[old_slot].discard(key)
                    existing[0] = tick
                    existing[1] = expiry_slot
                    wheel[expiry_slot].add(key)
                else:
                    dedup_cache[key] = [tick, expiry_slot]
                    wheel[expiry_slot].add(key)

                    symbol_name = _ID_TO_SYMBOL[symbol_id]
                    opportunity["symbol"] = symbol_name
                    opportunity["buy_exchange"] = _ID_TO_EXCHANGE[key[1]]
                    opportunity["sell_exchange"] = _ID_TO_EXCHANGE[key[2]]

                    record_opportunity(opportunity)
                    await broadcast_data(opportunity)
                    print(
                        "ARB | "
                        f"{symbol_name} | "
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
        producers.append(okx_stream(market_queue, symbol, get_venue_symbol("okx", symbol)))
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
