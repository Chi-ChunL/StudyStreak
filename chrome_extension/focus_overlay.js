(function () {
    if (window.__studyStreakFocusOverlayLoaded) {
        return;
    }

    window.__studyStreakFocusOverlayLoaded = true;

    const OVERLAY_ID = "studystreak-focus-overlay-root";
    const STORAGE_KEYS = [
        "focusActive",
        "focusStartedAt",
        "focusSubject",
        "pomodoroEnabled",
        "pomodoroPhase",
        "pomodoroPhaseStartedAt",
        "pomodoroPhaseDurationSeconds",
        "pomodoroWorkBlocksCompleted"
    ];

    let timerId = null;
    let currentState = {
        focusActive: false,
        focusStartedAt: null,
        focusSubject: "",
        pomodoroEnabled: false,
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: null,
        pomodoroPhaseDurationSeconds: 0,
        pomodoroWorkBlocksCompleted: 0
    };

    function storageGet(keys) {
        return new Promise((resolve) => {
            chrome.storage.local.get(keys, resolve);
        });
    }

    function formatElapsed(milliseconds) {
        const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        if (hours > 0) {
            return [
                hours,
                String(minutes).padStart(2, "0"),
                String(seconds).padStart(2, "0")
            ].join(":");
        }

        return `${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    function getPomodoroSecondsLeft() {
        const phaseStartedAt = Number(currentState.pomodoroPhaseStartedAt);
        const durationSeconds = Number(currentState.pomodoroPhaseDurationSeconds) || 0;

        if (!phaseStartedAt || durationSeconds <= 0) {
            return 0;
        }

        const elapsedSeconds = Math.floor((Date.now() - phaseStartedAt) / 1000);
        return Math.max(0, durationSeconds - elapsedSeconds);
    }

    function getOverlayRoot() {
        let root = document.getElementById(OVERLAY_ID);

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = OVERLAY_ID;
        root.style.position = "fixed";
        root.style.top = "14px";
        root.style.right = "14px";
        root.style.zIndex = "2147483647";
        root.style.pointerEvents = "none";

        const shadow = root.attachShadow({ mode: "open" });
        const style = document.createElement("style");
        style.textContent = `
            .timer {
                min-width: 146px;
                padding: 9px 12px;
                border: 2px solid #0f4c7a;
                border-radius: 8px;
                background: #f3e8d3;
                color: #15384f;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
                text-align: center;
                pointer-events: none;
            }

            .label {
                color: #0f4c7a;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0;
                line-height: 1.2;
                margin-bottom: 2px;
                text-transform: uppercase;
            }

            .time {
                color: #111827;
                font-size: 22px;
                font-weight: 900;
                letter-spacing: 0;
                line-height: 1.15;
            }

            .subject {
                color: #2f4f63;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.25;
                margin-top: 3px;
                max-width: 220px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .stop-button {
                width: 100%;
                margin-top: 8px;
                padding: 6px 8px;
                border: 2px solid #8a3a3a;
                border-radius: 6px;
                background: #a85c5c;
                color: #fff8e8;
                cursor: pointer;
                font: inherit;
                font-size: 12px;
                font-weight: 900;
                pointer-events: auto;
            }

            .stop-button:hover {
                background: #8c4949;
            }

            .stop-button:disabled {
                cursor: wait;
                opacity: 0.7;
            }
        `;

        const timer = document.createElement("div");
        timer.className = "timer";
        timer.innerHTML = `
            <div class="label">StudyStreak</div>
            <div class="time">0:00</div>
            <div class="subject">Focus running</div>
            <button class="stop-button" type="button">Stop Focus</button>
        `;

        shadow.append(style, timer);
        shadow.querySelector(".stop-button").addEventListener("click", stopFocusFromOverlay);
        document.documentElement.append(root);
        return root;
    }

    async function stopFocusFromOverlay(event) {
        event.preventDefault();
        event.stopPropagation();

        const button = event.currentTarget;
        button.disabled = true;
        button.textContent = "Stopping...";

        try {
            await chrome.runtime.sendMessage({ type: "stopFocus" });
            await refreshState();
        } catch {
            button.disabled = false;
            button.textContent = "Stop failed";
            setTimeout(() => {
                button.textContent = "Stop Focus";
            }, 1800);
        }
    }

    function removeOverlay() {
        const root = document.getElementById(OVERLAY_ID);

        if (root) {
            root.remove();
        }

        if (timerId !== null) {
            clearInterval(timerId);
            timerId = null;
        }
    }

    function updateOverlay() {
        if (!currentState.focusActive || !currentState.focusStartedAt) {
            removeOverlay();
            return;
        }

        const root = getOverlayRoot();
        const shadowTimer = root.shadowRoot;

        if (!shadowTimer) {
            return;
        }

        const startedAt = Number(currentState.focusStartedAt) || Date.now();
        const timeText = currentState.pomodoroEnabled
            ? formatElapsed(getPomodoroSecondsLeft() * 1000)
            : formatElapsed(Date.now() - startedAt);
        const subject = String(currentState.focusSubject || "Focus running").trim();
        const phase = currentState.pomodoroPhase === "break" ? "Break" : "Work";
        const label = currentState.pomodoroEnabled
            ? `StudyStreak ${phase}`
            : "StudyStreak";
        const subjectText = currentState.pomodoroEnabled
            ? `${subject || "Focus running"} | blocks ${Number(currentState.pomodoroWorkBlocksCompleted) || 0}`
            : subject || "Focus running";

        shadowTimer.querySelector(".label").textContent = label;
        shadowTimer.querySelector(".time").textContent = timeText;
        shadowTimer.querySelector(".subject").textContent = subjectText;
    }

    function renderOverlay() {
        updateOverlay();

        if (currentState.focusActive && timerId === null) {
            timerId = setInterval(updateOverlay, 1000);
        }
    }

    async function refreshState() {
        currentState = {
            ...currentState,
            ...(await storageGet(STORAGE_KEYS))
        };

        renderOverlay();
    }

    chrome.storage.onChanged.addListener((changes, areaName) => {
        if (areaName !== "local") {
            return;
        }

        let changed = false;

        STORAGE_KEYS.forEach((key) => {
            if (changes[key]) {
                currentState[key] = changes[key].newValue;
                changed = true;
            }
        });

        if (changed) {
            renderOverlay();
        }
    });

    refreshState();
})();
