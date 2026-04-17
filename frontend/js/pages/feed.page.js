import { RealtimeChannel } from "../core/ws-client.js";
import { animateNumber } from "../core/motion.js";
import { toFixedOrDash, formatTime, normalize, numberOrZero, clampInt } from "../core/format.js";

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
const feedPillDot = document.getElementById("feed-pill-dot");
const feedPillLabel = document.getElementById("feed-pill-label");

const channel = new RealtimeChannel("/ws");
const events = [];
const rawEntries = [];
let renderScheduled = false;
let rawOpen = false;
let shownCountTween = 0;

channel.onStatus(({ state }) => {
    if (state === "live") {
        setConnectionLabel("Live", "good");
        return;
    }
    if (state === "error") {
        setConnectionLabel("Error", "bad");
        return;
    }
    if (state === "reconnecting") {
        setConnectionLabel("Reconnecting", "warn");
        return;
    }
    setConnectionLabel("Connecting", "warn");
});

channel.onMessage((rawPayload) => {
    try {
        const payload = JSON.parse(rawPayload);
        payload._receivedAt = Date.now();
        events.push(payload);
        if (events.length > BUFFER_LIMIT) {
            events.shift();
        }
        appendRaw(rawPayload);
        scheduleRender();
    } catch (error) {
        appendRaw(`PARSE_ERROR ${String(error)}\n${rawPayload}`);
    }
});

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

    animateNumber(shownCountTween, visible.length, 220, (value) => {
        feedStats.textContent = `Events: ${events.length} | Showing: ${Math.round(value)}`;
    });
    shownCountTween = visible.length;
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
    tr.classList.add("row-enter");
    window.setTimeout(() => tr.classList.remove("row-enter"), 420);

    appendCell(tr, formatTime(event._receivedAt));
    appendCell(tr, String(event.symbol || "").toUpperCase(), "mono");
    appendCell(tr, event.buy_exchange || "-");
    appendCell(tr, toFixedOrDash(event.buy_ask), "mono");
    appendCell(tr, event.sell_exchange || "-");
    appendCell(tr, toFixedOrDash(event.sell_bid), "mono");
    appendCell(tr, toFixedOrDash(event.gross_spread), Number(event.gross_spread) >= 0 ? "positive" : "negative");
    appendCell(tr, toFixedOrDash(event.net_spread_bps), Number(event.net_spread_bps) >= 0 ? "positive" : "negative");
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

function setConnectionLabel(label, state) {
    feedPillLabel.textContent = label;
    feedPillDot.classList.remove("good", "bad", "pulse");
    if (state === "good") {
        feedPillDot.classList.add("good", "pulse");
        return;
    }
    if (state === "bad") {
        feedPillDot.classList.add("bad");
    }
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

window.addEventListener("beforeunload", () => channel.disconnect());
bindEvents();
setConnectionLabel("Connecting", "warn");
channel.connect();
scheduleRender();
