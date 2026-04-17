import { getJson } from "../core/http-client.js";

const healthDot = document.getElementById("health-dot");
const healthLabel = document.getElementById("health-label");
const healthDetail = document.getElementById("health-detail");
const healthJson = document.getElementById("health-json");
const trackedSymbols = document.getElementById("tracked-symbols");
const venueEntries = document.getElementById("venue-entries");
const stateSample = document.getElementById("state-sample");

function setHealth(label, detail, state) {
    healthLabel.textContent = label;
    healthDetail.textContent = detail;
    healthDot.classList.remove("good", "bad", "pulse");
    if (state === "good") {
        healthDot.classList.add("good", "pulse");
    } else if (state === "bad") {
        healthDot.classList.add("bad");
    }
}

async function checkStatus() {
    try {
        const data = await getJson("/api/health");
        healthJson.textContent = JSON.stringify(data, null, 2);
        if (data.status === "OK") {
            setHealth("Online", data.service || "Service healthy", "good");
        } else {
            setHealth("Degraded", "Unexpected health payload", "bad");
        }
    } catch (error) {
        setHealth("Offline", "Cannot connect to /api/health", "bad");
        healthJson.textContent = `Error: ${error.message}`;
    }
}

async function checkState() {
    try {
        const data = await getJson("/api/state");
        const symbols = Object.keys(data || {});
        trackedSymbols.textContent = String(symbols.length);

        let venueCount = 0;
        for (const symbol of symbols) {
            venueCount += Object.keys(data[symbol] || {}).length;
        }

        venueEntries.textContent = String(venueCount);
        stateSample.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        trackedSymbols.textContent = "0";
        venueEntries.textContent = "0";
        stateSample.textContent = `Error: ${error.message}`;
    }
}

checkStatus();
checkState();
window.setInterval(checkStatus, 5000);
window.setInterval(checkState, 5000);
