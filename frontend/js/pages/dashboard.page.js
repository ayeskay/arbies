import { RealtimeChannel } from "../core/ws-client.js";
import { animateNumber } from "../core/motion.js";
import { toFixedOrDash, formatTime } from "../core/format.js";
import { getJson, postJson } from "../core/http-client.js";

const tbody = document.getElementById("arb-body");
const MAX_ROWS = 80;
const WARMLOAD_LIMIT = 80;
const STARTUP_DEDUP_MS = 3000;
const RECENT_KEY = "arbies.recentSymbols";
const QUICK_BUTTON_COUNT = 3;

const elConnectionStatus = document.getElementById("connection-status");
const elConnectionSubtext = document.getElementById("connection-subtext");
const elTotal = document.getElementById("total-opportunities");
const elBestNet = document.getElementById("best-net-bps");
const elBestSymbol = document.getElementById("best-symbol");
const elTopSymbol = document.getElementById("top-symbol");
const elTopSymbolCount = document.getElementById("top-symbol-count");
const elSymbolInput = document.getElementById("symbol-input");
const elApplySymbol = document.getElementById("apply-symbol");
const elSymbolSuggestions = document.getElementById("symbol-suggestions");
const elSelectedSymbol = document.getElementById("selected-symbol-label");
const elQuickButtons = document.getElementById("quick-buttons");
const elRecentSearches = document.getElementById("recent-searches");

const channel = new RealtimeChannel("/ws");
const pendingRows = [];
const symbolHitMap = new Map();
let supportedSymbols = [];
let topSymbols = [];
let selectedSymbol = "BTCUSDT";

const state = {
    total: 0,
    bestNetBps: Number.NEGATIVE_INFINITY,
    bestSymbol: "",
};

const metricTween = {
    total: 0,
    bestNet: 0,
};

let flushScheduled = false;
let startupDedupActive = true;
const startupKeys = new Set();

channel.onStatus(({ state: status, detail }) => {
    let kind = "metric-warn";
    if (status === "live") {
        kind = "metric-good";
    }
    if (status === "error") {
        kind = "metric-bad";
    }
    setConnectionState(capitalize(status), detail, kind);
});

channel.onMessage((rawPayload) => {
    try {
        const data = JSON.parse(rawPayload);
        if (String(data.symbol || "").toUpperCase() !== selectedSymbol) {
            return;
        }
        enqueueOpportunity(data);
    } catch {
        setConnectionState("Warning", "Received malformed payload", "metric-warn");
    }
});

function normalizeSymbol(value) {
    const compact = String(value || "").trim().replace(/[-/\s]/g, "").toUpperCase();
    if (!compact) {
        return "";
    }
    if (compact.endsWith("USD") && !compact.endsWith("USDT")) {
        return `${compact}T`;
    }
    return compact;
}

function keyForOpportunity(data) {
    const symbol = String(data.symbol || "").toUpperCase();
    const buyExchange = String(data.buy_exchange || "").toLowerCase();
    const sellExchange = String(data.sell_exchange || "").toLowerCase();
    const buyAsk = Number(data.buy_ask) || 0;
    const sellBid = Number(data.sell_bid) || 0;
    const bucket = Math.floor(((buyAsk + sellBid) * 0.5) * 100);
    return `${symbol}|${buyExchange}|${sellExchange}|${bucket}`;
}

function enqueueOpportunity(data) {
    const key = keyForOpportunity(data);
    if (startupDedupActive && startupKeys.has(key)) {
        return;
    }
    if (startupDedupActive) {
        startupKeys.add(key);
    }
    pendingRows.push(data);
    scheduleFlush();
}

async function warmLoadOpportunities() {
    try {
        const seed = await getJson(`/api/opportunities?limit=${WARMLOAD_LIMIT}`);
        if (!Array.isArray(seed) || seed.length === 0) {
            return;
        }
        // API returns newest-first; enqueue oldest-first so table order stays correct.
        for (let i = seed.length - 1; i >= 0; i -= 1) {
            const row = seed[i];
            if (String(row.symbol || "").toUpperCase() === selectedSymbol) {
                enqueueOpportunity(row);
            }
        }
    } catch {
        // Warm load is optional; live websocket stream is still source of truth.
    }
}

function capitalize(value) {
    if (!value) {
        return "Unknown";
    }
    return value[0].toUpperCase() + value.slice(1);
}

function setConnectionState(label, detail, kind) {
    elConnectionStatus.textContent = label;
    elConnectionSubtext.textContent = detail;
    elConnectionStatus.classList.remove("metric-good", "metric-warn", "metric-bad");
    if (kind) {
        elConnectionStatus.classList.add(kind);
    }
}

function scheduleFlush() {
    if (flushScheduled) {
        return;
    }
    flushScheduled = true;
    window.requestAnimationFrame(flushRows);
}

function flushRows() {
    flushScheduled = false;
    if (pendingRows.length === 0) {
        return;
    }

    const rows = pendingRows.splice(0, pendingRows.length);
    const fragment = document.createDocumentFragment();
    for (let i = rows.length - 1; i >= 0; i -= 1) {
        const rowData = rows[i];
        fragment.appendChild(buildRow(rowData));
        trackMetrics(rowData);
    }
    tbody.insertBefore(fragment, tbody.firstChild);

    while (tbody.children.length > MAX_ROWS) {
        tbody.removeChild(tbody.lastChild);
    }

    if (tbody.firstElementChild) {
        tbody.firstElementChild.classList.add("row-flash");
        window.setTimeout(() => {
            if (tbody.firstElementChild) {
                tbody.firstElementChild.classList.remove("row-flash");
            }
        }, 920);
    }

    renderMetrics();
}

function trackMetrics(data) {
    state.total += 1;
    const symbol = String(data.symbol || "").toUpperCase();
    symbolHitMap.set(symbol, (symbolHitMap.get(symbol) || 0) + 1);

    const netBps = Number(data.net_spread_bps);
    if (Number.isFinite(netBps) && netBps > state.bestNetBps) {
        state.bestNetBps = netBps;
        state.bestSymbol = symbol || "-";
    }
}

function renderMetrics() {
    const nextTotal = state.total;
    const nextBestNet = Number.isFinite(state.bestNetBps) ? state.bestNetBps : 0;

    animateNumber(metricTween.total, nextTotal, 260, (value) => {
        elTotal.textContent = String(Math.round(value));
    });
    metricTween.total = nextTotal;

    animateNumber(metricTween.bestNet, nextBestNet, 280, (value) => {
        elBestNet.textContent = value.toFixed(2);
    });
    metricTween.bestNet = nextBestNet;

    elBestSymbol.textContent = state.bestSymbol ? `${state.bestSymbol} seen this run` : "No symbol yet";

    let topSymbol = "-";
    let topCount = 0;
    for (const [symbol, count] of symbolHitMap.entries()) {
        if (count > topCount) {
            topSymbol = symbol;
            topCount = count;
        }
    }

    elTopSymbol.textContent = topSymbol;
    elTopSymbolCount.textContent = `${topCount} hits`;
}

function buildRow(data) {
    const tr = document.createElement("tr");
    tr.classList.add("row-enter");
    window.setTimeout(() => tr.classList.remove("row-enter"), 420);

    const eventTime = Number(data.timestamp) > 0 ? Number(data.timestamp) * 1000 : Date.now();
    appendCell(tr, formatTime(eventTime));
    appendCell(tr, (data.symbol || "").toUpperCase(), "mono");
    appendCell(tr, data.buy_exchange || "-");
    appendCell(tr, toFixedOrDash(data.buy_ask), "mono");
    appendCell(tr, data.sell_exchange || "-");
    appendCell(tr, toFixedOrDash(data.sell_bid), "mono");
    appendCell(tr, toFixedOrDash(data.gross_spread), Number(data.gross_spread) >= 0 ? "positive" : "negative");
    appendCell(tr, toFixedOrDash(data.net_spread), Number(data.net_spread) >= 0 ? "positive" : "negative");
    appendCell(tr, toFixedOrDash(data.net_spread_bps), Number(data.net_spread_bps) >= 0 ? "positive" : "negative");

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

function clearTableAndMetrics() {
    pendingRows.length = 0;
    tbody.replaceChildren();
    symbolHitMap.clear();
    state.total = 0;
    state.bestNetBps = Number.NEGATIVE_INFINITY;
    state.bestSymbol = "";
    metricTween.total = 0;
    metricTween.bestNet = 0;
    renderMetrics();
}

function readRecentSymbols() {
    try {
        const parsed = JSON.parse(window.localStorage.getItem(RECENT_KEY) || "[]");
        if (Array.isArray(parsed)) {
            return parsed.filter((item) => typeof item === "string").slice(0, 6);
        }
    } catch {
        // ignore local storage parse issues
    }
    return [];
}

function writeRecentSymbols(symbol) {
    const recent = readRecentSymbols().filter((item) => item !== symbol);
    recent.unshift(symbol);
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 6)));
    renderRecentSearches();
}

function renderSymbolSuggestions() {
    const fragment = document.createDocumentFragment();
    for (const symbol of supportedSymbols) {
        const option = document.createElement("option");
        option.value = symbol;
        fragment.appendChild(option);
    }
    elSymbolSuggestions.replaceChildren(fragment);
}

function renderQuickButtons() {
    const fragment = document.createDocumentFragment();
    const picks = topSymbols.slice(0, QUICK_BUTTON_COUNT);
    for (const symbol of picks) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "quick-btn";
        button.textContent = symbol.replace("USDT", "");
        button.addEventListener("click", () => handleSymbolChange(symbol));
        fragment.appendChild(button);
    }
    elQuickButtons.replaceChildren(fragment);
}

function renderRecentSearches() {
    const recent = readRecentSymbols();
    const fragment = document.createDocumentFragment();
    if (recent.length === 0) {
        const empty = document.createElement("span");
        empty.className = "subtle";
        empty.textContent = "No recent symbols yet";
        fragment.appendChild(empty);
    } else {
        for (const symbol of recent) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "quick-btn quick-btn-muted";
            button.textContent = symbol;
            button.addEventListener("click", () => handleSymbolChange(symbol));
            fragment.appendChild(button);
        }
    }
    elRecentSearches.replaceChildren(fragment);
}

function setSelectedSymbolUi(symbol) {
    selectedSymbol = symbol;
    elSelectedSymbol.textContent = `Selected: ${symbol}`;
    elSymbolInput.value = symbol;
}

async function handleSymbolChange(rawValue) {
    const nextSymbol = normalizeSymbol(rawValue);
    if (!nextSymbol) {
        return;
    }
    if (!supportedSymbols.includes(nextSymbol)) {
        setConnectionState("Warning", `Unsupported symbol: ${nextSymbol}`, "metric-warn");
        return;
    }

    if (nextSymbol === selectedSymbol) {
        return;
    }

    elApplySymbol.disabled = true;
    try {
        const result = await postJson("/api/symbol", { symbol: nextSymbol });
        const active = normalizeSymbol(result.selected_symbol || nextSymbol);
        setSelectedSymbolUi(active);
        writeRecentSymbols(active);
        clearTableAndMetrics();
        await warmLoadOpportunities();
        setConnectionState("Live", `Tracking ${active} across exchanges`, "metric-good");
    } catch (error) {
        setConnectionState("Error", String(error.message || error), "metric-bad");
    } finally {
        elApplySymbol.disabled = false;
    }
}

async function loadSymbolMetadata() {
    const [symbolsData, selectedData] = await Promise.all([
        getJson("/api/symbols"),
        getJson("/api/symbol"),
    ]);

    supportedSymbols = (symbolsData.supported_symbols || []).map((item) => normalizeSymbol(item));
    supportedSymbols = supportedSymbols.filter(Boolean);
    topSymbols = (symbolsData.top_symbols || []).map((item) => normalizeSymbol(item)).filter(Boolean);

    const initial = normalizeSymbol(selectedData.selected_symbol || symbolsData.default_symbol || "BTCUSDT");
    setSelectedSymbolUi(initial);
    renderSymbolSuggestions();
    renderQuickButtons();
    renderRecentSearches();
}

function bindSymbolControls() {
    elApplySymbol.addEventListener("click", () => handleSymbolChange(elSymbolInput.value));
    elSymbolInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            handleSymbolChange(elSymbolInput.value);
        }
    });
}

window.addEventListener("beforeunload", () => channel.disconnect());

async function bootstrap() {
    await loadSymbolMetadata();
    bindSymbolControls();
    await warmLoadOpportunities();
    channel.connect();
    window.setTimeout(() => {
        startupDedupActive = false;
        startupKeys.clear();
    }, STARTUP_DEDUP_MS);
}

bootstrap();
