import asyncio
from config.settings import (
    DEFAULT_SYMBOL,
    EXCHANGES,
    OPPORTUNITY_DEDUP_TTL_TICKS,
    PRICE_BUCKET_SCALE,
    get_venue_symbol,
    normalize_symbol,
    get_supported_symbols,
)
from core.queue import market_queue
from core.metrics import record_market_event
from core.state import update_state, get_state
from signals.spread import get_best_opportunity
from data_ingestion.stream_factory import STREAM_BUILDERS
from api.server import start_api_server, broadcast_data, record_opportunity, register_runtime

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

def _build_compact_key(symbol, opportunity):
    mid_price = (opportunity["sell_bid"] + opportunity["buy_ask"]) * 0.5
    price_bucket = int(mid_price * PRICE_BUCKET_SCALE)
    return (
        symbol,
        opportunity["buy_exchange"],
        opportunity["sell_exchange"],
        price_bucket,
    )


class StreamOrchestrator:
    def __init__(self, queue):
        self.queue = queue
        self._active_symbol = normalize_symbol(DEFAULT_SYMBOL)
        self._tasks = {}
        self._lock = asyncio.Lock()

    def get_active_symbol(self):
        return self._active_symbol

    async def start(self):
        await self.set_symbol(self._active_symbol)

    async def set_symbol(self, symbol):
        next_symbol = normalize_symbol(symbol)

        async with self._lock:
            if next_symbol == self._active_symbol and self._tasks:
                return self._active_symbol

            if next_symbol not in get_supported_symbols():
                raise ValueError(f"Unsupported symbol: {symbol}")

            await self._stop_all_streams()
            self._start_symbol_streams(next_symbol)
            self._active_symbol = next_symbol
            print(f"STREAM | active symbol -> {self._active_symbol.upper()}")
            return self._active_symbol

    async def shutdown(self):
        async with self._lock:
            await self._stop_all_streams()

    def _start_symbol_streams(self, symbol):
        self._tasks = {}
        for exchange in EXCHANGES:
            stream_builder = STREAM_BUILDERS.get(exchange)
            if not stream_builder:
                continue
            try:
                venue_symbol = get_venue_symbol(exchange, symbol)
            except KeyError:
                continue

            task = asyncio.create_task(
                stream_builder(self.queue, symbol, venue_symbol),
                name=f"stream:{exchange}:{symbol}",
            )
            self._tasks[exchange] = task

    async def _stop_all_streams(self):
        if not self._tasks:
            return

        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def consumer_loop():
    ttl = OPPORTUNITY_DEDUP_TTL_TICKS
    dedup_cache = {}
    wheel = [set() for _ in range(ttl)]
    tick = 0

    while True:
        data = await market_queue.get()
        tick += 1
        try:
            record_market_event(data.get("exchange"))
            expire_slot = tick % ttl
            for expired_key in wheel[expire_slot]:
                dedup_cache.pop(expired_key, None)
            wheel[expire_slot].clear()

            update_state(data)
            symbol_state = get_state(data["symbol"])
            opportunity = get_best_opportunity(symbol_state)
            if opportunity:
                symbol_key = data["symbol"]
                key = _build_compact_key(symbol_key, opportunity)
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

                    symbol_name = symbol_key
                    opportunity["symbol"] = symbol_name

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
    orchestrator = StreamOrchestrator(market_queue)
    await orchestrator.start()

    register_runtime(
        get_symbol=orchestrator.get_active_symbol,
        set_symbol=orchestrator.set_symbol,
        supported_symbols=get_supported_symbols(),
        exchanges=EXCHANGES,
    )

    try:
        await asyncio.gather(start_api_server(), consumer_loop())
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
