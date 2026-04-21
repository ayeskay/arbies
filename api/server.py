import asyncio
import orjson
import os
from collections import deque
from aiohttp import web
from config.settings import (
    OPPORTUNITY_HISTORY_CAPACITY,
    OPPORTUNITY_WARMLOAD_DEFAULT_LIMIT,
    OPPORTUNITY_WARMLOAD_MAX_LIMIT,
)

connected_clients = set()
opportunity_history = deque(maxlen=OPPORTUNITY_HISTORY_CAPACITY)

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
    app = web.Application()

    # API Endpoints
    app.router.add_get('/api/health', health_handler)
    app.router.add_get('/api/state', state_handler)
    app.router.add_get('/api/opportunities', opportunities_handler)
    
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
