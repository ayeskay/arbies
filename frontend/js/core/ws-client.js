export class RealtimeChannel {
    constructor(path = "/ws") {
        this.path = path;
        this.socket = null;
        this.reconnectDelayMs = 1000;
        this.maxReconnectDelayMs = 10000;
        this.reconnectTimer = null;
        this.messageListeners = new Set();
        this.statusListeners = new Set();
    }

    connect() {
        this.#emitStatus("connecting", "Opening websocket stream");
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        this.socket = new WebSocket(`${protocol}//${window.location.host}${this.path}`);

        this.socket.onopen = () => {
            this.reconnectDelayMs = 1000;
            this.#emitStatus("live", "Receiving market events");
        };

        this.socket.onmessage = (event) => {
            this.#emitMessage(event.data);
        };

        this.socket.onclose = () => {
            this.#emitStatus("reconnecting", "Socket closed, retrying");
            this.#scheduleReconnect();
        };

        this.socket.onerror = () => {
            this.#emitStatus("error", "Socket error detected");
            if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
                this.socket.close();
            }
        };
    }

    disconnect() {
        if (this.reconnectTimer) {
            window.clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
            this.socket.close();
        }
    }

    onMessage(listener) {
        this.messageListeners.add(listener);
        return () => this.messageListeners.delete(listener);
    }

    onStatus(listener) {
        this.statusListeners.add(listener);
        return () => this.statusListeners.delete(listener);
    }

    #scheduleReconnect() {
        if (this.reconnectTimer) {
            return;
        }

        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, this.reconnectDelayMs);

        this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 2, this.maxReconnectDelayMs);
    }

    #emitMessage(rawPayload) {
        for (const listener of this.messageListeners) {
            listener(rawPayload);
        }
    }

    #emitStatus(state, detail) {
        for (const listener of this.statusListeners) {
            listener({ state, detail });
        }
    }
}
