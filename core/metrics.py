import time
from collections import defaultdict, deque

WINDOW_SECONDS = 60

_market_events = defaultdict(deque)
_api_events = defaultdict(deque)


def _trim(bucket, now):
    cutoff = now - WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()


def record_market_event(exchange):
    now = time.time()
    bucket = _market_events[str(exchange or "unknown")]
    bucket.append(now)
    _trim(bucket, now)


def record_api_request(route):
    now = time.time()
    bucket = _api_events[str(route or "unknown")]
    bucket.append(now)
    _trim(bucket, now)


def get_metrics_snapshot():
    now = time.time()

    market_by_exchange = {}
    market_total = 0
    for exchange, bucket in _market_events.items():
        _trim(bucket, now)
        count = len(bucket)
        market_by_exchange[exchange] = count
        market_total += count

    api_by_route = {}
    api_total = 0
    for route, bucket in _api_events.items():
        _trim(bucket, now)
        count = len(bucket)
        api_by_route[route] = count
        api_total += count

    return {
        "window_seconds": WINDOW_SECONDS,
        "market_requests_per_min": market_total,
        "market_by_exchange": market_by_exchange,
        "api_requests_per_min": api_total,
        "api_by_route": api_by_route,
        "timestamp": now,
    }
