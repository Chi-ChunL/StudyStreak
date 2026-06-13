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
    let keepOverlayAfterStop = false;
    let removeAfterStopTimerId = null;
    let stopStatus = {
        text: "",
        type: "pending"
    };
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

            .status {
                display: none;
                margin-top: 7px;
                font-size: 12px;
                font-weight: 800;
                line-height: 1.25;
            }

            .status.success {
                display: block;
                color: #0b7a39;
            }

            .status.failure {
                display: block;
                color: #8a1f1f;
            }

            .status.pending {
                display: block;
                color: #174a7c;
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
            <div class="status" aria-live="polite"></div>
            <button class="stop-button" type="button">Stop Focus</button>
        `;

        shadow.append(style, timer);
        shadow.querySelector(".stop-button").addEventListener("click", stopFocusFromOverlay);
        document.documentElement.append(root);
        return root;
    }

    function setOverlayStatus(text, type = "pending") {
        stopStatus = { text, type };

        const root = document.getElementById(OVERLAY_ID);

        if (!root?.shadowRoot) {
            return;
        }

        const status = root.shadowRoot.querySelector(".status");
        status.textContent = text;
        status.className = text ? `status ${type}` : "status";
    }

    function getStopResultMessage(summary) {
        if (!summary) {
            return {
                text: "Upload unsuccessful: no response.",
                type: "failure",
                buttonText: "Upload unsuccessful"
            };
        }

        if (!summary.completedAt) {
            return {
                text: summary.serverUpload?.error || "Focus stopped. No new upload.",
                type: "success",
                buttonText: "Focus stopped"
            };
        }

        if (summary.serverUpload?.ok && summary.qualityUpload?.ok) {
            return {
                text: `Upload successful: ${summary.serverUpload.minutes} min synced.`,
                type: "success",
                buttonText: "Upload successful"
            };
        }

        if (summary.serverUpload?.ok) {
            return {
                text: `Leaderboard uploaded ${summary.serverUpload.minutes} min. Quality sync failed.`,
                type: "failure",
                buttonText: "Upload partly failed"
            };
        }

        return {
            text: `Upload unsuccessful: ${summary.serverUpload?.error || "Unknown error."}`,
            type: "failure",
            buttonText: "Upload unsuccessful"
        };
    }

    function renderStoppedOverlay() {
        const root = getOverlayRoot();
        const shadowTimer = root.shadowRoot;

        if (!shadowTimer) {
            return;
        }

        shadowTimer.querySelector(".label").textContent = "StudyStreak";
        shadowTimer.querySelector(".time").textContent = "Stopped";
        shadowTimer.querySelector(".subject").textContent = "Focus session ended";
        setOverlayStatus(stopStatus.text || "Stopping...", stopStatus.type || "pending");
    }

    async function stopFocusFromOverlay(event) {
        event.preventDefault();
        event.stopPropagation();

        const button = event.currentTarget;
        keepOverlayAfterStop = true;
        button.disabled = true;
        button.textContent = "Stopping...";
        setOverlayStatus("Stopping focus and uploading...", "pending");

        try {
            const summary = await chrome.runtime.sendMessage({ type: "stopFocus" });
            const result = getStopResultMessage(summary);
            button.textContent = result.buttonText;
            setOverlayStatus(result.text, result.type);
            await refreshState();

            if (removeAfterStopTimerId !== null) {
                clearTimeout(removeAfterStopTimerId);
            }

            removeAfterStopTimerId = setTimeout(() => {
                keepOverlayAfterStop = false;
                removeAfterStopTimerId = null;
                removeOverlay();
            }, 5000);
        } catch {
            button.disabled = false;
            button.textContent = "Stop failed";
            setOverlayStatus("Upload unsuccessful: stop failed.", "failure");
            setTimeout(() => {
                button.textContent = "Stop Focus";
                setOverlayStatus("", "pending");
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

        stopStatus = {
            text: "",
            type: "pending"
        };
    }

    function updateOverlay() {
        if (!currentState.focusActive || !currentState.focusStartedAt) {
            if (keepOverlayAfterStop) {
                renderStoppedOverlay();
                return;
            }

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
        setOverlayStatus("", "pending");

        const stopButton = shadowTimer.querySelector(".stop-button");
        stopButton.disabled = false;
        stopButton.textContent = "Stop Focus";
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
