(function () {
    const SCRIPT_VERSION = "todo-overlay-v7";

    if (window.__studyStreakFocusOverlayVersion === SCRIPT_VERSION) {
        window.__studyStreakRefreshOverlay?.();
        return;
    }

    window.__studyStreakFocusOverlayLoaded = true;
    window.__studyStreakFocusOverlayVersion = SCRIPT_VERSION;

    const OVERLAY_ID = "studystreak-focus-overlay-root";
    const TODO_OVERLAY_ID = "studystreak-todo-overlay-root";
    const FOCUS_STORAGE_KEYS = [
        "focusActive",
        "focusStartedAt",
        "focusSubject",
        "pomodoroEnabled",
        "pomodoroPhase",
        "pomodoroPhaseStartedAt",
        "pomodoroPhaseDurationSeconds",
        "pomodoroWorkBlocksCompleted",
        "syncedSubjectTopics",
        "focusOverlayPosition"
    ];
    const TODO_STORAGE_KEYS = ["serverToken", "todoOverlayEnabled", "todoItems", "todoOverlayPosition"];
    const STORAGE_KEYS = [...FOCUS_STORAGE_KEYS, ...TODO_STORAGE_KEYS];

    let timerId = null;
    let keepOverlayAfterStop = false;
    let removeAfterStopTimerId = null;
    let stopStatus = {
        text: "",
        type: "pending"
    };
    let overlayMinimized = false;
    let overlayWatchdogId = null;
    let overlayObserver = null;
    let startupRefreshTimerIds = [];
    let currentState = {
        focusActive: false,
        focusStartedAt: null,
        focusSubject: "",
        pomodoroEnabled: false,
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: null,
        pomodoroPhaseDurationSeconds: 0,
        pomodoroWorkBlocksCompleted: 0,
        syncedSubjectTopics: {},
        focusOverlayPosition: null,
        serverToken: "",
        todoOverlayEnabled: true,
        todoItems: [],
        todoOverlayPosition: null
    };
    let pendingReviewSummary = null;

    function storageGet(keys) {
        return new Promise((resolve) => {
            chrome.storage.local.get(keys, resolve);
        });
    }

    function storageSet(values) {
        return new Promise((resolve) => {
            chrome.storage.local.set(values, resolve);
        });
    }

    function sendRuntimeMessage(message) {
        return new Promise((resolve, reject) => {
            let settled = false;
            const finish = (error, response) => {
                if (settled) {
                    return;
                }

                settled = true;
                if (error) {
                    reject(error);
                    return;
                }

                resolve(response);
            };

            try {
                const possiblePromise = chrome.runtime.sendMessage(message, (response) => {
                    const error = chrome.runtime.lastError;
                    finish(error ? new Error(error.message) : null, response);
                });

                if (possiblePromise?.then) {
                    possiblePromise.then(
                        (response) => finish(null, response),
                        (error) => finish(error)
                    );
                }
            } catch (error) {
                finish(error);
            }
        });
    }

    function getMountRoot() {
        return document.documentElement || document.body;
    }

    function appendOverlayRoot(root) {
        const mountRoot = getMountRoot();

        if (!mountRoot) {
            scheduleRefresh(50);
            return false;
        }

        mountRoot.append(root);
        return true;
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

    function cleanTodoItems(items) {
        if (!Array.isArray(items)) {
            return [];
        }

        return items
            .map((item, index) => {
                const text = String(item?.text || "").trim();

                if (!text) {
                    return null;
                }

                return {
                    id: String(item?.id || `todo-${Date.now()}-${index}`),
                    text: text.slice(0, 120),
                    done: Boolean(item?.done)
                };
            })
            .filter(Boolean)
            .slice(0, 50);
    }

    function cleanSubjectTopicMap(subjectTopics) {
        const cleaned = {};

        if (!subjectTopics || typeof subjectTopics !== "object" || Array.isArray(subjectTopics)) {
            return cleaned;
        }

        Object.entries(subjectTopics).forEach(([subject, topics]) => {
            const cleanSubject = String(subject || "").trim().toLowerCase();
            const topicList = Array.isArray(topics) ? topics : [topics];

            if (!cleanSubject) {
                return;
            }

            cleaned[cleanSubject] = topicList
                .map((topic) => String(topic || "").trim())
                .filter(Boolean)
                .filter((topic, index, list) => list.indexOf(topic) === index)
                .slice(0, 30);
        });

        return cleaned;
    }

    function getSubjectTopics(subject) {
        const subjectTopics = cleanSubjectTopicMap(currentState.syncedSubjectTopics);
        const cleanSubject = String(subject || "").trim().toLowerCase();
        const topics = subjectTopics[cleanSubject];

        return Array.isArray(topics) ? topics : [];
    }

    function clampPosition(position, fallback) {
        const left = Number(position?.left);
        const top = Number(position?.top);
        const fallbackLeft = Number(fallback?.left) || 14;
        const fallbackTop = Number(fallback?.top) || 14;
        const maxLeft = Math.max(6, window.innerWidth - 80);
        const maxTop = Math.max(6, window.innerHeight - 48);

        return {
            left: Math.min(Math.max(Number.isFinite(left) ? left : fallbackLeft, 6), maxLeft),
            top: Math.min(Math.max(Number.isFinite(top) ? top : fallbackTop, 6), maxTop)
        };
    }

    function applyOverlayPosition(root, position, fallback) {
        const nextPosition = clampPosition(position, fallback);

        root.style.left = `${nextPosition.left}px`;
        root.style.top = `${nextPosition.top}px`;
        root.style.right = "auto";
        root.style.bottom = "auto";
    }

    function makeOverlayDraggable(root, handle, storageKey) {
        let dragState = null;

        handle.addEventListener("pointerdown", (event) => {
            const target = event.target;

            if (target?.closest?.("button, input, textarea, select, a, label")) {
                return;
            }

            const rect = root.getBoundingClientRect();
            dragState = {
                pointerId: event.pointerId,
                offsetX: event.clientX - rect.left,
                offsetY: event.clientY - rect.top
            };

            root.style.left = `${rect.left}px`;
            root.style.top = `${rect.top}px`;
            root.style.right = "auto";
            root.style.bottom = "auto";
            handle.setPointerCapture?.(event.pointerId);
            event.preventDefault();
        });

        handle.addEventListener("pointermove", (event) => {
            if (!dragState || dragState.pointerId !== event.pointerId) {
                return;
            }

            applyOverlayPosition(
                root,
                {
                    left: event.clientX - dragState.offsetX,
                    top: event.clientY - dragState.offsetY
                },
                { left: 14, top: 14 }
            );
        });

        const finishDrag = async (event) => {
            if (!dragState || dragState.pointerId !== event.pointerId) {
                return;
            }

            const rect = root.getBoundingClientRect();
            dragState = null;
            handle.releasePointerCapture?.(event.pointerId);

            await storageSet({
                [storageKey]: {
                    left: Math.round(rect.left),
                    top: Math.round(rect.top)
                }
            });
        };

        handle.addEventListener("pointerup", finishDrag);
        handle.addEventListener("pointercancel", finishDrag);
    }

    function getOverlayRoot() {
        let root = document.getElementById(OVERLAY_ID);

        if (root) {
            if (root.shadowRoot?.querySelector(".review-panel")) {
                return root;
            }

            root.remove();
        }

        root = document.createElement("div");
        root.id = OVERLAY_ID;
        root.style.position = "fixed";
        root.style.zIndex = "2147483647";
        root.style.pointerEvents = "auto";
        applyOverlayPosition(
            root,
            currentState.focusOverlayPosition,
            { left: Math.max(14, window.innerWidth - 188), top: 14 }
        );

        const shadow = root.attachShadow({ mode: "open" });
        const style = document.createElement("style");
        style.textContent = `
            .timer {
                box-sizing: border-box;
                width: 246px;
                padding: 9px 12px;
                border: 2px solid #0f4c7a;
                border-radius: 8px;
                background: #f3e8d3;
                color: #15384f;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
                text-align: center;
                cursor: move;
                pointer-events: auto;
                user-select: none;
            }

            .timer.minimized {
                width: 142px;
                padding: 7px 9px;
            }

            .timer.minimized .subject,
            .timer.minimized .status,
            .timer.minimized .stop-button,
            .timer.minimized .review-panel {
                display: none;
            }

            .topline {
                display: grid;
                grid-template-columns: 1fr auto;
                gap: 6px;
                align-items: center;
            }

            .minimize-button {
                width: 24px;
                height: 22px;
                margin: 0;
                padding: 0;
                border: 1px solid #9b8061;
                border-radius: 5px;
                background: #fff8e8;
                color: #15384f;
                cursor: pointer;
                font: inherit;
                font-size: 12px;
                font-weight: 900;
                pointer-events: auto;
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

            .review-panel {
                display: none;
                margin-top: 9px;
                padding-top: 9px;
                border-top: 1px solid #d4bd95;
                text-align: left;
            }

            .review-panel.visible {
                display: block;
            }

            .review-title {
                color: #0f4c7a;
                font-size: 12px;
                font-weight: 900;
                line-height: 1.2;
                margin-bottom: 6px;
                text-align: center;
            }

            .review-label {
                display: block;
                color: #2f4f63;
                font-size: 11px;
                font-weight: 900;
                margin-top: 6px;
            }

            .review-topic,
            .review-note {
                box-sizing: border-box;
                width: 100%;
                margin-top: 4px;
                border: 2px solid #9b8061;
                border-radius: 5px;
                background: #fff8e8;
                color: #111827;
                font: inherit;
                font-size: 12px;
                pointer-events: auto;
            }

            .review-topic {
                padding: 5px 6px;
            }

            .review-note {
                min-height: 62px;
                padding: 6px;
                resize: vertical;
            }

            .review-actions {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 7px;
                margin-top: 8px;
            }

            .review-actions button {
                margin: 0;
                padding: 6px 7px;
                border-radius: 6px;
                cursor: pointer;
                font: inherit;
                font-size: 12px;
                font-weight: 900;
                pointer-events: auto;
            }

            .save-review {
                border: 2px solid #0f6b35;
                background: #dfead6;
                color: #173f20;
            }

            .skip-review {
                border: 2px solid #9b8061;
                background: #ead7b2;
                color: #2c211c;
            }

            .save-review:disabled,
            .skip-review:disabled {
                cursor: wait;
                opacity: 0.7;
            }
        `;

        const timer = document.createElement("div");
        timer.className = "timer";
        timer.innerHTML = `
            <div class="topline">
                <div class="label">StudyStreak</div>
                <button class="minimize-button" type="button" title="Minimize overlay">-</button>
            </div>
            <div class="time">0:00</div>
            <div class="subject">Focus running</div>
            <div class="status" aria-live="polite"></div>
            <button class="stop-button" type="button">Stop Focus</button>
            <div class="review-panel" aria-live="polite">
                <div class="review-title">Review this session</div>
                <label class="review-label">
                    Topic
                    <select class="review-topic"></select>
                </label>
                <label class="review-label">
                    Note
                    <textarea class="review-note" maxlength="1000" placeholder="What did you cover?"></textarea>
                </label>
                <div class="review-actions">
                    <button class="save-review" type="button">Save</button>
                    <button class="skip-review" type="button">Skip</button>
                </div>
            </div>
        `;

        shadow.append(style, timer);
        makeOverlayDraggable(root, timer, "focusOverlayPosition");
        shadow.querySelector(".stop-button").addEventListener("click", stopFocusFromOverlay);
        shadow.querySelector(".minimize-button").addEventListener("click", toggleOverlayMinimized);
        shadow.querySelector(".save-review").addEventListener("click", saveReviewFromOverlay);
        shadow.querySelector(".skip-review").addEventListener("click", skipReviewFromOverlay);
        if (!appendOverlayRoot(root)) {
            return null;
        }

        return root;
    }

    function getTodoOverlayRoot() {
        let root = document.getElementById(TODO_OVERLAY_ID);

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = TODO_OVERLAY_ID;
        root.style.position = "fixed";
        root.style.zIndex = "2147483646";
        root.style.pointerEvents = "auto";
        applyOverlayPosition(
            root,
            currentState.todoOverlayPosition,
            { left: Math.max(14, window.innerWidth - 274), top: Math.max(14, window.innerHeight - 250) }
        );

        const shadow = root.attachShadow({ mode: "open" });
        const style = document.createElement("style");
        style.textContent = `
            .todo-card {
                width: 246px;
                max-height: 44vh;
                border: 2px solid #0f4c7a;
                border-radius: 8px;
                background: #f3e8d3;
                color: #15384f;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
                overflow: hidden;
                pointer-events: auto;
                user-select: none;
            }

            .todo-header {
                display: flex;
                justify-content: space-between;
                gap: 10px;
                padding: 8px 10px;
                border-bottom: 1px solid #d4bd95;
                color: #0f4c7a;
                cursor: move;
                font-size: 12px;
                font-weight: 900;
                text-transform: uppercase;
            }

            .todo-list {
                max-height: calc(44vh - 84px);
                overflow-y: auto;
                padding: 8px 10px;
            }

            .todo-empty {
                color: #3c5667;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.35;
            }

            .todo-item {
                display: grid;
                grid-template-columns: auto 1fr;
                gap: 7px;
                align-items: start;
                color: #17202a;
                font-size: 12px;
                font-weight: 800;
                line-height: 1.35;
            }

            .todo-item + .todo-item {
                margin-top: 7px;
                padding-top: 7px;
                border-top: 1px solid #d4bd95;
            }

            .todo-item input {
                width: 14px;
                height: 14px;
                margin: 1px 0 0;
                accent-color: #0f7a38;
                cursor: pointer;
                pointer-events: auto;
            }

            .todo-item.done span {
                color: #64717b;
                text-decoration: line-through;
            }

            .todo-text {
                overflow-wrap: anywhere;
            }

            .todo-footer {
                padding: 8px 10px 10px;
                border-top: 1px solid #d4bd95;
            }

            .complete-all-button {
                width: 100%;
                margin: 0;
                padding: 7px 8px;
                border: 2px solid #0f6b35;
                border-radius: 6px;
                background: #dfead6;
                color: #173f20;
                cursor: pointer;
                font: inherit;
                font-size: 12px;
                font-weight: 900;
                pointer-events: auto;
            }

            .complete-all-button:disabled {
                cursor: not-allowed;
                opacity: 0.55;
            }
        `;

        const card = document.createElement("div");
        const header = document.createElement("div");
        const title = document.createElement("span");
        const count = document.createElement("span");
        const list = document.createElement("div");
        const footer = document.createElement("div");
        const completeAllButton = document.createElement("button");

        card.className = "todo-card";
        header.className = "todo-header";
        count.className = "todo-count";
        list.className = "todo-list";
        footer.className = "todo-footer";
        completeAllButton.className = "complete-all-button";
        completeAllButton.type = "button";
        completeAllButton.textContent = "Complete All";
        title.textContent = "Todo";

        header.append(title, count);
        footer.append(completeAllButton);
        card.append(header, list, footer);
        shadow.append(style, card);

        makeOverlayDraggable(root, header, "todoOverlayPosition");
        list.addEventListener("change", onTodoOverlayChange);
        completeAllButton.addEventListener("click", completeAllTodosFromOverlay);
        if (!appendOverlayRoot(root)) {
            return null;
        }

        return root;
    }

    function removeTodoOverlay() {
        const root = document.getElementById(TODO_OVERLAY_ID);

        if (root) {
            root.remove();
        }
    }

    async function onTodoOverlayChange(event) {
        if (!event.target?.matches('input[type="checkbox"]')) {
            return;
        }

        const todoId = event.target.dataset.todoId;
        const nextItems = cleanTodoItems(currentState.todoItems).map((item) => {
            if (item.id !== todoId) {
                return item;
            }

            return {
                ...item,
                done: event.target.checked
            };
        });

        currentState.todoItems = nextItems;
        renderTodoOverlay();

        try {
            await sendRuntimeMessage({
                type: "saveTodoItems",
                todoItems: nextItems
            });
        } catch {
            await storageSet({ todoItems: nextItems });
        }
    }

    async function completeAllTodosFromOverlay(event) {
        event.preventDefault();
        event.stopPropagation();

        const items = cleanTodoItems(currentState.todoItems);

        if (items.length === 0) {
            return;
        }

        const root = document.getElementById(TODO_OVERLAY_ID);
        const button = root?.shadowRoot?.querySelector(".complete-all-button");

        if (button) {
            button.disabled = true;
            button.textContent = "Completing...";
        }

        currentState.todoItems = [];
        renderTodoOverlay();

        try {
            await sendRuntimeMessage({
                type: "completeAllTodoItems"
            });
        } catch {
            await storageSet({ todoItems: [] });
        }
    }

    function renderTodoOverlay() {
        if (!currentState.serverToken || currentState.todoOverlayEnabled === false) {
            removeTodoOverlay();
            return;
        }

        const root = getTodoOverlayRoot();
        const shadow = root?.shadowRoot;

        if (!shadow) {
            scheduleRefresh(100);
            return;
        }

        applyOverlayPosition(
            root,
            currentState.todoOverlayPosition,
            { left: Math.max(14, window.innerWidth - 274), top: Math.max(14, window.innerHeight - 250) }
        );

        const items = cleanTodoItems(currentState.todoItems);
        const list = shadow.querySelector(".todo-list");
        const count = shadow.querySelector(".todo-count");
        const completeAllButton = shadow.querySelector(".complete-all-button");
        const remaining = items.filter((item) => !item.done).length;

        count.textContent = items.length > 0 ? `${remaining}/${items.length}` : "0";
        if (completeAllButton) {
            completeAllButton.disabled = items.length === 0;
            completeAllButton.textContent = items.length === 0
                ? "No Tasks"
                : "Complete All";
        }
        list.replaceChildren();

        if (items.length === 0) {
            const empty = document.createElement("div");
            empty.className = "todo-empty";
            empty.textContent = "Add tasks from the extension popup.";
            list.append(empty);
            return;
        }

        items.forEach((item) => {
            const row = document.createElement("label");
            const checkbox = document.createElement("input");
            const text = document.createElement("span");

            row.className = item.done ? "todo-item done" : "todo-item";
            checkbox.type = "checkbox";
            checkbox.checked = item.done;
            checkbox.dataset.todoId = item.id;
            text.className = "todo-text";
            text.textContent = item.text;

            row.append(checkbox, text);
            list.append(row);
        });
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

    function toggleOverlayMinimized(event) {
        event.preventDefault();
        event.stopPropagation();
        overlayMinimized = !overlayMinimized;

        const root = document.getElementById(OVERLAY_ID);
        const timer = root?.shadowRoot?.querySelector(".timer");
        const button = root?.shadowRoot?.querySelector(".minimize-button");

        if (timer) {
            timer.classList.toggle("minimized", overlayMinimized);
        }

        if (button) {
            button.textContent = overlayMinimized ? "+" : "-";
            button.title = overlayMinimized ? "Show overlay" : "Minimize overlay";
        }
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

        if (summary.offlineQueued) {
            return {
                text: "Saved offline. Will upload automatically when sync works.",
                type: "pending",
                buttonText: "Saved offline"
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
        const shadowTimer = root?.shadowRoot;

        if (!shadowTimer) {
            scheduleRefresh(100);
            return;
        }

        shadowTimer.querySelector(".label").textContent = "StudyStreak";
        shadowTimer.querySelector(".time").textContent = "Stopped";
        shadowTimer.querySelector(".subject").textContent = "Focus session ended";
        setOverlayStatus(stopStatus.text || "Stopping...", stopStatus.type || "pending");
    }

    function scheduleStoppedOverlayRemoval(delay = 2500) {
        if (removeAfterStopTimerId !== null) {
            clearTimeout(removeAfterStopTimerId);
        }

        removeAfterStopTimerId = setTimeout(() => {
            keepOverlayAfterStop = false;
            pendingReviewSummary = null;
            removeAfterStopTimerId = null;
            removeOverlay();
        }, delay);
    }

    function hideReviewPanel() {
        const root = document.getElementById(OVERLAY_ID);
        const panel = root?.shadowRoot?.querySelector(".review-panel");

        if (panel) {
            panel.classList.remove("visible");
        }
    }

    function getDefaultReviewNote(summary) {
        const completedTodos = cleanTodoItems(summary?.completedTodos || summary?.todoSnapshot || [])
            .filter((item) => item.done);

        if (completedTodos.length === 0) {
            return "";
        }

        return [
            "Completed:",
            ...completedTodos.map((item) => `- ${item.text}`)
        ].join("\n");
    }

    function showReviewPanel(summary) {
        const root = getOverlayRoot();
        const shadow = root?.shadowRoot;

        if (!shadow || !summary?.completedAt) {
            scheduleRefresh(100);
            return;
        }

        pendingReviewSummary = summary;

        const topicSelect = shadow.querySelector(".review-topic");
        const noteInput = shadow.querySelector(".review-note");
        const panel = shadow.querySelector(".review-panel");
        const topics = getSubjectTopics(summary.subject);

        topicSelect.replaceChildren();

        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "No topic";
        topicSelect.append(emptyOption);

        topics.forEach((topic) => {
            const option = document.createElement("option");
            option.value = topic;
            option.textContent = topic;
            topicSelect.append(option);
        });

        topicSelect.value = topics.includes(summary.topic) ? summary.topic : "";
        noteInput.value = summary.reviewNote || getDefaultReviewNote(summary);
        panel.classList.add("visible");
        noteInput.focus();
    }

    async function saveReviewFromOverlay(event) {
        event.preventDefault();
        event.stopPropagation();

        if (!pendingReviewSummary?.completedAt) {
            setOverlayStatus("No completed session to review.", "failure");
            return;
        }

        const root = getOverlayRoot();
        const shadow = root?.shadowRoot;

        if (!shadow) {
            setOverlayStatus("Overlay is still loading. Try again.", "pending");
            return;
        }

        const saveButton = shadow.querySelector(".save-review");
        const skipButton = shadow.querySelector(".skip-review");
        const topic = shadow.querySelector(".review-topic").value;
        const reviewNote = shadow.querySelector(".review-note").value;

        saveButton.disabled = true;
        skipButton.disabled = true;
        saveButton.textContent = "Saving...";
        setOverlayStatus("Saving review...", "pending");

        try {
            const result = await sendRuntimeMessage({
                type: "saveFocusReview",
                completedAt: pendingReviewSummary.completedAt,
                topic,
                reviewNote
            });

            if (!result?.ok) {
                setOverlayStatus(result?.error || "Review saved locally, but sync failed.", "failure");
                saveButton.textContent = "Save";
                saveButton.disabled = false;
                skipButton.disabled = false;
                return;
            }

            hideReviewPanel();
            setOverlayStatus("Review synced.", "success");
            scheduleStoppedOverlayRemoval();
        } catch {
            setOverlayStatus("Review sync failed.", "failure");
            saveButton.textContent = "Save";
            saveButton.disabled = false;
            skipButton.disabled = false;
        }
    }

    async function skipReviewFromOverlay(event) {
        event.preventDefault();
        event.stopPropagation();

        if (pendingReviewSummary?.completedAt) {
            try {
                await sendRuntimeMessage({
                    type: "skipFocusReview",
                    completedAt: pendingReviewSummary.completedAt
                });
            } catch {
                // The session is already stopped; skipping can still close the local prompt.
            }
        }

        hideReviewPanel();
        setOverlayStatus("Review skipped.", "success");
        scheduleStoppedOverlayRemoval(1800);
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
            const summary = await sendRuntimeMessage({ type: "stopFocus" });
            const result = getStopResultMessage(summary);
            button.textContent = result.buttonText;
            setOverlayStatus(result.text, result.type);
            await refreshState();

            if (summary?.completedAt) {
                showReviewPanel(summary);
                return;
            }

            scheduleStoppedOverlayRemoval(5000);
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
        pendingReviewSummary = null;
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
        const shadowTimer = root?.shadowRoot;

        if (!shadowTimer) {
            scheduleRefresh(100);
            return;
        }

        const timerCard = shadowTimer.querySelector(".timer");
        const minimizeButton = shadowTimer.querySelector(".minimize-button");
        timerCard?.classList.toggle("minimized", overlayMinimized);
        if (minimizeButton) {
            minimizeButton.textContent = overlayMinimized ? "+" : "-";
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
        hideReviewPanel();

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

    function repairMissingOverlays() {
        if (currentState.focusActive && !document.getElementById(OVERLAY_ID)) {
            renderOverlay();
        }

        if (
            currentState.serverToken &&
            currentState.todoOverlayEnabled !== false &&
            !document.getElementById(TODO_OVERLAY_ID)
        ) {
            renderTodoOverlay();
        }
    }

    function startOverlayWatchdog() {
        if (overlayWatchdogId === null) {
            overlayWatchdogId = setInterval(repairMissingOverlays, 1500);
        }

        if (!overlayObserver && document.documentElement) {
            overlayObserver = new MutationObserver(repairMissingOverlays);
            overlayObserver.observe(document.documentElement, {
                childList: true
            });
            return;
        }

        if (!overlayObserver) {
            setTimeout(startOverlayWatchdog, 100);
        }
    }

    function scheduleRefresh(delayMs = 0) {
        const timerId = setTimeout(() => {
            startupRefreshTimerIds = startupRefreshTimerIds.filter((id) => id !== timerId);
            refreshState().catch(() => {});
        }, delayMs);

        startupRefreshTimerIds.push(timerId);
    }

    function scheduleStartupRefreshes() {
        [0, 100, 400, 1000, 2000, 4000].forEach(scheduleRefresh);
    }

    function bindPageLifecycleRefreshes() {
        window.addEventListener("pageshow", () => scheduleRefresh(0));
        window.addEventListener("focus", () => scheduleRefresh(0));
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) {
                scheduleRefresh(0);
            }
        });
        document.addEventListener("DOMContentLoaded", () => scheduleRefresh(0));
        window.addEventListener("load", () => scheduleRefresh(0));
        document.addEventListener("readystatechange", () => scheduleRefresh(0));
    }

    async function refreshState() {
        currentState = {
            ...currentState,
            ...(await storageGet(STORAGE_KEYS))
        };

        renderOverlay();
        renderTodoOverlay();
        repairMissingOverlays();
    }

    window.__studyStreakRefreshOverlay = refreshState;
    bindPageLifecycleRefreshes();
    startOverlayWatchdog();

    chrome.storage.onChanged.addListener((changes, areaName) => {
        if (areaName !== "local") {
            return;
        }

        let focusChanged = false;
        let todoChanged = false;

        FOCUS_STORAGE_KEYS.forEach((key) => {
            if (changes[key]) {
                currentState[key] = changes[key].newValue;
                focusChanged = true;
            }
        });

        TODO_STORAGE_KEYS.forEach((key) => {
            if (changes[key]) {
                currentState[key] = changes[key].newValue;
                todoChanged = true;
            }
        });

        if (focusChanged) {
            renderOverlay();
        }

        if (todoChanged) {
            renderTodoOverlay();
        }
    });

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message?.type !== "refreshStudyStreakOverlay") {
            return false;
        }

        refreshState()
            .then(() => sendResponse({ ok: true }))
            .catch((error) => {
                sendResponse({
                    ok: false,
                    error: String(error?.message || error || "Overlay refresh failed.")
                });
            });

        return true;
    });

    scheduleStartupRefreshes();
})();
