(function initUiMotion() {
    const root = document.documentElement;
    const glow = document.querySelector(".backdrop-glow");
    const revealNodes = document.querySelectorAll(".panel, .metric-card");

    if (glow) {
        window.addEventListener("pointermove", (event) => {
            const x = (event.clientX / window.innerWidth - 0.5) * 12;
            const y = (event.clientY / window.innerHeight - 0.5) * 12;
            glow.style.transform = `translate(${x}px, ${y}px)`;
        });

        window.addEventListener("pointerleave", () => {
            glow.style.transform = "translate(0, 0)";
        });
    }

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            }
        }, { threshold: 0.15 });

        revealNodes.forEach((node) => observer.observe(node));
    }

    root.classList.add("ui-motion-ready");
})();
