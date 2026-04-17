import asyncio
from config.settings import TRACKED_SYMBOLS, get_venue_symbol
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

async def consumer_loop():
    while True:
        data = await market_queue.get()
        try:
            update_state(data)
            symbol_state = get_state(data["symbol"])
            opportunity = get_best_opportunity(symbol_state)
            if opportunity:
                opportunity['symbol'] = data['symbol']
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
