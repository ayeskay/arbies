export function toFixedOrDash(value) {
    return Number.isFinite(value) ? value.toFixed(2) : "-";
}

export function formatTime(timestampMs) {
    const date = new Date(timestampMs || Date.now());
    return date.toTimeString().split(" ")[0] + "." + String(date.getMilliseconds()).padStart(3, "0");
}

export function normalize(value) {
    return String(value || "").trim().toLowerCase();
}

export function numberOrZero(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

export function clampInt(value, min, max, fallback) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
        return fallback;
    }
    return Math.min(max, Math.max(min, parsed));
}
