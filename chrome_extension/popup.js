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

const EMPTY_SUMMARY = {
    focusActive: false,
    score: 0,
    focusedSeconds: 0,
    distractedSeconds: 0,
    idleSeconds: 0,
    lastDomain: "none",
    lastCategory: "idle"
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
    statusText.textContent = "Focus stopped.";
}

async function refreshFocusStatus() {
    const summary = await chrome.runtime.sendMessage({
        type: "getFocusStatus"
    });

    renderFocusSummary(summary);
}

saveButton.addEventListener("click", saveSettings);
testButton.addEventListener("click", testNotification);
startFocusButton.addEventListener("click", startFocus);
stopFocusButton.addEventListener("click", stopFocus);

setInterval(refreshFocusStatus, 2000);

loadSettings();
