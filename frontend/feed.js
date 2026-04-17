const WS_PROTOCOL = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_URL = `${WS_PROTOCOL}//${window.location.host}/ws`;
const BUFFER_LIMIT = 500;
const RAW_LIMIT = 200;

const filters = {
    symbol: document.getElementById("symbol-filter"),
    buy: document.getElementById("buy-filter"),
    sell: document.getElementById("sell-filter"),
    minNetBps: document.getElementById("min-net-bps"),
    minGross: document.getElementById("min-gross"),
    maxRows: document.getElementById("max-rows"),
    sort: document.getElementById("sort-mode"),
    clear: document.getElementById("clear-filters"),
};

const feedBody = document.getElementById("feed-body");
const feedStats = document.getElementById("feed-stats");
const rawLog = document.getElementById("raw-log");
const toggleRaw = document.getElementById("toggle-raw");
const clearRaw = document.getElementById("clear-raw");

let ws = null;
let reconnectDelayMs = 1000;
let reconnectTimer = null;
let renderScheduled = false;
let rawOpen = false;

const events = [];
const rawEntries = [];

function connect() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => {
        reconnectDelayMs = 1000;
    };
    ws.onmessage = (event) => {
        try {
            const payload = JSON.parse(event.data);
            ingest(payload, event.data);
        } catch (err) {
            appendRaw(`PARSE_ERROR ${String(err)}\n${event.data}`);
        }
    };
    ws.onclose = () => scheduleReconnect();
    ws.onerror = () => {
        if (ws && ws.readyState <= WebSocket.OPEN) {
            ws.close();
        }
    };
}

function scheduleReconnect() {
    if (reconnectTimer) {
        return;
    }
    reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        connect();
    }, reconnectDelayMs);
    reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
}

function ingest(payload, rawText) {
    payload._receivedAt = Date.now();
    events.push(payload);
    if (events.length > BUFFER_LIMIT) {
        events.shift();
    }
    appendRaw(rawText);
    scheduleRender();
}

function appendRaw(entry) {
    rawEntries.push(entry);
    if (rawEntries.length > RAW_LIMIT) {
        rawEntries.shift();
    }
    if (rawOpen) {
        rawLog.textContent = rawEntries.join("\n");
    }
}

function scheduleRender() {
    if (renderScheduled) {
        return;
    }
    renderScheduled = true;
    window.requestAnimationFrame(render);
}

function render() {
    renderScheduled = false;
    const maxRows = clampInt(filters.maxRows.value, 10, 500, 50);
    const minNetBps = numberOrZero(filters.minNetBps.value);
    const minGross = numberOrZero(filters.minGross.value);
    const symbolQuery = normalize(filters.symbol.value);
    const buyQuery = normalize(filters.buy.value);
    const sellQuery = normalize(filters.sell.value);

    const filtered = events.filter((event) => {
        const symbol = normalize(event.symbol);
        const buy = normalize(event.buy_exchange);
        const sell = normalize(event.sell_exchange);
        const netBps = Number(event.net_spread_bps) || 0;
        const gross = Number(event.gross_spread) || 0;

        return symbol.includes(symbolQuery)
            && buy.includes(buyQuery)
            && sell.includes(sellQuery)
            && netBps >= minNetBps
            && gross >= minGross;
    });

    sortEvents(filtered, filters.sort.value);
    const visible = filtered.slice(0, maxRows);

    const fragment = document.createDocumentFragment();
    for (const event of visible) {
        fragment.appendChild(buildRow(event));
    }
    feedBody.replaceChildren(fragment);
    feedStats.textContent = `Events: ${events.length} | Showing: ${visible.length}`;
}

function sortEvents(list, mode) {
    if (mode === "net_bps") {
        list.sort((a, b) => (Number(b.net_spread_bps) || 0) - (Number(a.net_spread_bps) || 0));
        return;
    }
    if (mode === "symbol") {
        list.sort((a, b) => String(a.symbol || "").localeCompare(String(b.symbol || "")));
        return;
    }
    list.sort((a, b) => (b._receivedAt || 0) - (a._receivedAt || 0));
}

function buildRow(event) {
    const tr = document.createElement("tr");
    appendCell(tr, formatTime(event._receivedAt));
    appendCell(tr, String(event.symbol || "").toUpperCase());
    appendCell(tr, event.buy_exchange || "-");
    appendCell(tr, toFixedOrDash(event.buy_ask));
    appendCell(tr, event.sell_exchange || "-");
    appendCell(tr, toFixedOrDash(event.sell_bid));
    appendCell(tr, toFixedOrDash(event.gross_spread), "positive");
    appendCell(tr, toFixedOrDash(event.net_spread_bps), "positive");
    return tr;
}

function appendCell(tr, value, className) {
    const td = document.createElement("td");
    td.textContent = value;
    if (className) {
        td.classList.add(className);
    }
    tr.appendChild(td);
}

function toFixedOrDash(value) {
    return Number.isFinite(value) ? value.toFixed(2) : "-";
}

function formatTime(ts) {
    const date = new Date(ts || Date.now());
    return date.toTimeString().split(" ")[0] + "." + String(date.getMilliseconds()).padStart(3, "0");
}

function normalize(value) {
    return String(value || "").trim().toLowerCase();
}

function numberOrZero(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function clampInt(value, min, max, fallback) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
        return fallback;
    }
    return Math.min(max, Math.max(min, parsed));
}

function clearFilters() {
    filters.symbol.value = "";
    filters.buy.value = "";
    filters.sell.value = "";
    filters.minNetBps.value = "0";
    filters.minGross.value = "0";
    filters.maxRows.value = "50";
    filters.sort.value = "newest";
    scheduleRender();
}

function bindEvents() {
    for (const control of [filters.symbol, filters.buy, filters.sell, filters.minNetBps, filters.minGross, filters.maxRows, filters.sort]) {
        control.addEventListener("input", scheduleRender);
        control.addEventListener("change", scheduleRender);
    }

    filters.clear.addEventListener("click", clearFilters);

    toggleRaw.addEventListener("click", () => {
        rawOpen = !rawOpen;
        rawLog.classList.toggle("open", rawOpen);
        toggleRaw.textContent = rawOpen ? "Hide Raw Stream" : "Show Raw Stream";
        if (rawOpen) {
            rawLog.textContent = rawEntries.join("\n");
        }
    });

    clearRaw.addEventListener("click", () => {
        rawEntries.length = 0;
        rawLog.textContent = "";
    });
}

window.addEventListener("beforeunload", () => {
    if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
    }
    if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close();
    }
});

bindEvents();
connect();
scheduleRender();
