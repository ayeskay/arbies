import { getJson } from "../core/http-client.js";

function write(targetId, text) {
    document.getElementById(targetId).innerText = text;
}

async function testHealth() {
    write("res-health", "Calling /api/health...");
    try {
        const data = await getJson("/api/health");
        write("res-health", JSON.stringify(data, null, 2));
    } catch (error) {
        write("res-health", "Error: " + error.message);
    }
}

async function testState() {
    write("res-state", "Calling /api/state...");
    try {
        const data = await getJson("/api/state");
        write("res-state", JSON.stringify(data, null, 2));
    } catch (error) {
        write("res-state", "Error: " + error.message);
    }
}

let testSocket = null;

function testWS() {
    const out = document.getElementById("res-ws");
    if (testSocket) {
        out.innerText = "Already connected.\n" + out.innerText;
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    testSocket = new WebSocket(`${protocol}//${window.location.host}/ws`);
    out.innerText = "Connecting...\n";

    testSocket.onopen = () => {
        out.innerText = "Connected. Listening for messages...\n" + out.innerText;
    };

    testSocket.onmessage = (event) => {
        try {
            const payload = JSON.stringify(JSON.parse(event.data), null, 2);
            out.innerText = `[Message]\n${payload}\n\n` + out.innerText;
        } catch {
            out.innerText = `[Message]\n${event.data}\n\n` + out.innerText;
        }
    };

    testSocket.onclose = () => {
        out.innerText = "Disconnected.\n" + out.innerText;
        testSocket = null;
    };

    testSocket.onerror = () => {
        out.innerText = "Socket error detected.\n" + out.innerText;
    };
}

function disconnectWS() {
    if (testSocket) {
        testSocket.close();
    }
}

window.arbiesApiLab = {
    testHealth,
    testState,
    testWS,
    disconnectWS,
};
