import { RealtimeChannel } from "../core/ws-client.js";
import { animateNumber } from "../core/motion.js";
import { toFixedOrDash, formatTime } from "../core/format.js";

const tbody = document.getElementById("arb-body");
const MAX_ROWS = 80;

const elConnectionStatus = document.getElementById("connection-status");
const elConnectionSubtext = document.getElementById("connection-subtext");
const elTotal = document.getElementById("total-opportunities");
const elBestNet = document.getElementById("best-net-bps");
const elBestSymbol = document.getElementById("best-symbol");
const elTopSymbol = document.getElementById("top-symbol");
const elTopSymbolCount = document.getElementById("top-symbol-count");

const channel = new RealtimeChannel("/ws");
const pendingRows = [];
const symbolHitMap = new Map();

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
        pendingRows.push(data);
        scheduleFlush();
    } catch {
        setConnectionState("Warning", "Received malformed payload", "metric-warn");
    }
});

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

    appendCell(tr, formatTime(Date.now()));
    appendCell(tr, (data.symbol || "").toUpperCase(), "mono");
    appendCell(tr, data.buy_exchange || "-");
    appendCell(tr, toFixedOrDash(data.buy_ask), "mono");
    appendCell(tr, data.sell_exchange || "-");
    appendCell(tr, toFixedOrDash(data.sell_bid), "mono");
    appendCell(tr, toFixedOrDash(data.gross_spread), Number(data.gross_spread) >= 0 ? "positive" : "negative");
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

window.addEventListener("beforeunload", () => channel.disconnect());
channel.connect();
