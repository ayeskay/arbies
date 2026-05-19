export async function getJson(path) {
    const response = await fetch(path);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status} for ${path}`);
    }
    return response.json();
}


export async function postJson(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload || {}),
    });

    if (!response.ok) {
        let message = `HTTP ${response.status} for ${path}`;
        try {
            const errorPayload = await response.json();
            if (errorPayload && errorPayload.error) {
                message = errorPayload.error;
            }
        } catch {
            // ignore JSON parse errors and keep fallback message
        }
        throw new Error(message);
    }

    return response.json();
}
