const remindersEnabled = document.querySelector("#reminders-enabled");
const reminderTime = document.querySelector("#reminder-time");
const saveButton = document.querySelector("#save-button");
const testButton = document.querySelector("#test-button");
const statusText = document.querySelector("#status");
const allowedDomains = document.querySelector("#allowed-domains");
const startFocusButton = document.querySelector("#start-focus-button");
const stopFocusButton = document.querySelector("#stop-focus-button");
const focusState = document.querySelector("#focus-state");
const focusScore = document.querySelector("#focus-score");
const focusTime = document.querySelector("#focus-time");
const focusDomain = document.querySelector("#focus-domain");
const lastFocusSummary = document.querySelector("#last-focus-summary");
const copySummaryButton = document.querySelector("#copy-summary-button");
const focusHistory = document.querySelector("#focus-history");
const clearHistoryButton = document.querySelector("#clear-history-button");
const copyJsonButton = document.querySelector("#copy-json-button");
const importKey = document.querySelector("#import-key");

let latestCompletedFocusSession = null;

const EMPTY_SUMMARY = {
    focusActive: false,
    score: 0,
    focusedSeconds: 0,
    distractedSeconds: 0,
    idleSeconds: 0,
    lastDomain: "none",
    lastCategory: "idle",
    topDistractedDomain: "none"
};

function parseDomains(value) {
    return value
        .split(/\n|,/)
        .map((domain) => domain.trim())
        .filter(Boolean);
}

function formatSeconds(seconds) {
    const safeSeconds = Number.isFinite(seconds) ? seconds : 0;
    const minutes = Math.floor(safeSeconds / 60);
    const remainingSeconds = safeSeconds % 60;

    if (minutes <= 0) {
        return `${remainingSeconds}s`;
    }

    return `${minutes}m ${remainingSeconds}s`;
}

function formatFocusSummaryText(summary) {
    return [
        "StudyStreak focus summary",
        `Score: ${summary.score}%`,
        `Focused: ${formatSeconds(summary.focusedSeconds)}`,
        `Distracted: ${formatSeconds(summary.distractedSeconds)}`,
        `Idle: ${formatSeconds(summary.idleSeconds)}`,
        `Top distraction: ${summary.topDistractedDomain || "none"}`
    ].join("\n");
}

function renderCompletedSummary(summary) {
    latestCompletedFocusSession = summary || null;
    copySummaryButton.disabled = !latestCompletedFocusSession;
    copyJsonButton.disabled = !latestCompletedFocusSession;

    if (!latestCompletedFocusSession) {
        lastFocusSummary.textContent = "No completed focus session yet.";
        return;
    }

    lastFocusSummary.textContent = formatFocusSummaryText(latestCompletedFocusSession);
}

function renderFocusHistory(history) {
    const recentHistory = Array.isArray(history) ? history : [];

    if (recentHistory.length === 0) {
        focusHistory.textContent = "No focus history yet.";
        return;
    }

    focusHistory.innerHTML = recentHistory
        .map((session) => {
            return `
                <div class="history-item">
                    <strong>${session.score}%</strong>
                    <span>${formatSeconds(session.focusedSeconds)} focused</span>
                    <span>Top distraction: ${session.topDistractedDomain || "none"}</span>
                </div>
            `;
        })
        .join("");
}

function renderFocusSummary(summary) {
    const safeSummary = {
        ...EMPTY_SUMMARY,
        ...(summary || {})
    };

    startFocusButton.disabled = safeSummary.focusActive;
    stopFocusButton.disabled = !safeSummary.focusActive;

    focusState.textContent = safeSummary.focusActive
        ? "Focus is running."
        : "Focus is stopped.";
    focusScore.textContent = `Focus quality: ${safeSummary.score}%`;
    focusTime.textContent =
        `Focused ${formatSeconds(safeSummary.focusedSeconds)} | ` +
        `Distracted ${formatSeconds(safeSummary.distractedSeconds)} | ` +
        `Idle ${formatSeconds(safeSummary.idleSeconds)}`;
    focusDomain.textContent = `Current: ${safeSummary.lastDomain} (${safeSummary.lastCategory})`;
}

async function loadSettings() {
    try {
        const state = await chrome.runtime.sendMessage({
            type: "getCompanionState"
        });

        if (!state?.settings || !state?.summary) {
            throw new Error("Background worker did not return companion state.");
        }

        remindersEnabled.checked = state.settings.remindersEnabled;
        reminderTime.value = state.settings.reminderTime;
        allowedDomains.value = state.settings.allowedDomains.join("\n");

        renderFocusSummary(state.summary);
        renderCompletedSummary(state.settings.lastCompletedFocusSession);
        renderFocusHistory(state.settings.focusHistory);
    } catch (error) {
        console.error(error);
        renderFocusSummary(EMPTY_SUMMARY);
        statusText.textContent = "Reload the extension in chrome://extensions.";
    }
}

async function saveSettings(showMessage = true) {
    await chrome.runtime.sendMessage({
        type: "saveSettings",
        settings: {
            remindersEnabled: remindersEnabled.checked,
            reminderTime: reminderTime.value || "17:00",
            allowedDomains: parseDomains(allowedDomains.value)
        }
    });

    if (showMessage) {
        statusText.textContent = "Saved.";
    }
}

async function testNotification() {
    await chrome.runtime.sendMessage({
        type: "testNotification"
    });

    statusText.textContent = "Test sent.";
}

async function startFocus() {
    await saveSettings(false);

    const summary = await chrome.runtime.sendMessage({
        type: "startFocus"
    });

    renderFocusSummary(summary);
    statusText.textContent = "Focus started.";
}

async function stopFocus() {
    const summary = await chrome.runtime.sendMessage({
        type: "stopFocus"
    });

    renderFocusSummary(summary);
    renderCompletedSummary(summary);
    const state = await chrome.runtime.sendMessage({
        type: "getCompanionState"
    });

    renderFocusHistory(state.settings.focusHistory);
    statusText.textContent = "Focus stopped.";
}

async function refreshFocusStatus() {
    const summary = await chrome.runtime.sendMessage({
        type: "getFocusStatus"
    });

    renderFocusSummary(summary);
}

async function copySummary() {
    if (!latestCompletedFocusSession) {
        return;
    }    

    await navigator.clipboard.writeText(
        formatFocusSummaryText(latestCompletedFocusSession)
    );

    statusText.textContent = "Summary copied.";
}

function buildFocusSummaryJson(summary) {
    return {
        source: "chrome_extension",
        score: summary.score,
        focused_seconds: summary.focusedSeconds,
        distracted_seconds: summary.distractedSeconds,
        idle_seconds: summary.idleSeconds,
        top_distracted_domain: summary.topDistractedDomain || "none",
        completed_at: summary.completedAt
    };
}

function stableStringify(value) {
    if (value === null || typeof value !== "object") {
        return JSON.stringify(value);
    }

    if (Array.isArray(value)) {
        return `[${value.map(stableStringify).join(",")}]`;
    }

    return `{${Object.keys(value).sort().map((key) => {
        return `${JSON.stringify(key)}:${stableStringify(value[key])}`;
    }).join(",")}}`;
}

async function signFocusSummary(payload, secret) {
    const encoder = new TextEncoder();

    const key = await crypto.subtle.importKey(
        "raw",
        encoder.encode(secret),
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
    );

    const signature = await crypto.subtle.sign(
        "HMAC",
        key,
        encoder.encode(stableStringify(payload))
    );

    return [...new Uint8Array(signature)]
        .map((byte) => byte.toString(16).padStart(2, "0"))
        .join("");
}

async function copySummaryJson() {
    if (!latestCompletedFocusSession) {
        return;
    }

    const secret = importKey.value.trim();

    if (!secret) {
        statusText.textContent = "Enter import key first.";
        return;
    }

    const payload = buildFocusSummaryJson(latestCompletedFocusSession);
    const signature = await signFocusSummary(payload, secret);

    await navigator.clipboard.writeText(
        JSON.stringify(
            {
                payload,
                signature
            },
            null,
            2
        )
    );

    statusText.textContent = "Signed JSON copied.";
}

async function clearFocusHistory() {
    await chrome.runtime.sendMessage({
        type: "clearFocusHistory"
    });

    renderCompletedSummary(null);
    renderFocusHistory([]);
    statusText.textContent = "Focus history cleared.";
}

saveButton.addEventListener("click", saveSettings);
testButton.addEventListener("click", testNotification);
startFocusButton.addEventListener("click", startFocus);
stopFocusButton.addEventListener("click", stopFocus);
copySummaryButton.addEventListener("click", copySummary);
copyJsonButton.addEventListener("click", copySummaryJson);
clearHistoryButton.addEventListener("click", clearFocusHistory);

setInterval(refreshFocusStatus, 2000);

loadSettings();
