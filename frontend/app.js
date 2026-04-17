const tbody = document.getElementById("arb-body");
const MAX_ROWS = 50;
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

let ws = null;
let reconnectDelayMs = 1000;
let reconnectTimer = null;
let flushScheduled = false;
const pendingRows = [];

function connectWebSocket() {
    ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

    ws.onopen = () => {
        reconnectDelayMs = 1000;
        console.log("Connected to Market Data Server");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            pendingRows.push(data);
            scheduleFlush();
        } catch (e) {
            console.error("Error parsing message", e);
        }
    };

    ws.onclose = () => {
        console.log("Disconnected from server");
        scheduleReconnect();
    };

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
        connectWebSocket();
    }, reconnectDelayMs);
    reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
}

function formatTime(date) {
    return date.toTimeString().split(' ')[0] + '.' + date.getMilliseconds().toString().padStart(3, '0');
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
        fragment.appendChild(buildRow(rows[i]));
    }
    tbody.insertBefore(fragment, tbody.firstChild);

    while (tbody.children.length > MAX_ROWS) {
        tbody.removeChild(tbody.lastChild);
    }
}

function buildRow(data) {
    const tr = document.createElement("tr");
    appendCell(tr, formatTime(new Date()));
    appendCell(tr, (data.symbol || "").toUpperCase());
    appendCell(tr, data.buy_exchange || "");
    appendCell(tr, toFixedOrDash(data.buy_ask));
    appendCell(tr, data.sell_exchange || "");
    appendCell(tr, toFixedOrDash(data.sell_bid));
    appendCell(tr, toFixedOrDash(data.gross_spread), "positive");
    appendCell(tr, toFixedOrDash(data.net_spread_bps), "positive");
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

window.addEventListener("beforeunload", () => {
    if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
    }
    if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close();
    }
});

connectWebSocket();
