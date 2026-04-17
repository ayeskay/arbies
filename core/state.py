_state = {}

def update_state(data):
    symbol = data["symbol"]
    exchange = data["exchange"]
    if symbol not in _state:
        _state[symbol] = {}
    _state[symbol][exchange] = {
        "bid": data["bid"],
        "ask": data["ask"],
        "bid_size": data.get("bid_size", 0.0),
        "ask_size": data.get("ask_size", 0.0),
        "timestamp": data["timestamp"]
    }

def get_state(symbol):
    return _state.get(symbol, {})
