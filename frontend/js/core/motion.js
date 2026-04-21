export function animateNumber(from, to, durationMs, onFrame) {
    const start = performance.now();
    const delta = to - from;

    function step(now) {
        const progress = Math.min((now - start) / durationMs, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        onFrame(from + delta * eased);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    }

    window.requestAnimationFrame(step);
}
