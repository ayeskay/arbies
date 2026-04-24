import asyncio
import orjson
import os
from collections import deque
from aiohttp import web
from core.metrics import get_metrics_snapshot, record_api_request
from config.settings import (
    DEFAULT_SYMBOL,
    OPPORTUNITY_HISTORY_CAPACITY,
    TOP_TRADED_SYMBOLS,
    OPPORTUNITY_WARMLOAD_DEFAULT_LIMIT,
    OPPORTUNITY_WARMLOAD_MAX_LIMIT,
    normalize_symbol,
)

connected_clients = set()
opportunity_history = deque(maxlen=OPPORTUNITY_HISTORY_CAPACITY)
_runtime_get_symbol = None
_runtime_set_symbol = None
_supported_symbols = []
_exchanges = []


def register_runtime(get_symbol, set_symbol, supported_symbols, exchanges):
    global _runtime_get_symbol, _runtime_set_symbol, _supported_symbols, _exchanges
    _runtime_get_symbol = get_symbol
    _runtime_set_symbol = set_symbol
    _supported_symbols = list(supported_symbols)
    _exchanges = list(exchanges)

async def health_handler(request):
    payload = {"status": "OK", "service": "Arbies Arbitrage Engine"}
    return web.Response(text=orjson.dumps(payload).decode('utf-8'), content_type='application/json')

async def state_handler(request):
    from core.state import _state
    return web.Response(text=orjson.dumps(_state).decode('utf-8'), content_type='application/json')


async def opportunities_handler(request):
    try:
        requested = int(request.query.get("limit", OPPORTUNITY_WARMLOAD_DEFAULT_LIMIT))
    except (TypeError, ValueError):
        requested = OPPORTUNITY_WARMLOAD_DEFAULT_LIMIT
    limit = max(1, min(requested, OPPORTUNITY_WARMLOAD_MAX_LIMIT))

    newest_first = list(reversed(opportunity_history))
    payload = newest_first[:limit]
    return web.Response(text=orjson.dumps(payload).decode("utf-8"), content_type="application/json")


async def metrics_handler(request):
    payload = get_metrics_snapshot()
    return web.Response(text=orjson.dumps(payload).decode("utf-8"), content_type="application/json")


async def symbols_handler(request):
    payload = {
        "default_symbol": DEFAULT_SYMBOL.upper(),
        "top_symbols": list(TOP_TRADED_SYMBOLS),
        "supported_symbols": [symbol.upper() for symbol in _supported_symbols],
        "exchanges": list(_exchanges),
    }
    return web.Response(text=orjson.dumps(payload).decode("utf-8"), content_type="application/json")


async def selected_symbol_handler(request):
    if request.method == "GET":
        active = DEFAULT_SYMBOL
        if _runtime_get_symbol:
            active = _runtime_get_symbol()
        payload = {
            "selected_symbol": str(active).upper(),
            "exchanges": list(_exchanges),
        }
        return web.Response(text=orjson.dumps(payload).decode("utf-8"), content_type="application/json")

    if _runtime_set_symbol is None:
        return web.Response(status=503, text=orjson.dumps({"error": "Runtime not ready"}).decode("utf-8"), content_type="application/json")

    body = await request.json()
    requested = normalize_symbol(body.get("symbol"))
    try:
        active = await _runtime_set_symbol(requested)
    except ValueError as exc:
        payload = {"error": str(exc)}
        return web.Response(status=400, text=orjson.dumps(payload).decode("utf-8"), content_type="application/json")

    payload = {
        "selected_symbol": str(active).upper(),
        "message": "Symbol stream updated",
    }
    return web.Response(text=orjson.dumps(payload).decode("utf-8"), content_type="application/json")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    try:
        async for msg in ws:
            pass # Ignore incoming messages
    finally:
        connected_clients.remove(ws)
    return ws


@web.middleware
async def api_metrics_middleware(request, handler):
    if request.path.startswith("/api/"):
        record_api_request(request.path)
    return await handler(request)

async def broadcast_data(data: dict):
    if not connected_clients:
        return
    message = orjson.dumps(data).decode('utf-8')
    clients = [client for client in connected_clients if not client.closed]
    if not clients:
        return
    results = await asyncio.gather(
        *(client.send_str(message) for client in clients),
        return_exceptions=True
    )
    for client, result in zip(clients, results):
        if isinstance(result, Exception):
            connected_clients.discard(client)


def record_opportunity(data: dict):
    opportunity_history.append(dict(data))

async def index_handler(request):
    return web.FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'index.html'))

def get_app():
    app = web.Application(middlewares=[api_metrics_middleware])

    # API Endpoints
    app.router.add_get('/api/health', health_handler)
    app.router.add_get('/api/state', state_handler)
    app.router.add_get('/api/opportunities', opportunities_handler)
    app.router.add_get('/api/metrics', metrics_handler)
    app.router.add_get('/api/symbols', symbols_handler)
    app.router.add_get('/api/symbol', selected_symbol_handler)
    app.router.add_post('/api/symbol', selected_symbol_handler)
    
    # WebSockets
    app.router.add_get('/ws', websocket_handler)
    
    # Frontend Routes
    app.router.add_get('/', index_handler)
    
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    app.router.add_static('/', frontend_dir, name='static')
    
    return app

async def start_api_server():
    app = get_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8090)
    await site.start()
    print("API Server | http://127.0.0.1:8090")
    print("Test Endpoints | http://127.0.0.1:8090/test.html")
