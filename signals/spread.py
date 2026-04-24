from config.settings import MIN_NET_SPREAD_BPS, SLIPPAGE_BPS, VENUE_FEES_BPS


def get_best_metrics(exchanges):
    if not exchanges:
        return 0.0, 0.0, 0.0
    best_bid = max(ex["bid"] for ex in exchanges.values())
    best_ask = min(ex["ask"] for ex in exchanges.values())
    return best_bid, best_ask, best_bid - best_ask


def get_best_opportunity(exchanges):
    if len(exchanges) < 2:
        return None

    best_bid_exchange, best_bid = max(
        exchanges.items(), key=lambda item: item[1]["bid"]
    )
    best_ask_exchange, best_ask = min(
        exchanges.items(), key=lambda item: item[1]["ask"]
    )

    if best_bid_exchange == best_ask_exchange:
        return None

    gross_spread = best_bid["bid"] - best_ask["ask"]
    if gross_spread <= 0:
        return None

    buy_fee_bps = VENUE_FEES_BPS.get(best_ask_exchange, 0.0)
    sell_fee_bps = VENUE_FEES_BPS.get(best_bid_exchange, 0.0)
    total_cost_bps = buy_fee_bps + sell_fee_bps + SLIPPAGE_BPS
    gross_spread_bps = (gross_spread / best_ask["ask"]) * 10000 if best_ask["ask"] else 0.0
    net_spread_bps = gross_spread_bps - total_cost_bps
    if net_spread_bps < MIN_NET_SPREAD_BPS:
        return None

    net_spread = best_ask["ask"] * (net_spread_bps / 10000)
    spread_pct = (net_spread / best_ask["ask"]) * 100 if best_ask["ask"] else 0.0
    return {
        "buy_exchange": best_ask_exchange,
        "sell_exchange": best_bid_exchange,
        "buy_ask": best_ask["ask"],
        "sell_bid": best_bid["bid"],
        "buy_ask_size": best_ask.get("ask_size", 0.0),
        "sell_bid_size": best_bid.get("bid_size", 0.0),
        "gross_spread": gross_spread,
        "net_spread": net_spread,
        "gross_spread_bps": gross_spread_bps,
        "net_spread_bps": net_spread_bps,
        "spread_pct": spread_pct,
        "timestamp": max(best_bid.get("timestamp", 0.0), best_ask.get("timestamp", 0.0)),
    }
