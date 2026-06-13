const remindersEnabled = document.querySelector("#reminders-enabled");
const saveButton = document.querySelector("#save-button");
const testButton = document.querySelector("#test-button");
const statusText = document.querySelector("#status");
const allowedDomains = document.querySelector("#allowed-domains");
const startFocusButton = document.querySelector("#start-focus-button");
const focusSubject = document.querySelector("#focus-subject");
const refreshSubjectsButton = document.querySelector("#refresh-subjects-button");
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
const accountStatus = document.querySelector("#account-status");
const loginUsername = document.querySelector("#login-username");
const loginPassword = document.querySelector("#login-password");
const loginButton = document.querySelector("#login-button");
const logoutButton = document.querySelector("#logout-button");
const tabButtons = document.querySelectorAll(".side-tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");
const todaySessions = document.querySelector("#today-sessions");
const strictFocusEnabled = document.querySelector("#strict-focus-enabled");
const pomodoroEnabledInput = document.querySelector("#pomodoro-enabled");
const pomodoroState = document.querySelector("#pomodoro-state");

let latestCompletedFocusSession = null;
let currentSettings = {
    serverUsername: "",
    serverToken: "",
    focusActive: false,
    pomodoroEnabled: false,
    syncedSubjects: [],
    syncedSubjectWebsites: {}
};

const EMPTY_SUMMARY = {
    focusActive: false,
    score: 0,
    focusedSeconds: 0,
    distractedSeconds: 0,
    idleSeconds: 0,
    lastDomain: "none",
    lastCategory: "idle",
    topDistractedDomain: "none",
    pomodoroEnabled: false,
    pomodoroPhase: "work",
    pomodoroSecondsLeft: null,
    pomodoroWorkBlocksCompleted: 0
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

function formatClock(seconds) {
    const safeSeconds = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(safeSeconds / 60);
    const remainingSeconds = safeSeconds % 60;
    return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function formatFocusSummaryText(summary) {
    return [
        "StudyStreak focus summary",
        `Subject: ${summary.subject || "unknown"}`,
        `Score: ${summary.score}%`,
        `Focused: ${formatSeconds(summary.focusedSeconds)}`,
        `Distracted: ${formatSeconds(summary.distractedSeconds)}`,
        `Idle: ${formatSeconds(summary.idleSeconds)}`,
        `Server upload: ${formatServerUpload(summary)}`,
        `Quality sync: ${formatQualityUpload(summary)}`,
        `Top distraction: ${summary.topDistractedDomain || "none"}`
    ].join("\n");
}

function formatServerUpload(summary) {
    if (summary.serverUpload?.ok) {
        return `Uploaded ${summary.serverUpload.minutes} min`;
    }

    return summary.serverUpload?.error || "Not uploaded";
}

function formatQualityUpload(summary) {
    if (summary.qualityUpload?.ok) {
        return "Synced";
    }

    return summary.qualityUpload?.error || "Not synced";
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];


function getTodayDayName() {
    return DAY_NAMES[new Date().getDay()];
}


function getTodayTimetableSessions(settings = currentSettings) {
    const timetable = Array.isArray(settings?.syncedTimetable)
        ? settings.syncedTimetable
        : [];

    return timetable
        .filter((session) => session.day === getTodayDayName())
        .sort((a, b) => String(a.start_time).localeCompare(String(b.start_time)));
}

function getSubjectWebsites(subject, settings = currentSettings) {
    const subjectWebsites = settings?.syncedSubjectWebsites || {};
    const cleanSubject = String(subject || "").trim().toLowerCase();
    const websites = subjectWebsites[cleanSubject];

    return Array.isArray(websites) ? websites : [];
}

function renderFocusWebsitesForSubject(subject) {
    const websites = getSubjectWebsites(subject);

    allowedDomains.value = websites.length > 0
        ? websites.join("\n")
        : currentSettings.allowedDomains.join("\n");
}

function renderTodaySessions(settings = currentSettings) {
    const sessions = getTodayTimetableSessions(settings);

    if (!todaySessions) {
        return;
    }

    if (sessions.length === 0) {
        todaySessions.textContent = "No sessions today.";
        return;
    }

    todaySessions.innerHTML = sessions
        .map((session) => {
            const subject = session.subject || "unknown";
            const startTime = session.start_time || "--:--";
            const minutes = Number(session.minutes) || 0;

            return `
                <div class="today-session-item">
                    <strong>${subject}</strong>
                    <span>${startTime} - ${minutes} min</span>
                </div>
            `;
        })
        .join("");
}


function renderCompletedSummary(summary) {
    latestCompletedFocusSession = summary || null;
    copySummaryButton.disabled = !isLoggedIn(currentSettings) || !latestCompletedFocusSession;
    copyJsonButton.disabled = !isLoggedIn(currentSettings) || !latestCompletedFocusSession;

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
                    <span>Subject: ${session.subject || "unknown"}</span>
                    <strong>${session.score}%</strong>
                    <span>${formatSeconds(session.focusedSeconds)} focused</span>
                    <span>Top distraction: ${session.topDistractedDomain || "none"}</span>
                </div>
            `;
        })
        .join("");
}

function getSyncedSubjects(settings = currentSettings) {
    return Array.isArray(settings?.syncedSubjects) ? settings.syncedSubjects : [];
}

function hasSyncedSubjects(settings = currentSettings) {
    return getSyncedSubjects(settings).length > 0;
}

function renderSubjectOptions(subjects, selectedSubject = "") {
    const safeSubjects = Array.isArray(subjects) ? subjects : [];
    focusSubject.innerHTML = "";

    if (safeSubjects.length === 0) {
        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "No synced subjects";
        focusSubject.append(emptyOption);
        focusSubject.disabled = true;
        return;
    }

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = "Choose a subject";
    focusSubject.append(placeholderOption);

    safeSubjects.forEach((subject) => {
        const option = document.createElement("option");
        option.value = subject;
        option.textContent = subject;
        focusSubject.append(option);
    });

    focusSubject.value = safeSubjects.includes(selectedSubject)
        ? selectedSubject
        : "";
    
    renderFocusWebsitesForSubject(focusSubject.value);

    focusSubject.disabled = !isLoggedIn(currentSettings) || currentSettings.focusActive;
}

function renderFocusSummary(summary) {
    const safeSummary = {
        ...EMPTY_SUMMARY,
        ...(summary || {})
    };

    currentSettings.focusActive = safeSummary.focusActive;
    currentSettings.pomodoroEnabled = safeSummary.pomodoroEnabled;
    startFocusButton.disabled = (
        !isLoggedIn(currentSettings) ||
        safeSummary.focusActive ||
        !hasSyncedSubjects(currentSettings)
    );
    stopFocusButton.disabled = !isLoggedIn(currentSettings) || !safeSummary.focusActive;
    focusSubject.disabled = (
        !isLoggedIn(currentSettings) ||
        safeSummary.focusActive ||
        !hasSyncedSubjects(currentSettings)
    );
    pomodoroEnabledInput.disabled = !isLoggedIn(currentSettings) || safeSummary.focusActive;

    if (safeSummary.focusActive && safeSummary.pomodoroEnabled) {
        const phaseLabel = safeSummary.pomodoroPhase === "break" ? "Break" : "Work";
        focusState.textContent = `Pomodoro ${phaseLabel} is running.`;
        pomodoroState.textContent =
            `${phaseLabel}: ${formatClock(safeSummary.pomodoroSecondsLeft)} | ` +
            `Completed work blocks: ${safeSummary.pomodoroWorkBlocksCompleted}`;
    } else {
        focusState.textContent = safeSummary.focusActive
            ? "Focus is running."
            : "Focus is stopped.";
        pomodoroState.textContent = pomodoroEnabledInput.checked
            ? "Pomodoro 50/10 ready."
            : "";
    }

    focusScore.textContent = `Focus quality: ${safeSummary.score}%`;
    focusTime.textContent =
        `Focused ${formatSeconds(safeSummary.focusedSeconds)} | ` +
        `Distracted ${formatSeconds(safeSummary.distractedSeconds)} | ` +
        `Idle ${formatSeconds(safeSummary.idleSeconds)}`;
    focusDomain.textContent = `Current: ${safeSummary.lastDomain} (${safeSummary.lastCategory})`;
}

function renderAccount(settings) {
    currentSettings = {
        ...currentSettings,
        ...(settings || {})
    };

    const loggedIn = isLoggedIn(settings);

    accountStatus.textContent = loggedIn
        ? `Logged in as ${settings.serverUsername}`
        : "Log in before using StudyStreak Companion.";

    logoutButton.disabled = !loggedIn;
    setAccountGate(settings);
}

function showPopupTab(tabName) {
    tabButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === tabName);
    });

    tabPanels.forEach((panel) => {
        panel.hidden = panel.dataset.panel !== tabName;
        panel.classList.toggle("active", panel.dataset.panel === tabName);
    });
}

function isLoggedIn(settings) {
    return Boolean(settings?.serverToken && settings?.serverUsername);
}

function setAccountGate(settings) {
    const loggedIn = isLoggedIn(settings);

    tabButtons.forEach((button) => {
        if (button.dataset.tab !== "account") {
            button.disabled = !loggedIn;
        }
    });

    saveButton.disabled = !loggedIn;
    testButton.disabled = !loggedIn;
    startFocusButton.disabled = !loggedIn || currentSettings.focusActive || !hasSyncedSubjects(settings);
    stopFocusButton.disabled = !loggedIn || !currentSettings.focusActive;
    copySummaryButton.disabled = !loggedIn || !latestCompletedFocusSession;
    copyJsonButton.disabled = !loggedIn || !latestCompletedFocusSession;
    clearHistoryButton.disabled = !loggedIn;
    refreshSubjectsButton.disabled = !loggedIn;
    focusSubject.disabled = !loggedIn || currentSettings.focusActive || !hasSyncedSubjects(settings);
    strictFocusEnabled.disabled = !loggedIn;
    pomodoroEnabledInput.disabled = !loggedIn || currentSettings.focusActive;

    if (!loggedIn) {
        showPopupTab("account");
    }
}

async function requireLogin() {
    const state = await chrome.runtime.sendMessage({
        type: "getCompanionState"
    });

    currentSettings = {
        ...currentSettings,
        ...(state?.settings || {})
    };

    renderAccount(currentSettings);

    if (!isLoggedIn(currentSettings)) {
        statusText.textContent = "Log in first.";
        showPopupTab("account");
        return false;
    }

    return true;
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
        allowedDomains.value = state.settings.allowedDomains.join("\n");
        strictFocusEnabled.checked = Boolean(state.settings.strictFocusEnabled);
        pomodoroEnabledInput.checked = Boolean(state.settings.pomodoroEnabled);

        currentSettings = {
            ...currentSettings,
            ...state.settings
        };

        renderTodaySessions(currentSettings);
        renderSubjectOptions(currentSettings.syncedSubjects, currentSettings.focusSubject);
        renderFocusSummary(state.summary);
        renderCompletedSummary(state.settings.lastCompletedFocusSession);
        renderFocusHistory(state.settings.focusHistory);
        renderAccount(currentSettings);
    } catch (error) {
        console.error(error);
        renderFocusSummary(EMPTY_SUMMARY);
        renderAccount({});
        statusText.textContent = "Reload the extension in chrome://extensions.";
    }
}

async function loginToServer() {
    const username = loginUsername.value.trim();
    const password = loginPassword.value;

    if (!username || !password) {
        statusText.textContent = "Enter username and password.";
        return;
    }

    const result = await chrome.runtime.sendMessage({
        type: "loginToServer",
        username,
        password
    });

    if (!result?.ok) {
        statusText.textContent = result?.error || "Login failed.";
        return;
    }

    loginPassword.value = "";
    loginUsername.value = result.serverUsername;
    currentSettings = {
        ...currentSettings,
        serverUsername: result.serverUsername,
        serverToken: "saved",
        syncedSubjects: result.subjects || [],
        syncedSubjectWebsites: result.subjectWebsites || {},
        syncedTimetable: result.timetable || []
    };

    renderTodaySessions(currentSettings);
    renderSubjectOptions(currentSettings.syncedSubjects, "");
    renderAccount(currentSettings);
    statusText.textContent = currentSettings.syncedSubjects.length > 0
        ? "Logged in."
        : "Logged in. Sync subjects in the terminal app, then refresh.";
    showPopupTab("focus");
}

async function logoutFromServer() {
    await chrome.runtime.sendMessage({ type: "logoutFromServer"});
    loginPassword.value = "";
    currentSettings = {
        ...currentSettings,
        serverUsername: "",
        serverToken: "",
        syncedSubjects: [],
        syncedSubjectWebsites: {},
        syncedTimetable: [],
        focusSubject: ""
    };

    renderTodaySessions(currentSettings);
    renderSubjectOptions([], "");
    renderAccount(currentSettings);
    statusText.textContent = "Logged out.";
    showPopupTab("account");
}

async function refreshSubjects() {
    if (!(await requireLogin())) {
        return;
    }

    const result = await chrome.runtime.sendMessage({
        type: "refreshSubjects"
    });

    if (!result?.ok) {
        statusText.textContent = result?.error || "Could not refresh subjects.";
        return;
    }

    currentSettings = {
        ...currentSettings,
        syncedSubjects: result.subjects || [],
        syncedSubjectWebsites: result.subjectWebsites || {},
        syncedTimetable: result.timetable || []
    };

    renderTodaySessions(currentSettings);
    renderSubjectOptions(currentSettings.syncedSubjects, currentSettings.focusSubject);
    setAccountGate(currentSettings);
    const timetableCount = Array.isArray(result.timetable) ? result.timetable.length : 0;
    statusText.textContent = currentSettings.syncedSubjects.length > 0
        ? `Subjects refreshed. ${timetableCount} timetable reminders scheduled.`
        : "No synced subjects yet.";
}

async function saveSettings(showMessage = true) {
    if (!(await requireLogin())) {
        return;
    }

    await chrome.runtime.sendMessage({
        type: "saveSettings",
        settings: {
            remindersEnabled: remindersEnabled.checked,
            strictFocusEnabled: strictFocusEnabled.checked,
            pomodoroEnabled: pomodoroEnabledInput.checked,
            allowedDomains: parseDomains(allowedDomains.value)
        }
    });

    if (showMessage) {
        statusText.textContent = "Saved.";
    }
}

async function saveReminderToggle() {
    if (!(await requireLogin())) {
        return;
    }

    await chrome.runtime.sendMessage({
        type: "saveSettings",
        settings: {
            remindersEnabled: remindersEnabled.checked,
            strictFocusEnabled: strictFocusEnabled.checked,
            pomodoroEnabled: pomodoroEnabledInput.checked,
            allowedDomains: parseDomains(allowedDomains.value)
        }
    });

    statusText.textContent = remindersEnabled.checked
        ? "Timetable notifications enabled."
        : "Timetable notifications disabled.";
}

async function testNotification() {
    if (!(await requireLogin())) {
        return;
    }

    await chrome.runtime.sendMessage({
        type: "testNotification"
    });

    statusText.textContent = "Test sent.";
}

async function startFocus() {
    if (!(await requireLogin())) {
        return;
    }

    const subject = focusSubject.value.trim();

    if (!subject) {
        statusText.textContent = "Choose a synced subject first.";
        return;
    }

    await saveSettings(false);
    const summary = await chrome.runtime.sendMessage({
        type: "startFocus",
        subject,
        pomodoroEnabled: pomodoroEnabledInput.checked
    });

    renderFocusSummary(summary);
    statusText.textContent = pomodoroEnabledInput.checked
        ? "Pomodoro started. Work blocks upload every 50 minutes."
        : "Focus started.";
}

async function stopFocus() {
    if (!(await requireLogin())) {
        return;
    }

    const summary = await chrome.runtime.sendMessage({
        type: "stopFocus"
    });

    renderFocusSummary(summary);
    const state = await chrome.runtime.sendMessage({
        type: "getCompanionState"
    });

    renderCompletedSummary(
        summary.completedAt
            ? summary
            : state.settings.lastCompletedFocusSession
    );
    renderFocusHistory(state.settings.focusHistory);

    if (!summary.completedAt && summary.serverUpload?.error) {
        statusText.textContent = summary.serverUpload.error;
        return;
    }

    const leaderboardStatus = summary.serverUpload?.ok
        ? `Leaderboard uploaded ${summary.serverUpload.minutes} min`
        : `Leaderboard failed: ${summary.serverUpload?.error || "Unknown error."}`;

    const qualityStatus = summary.qualityUpload?.ok
        ? "Quality synced"
        : `Quality failed: ${summary.qualityUpload?.error || "Unknown error."}`;

    statusText.textContent = `Focus stopped. ${leaderboardStatus}. ${qualityStatus}.`;
}

async function refreshFocusStatus() {
    const summary = await chrome.runtime.sendMessage({
        type: "getFocusStatus"
    });

    renderFocusSummary(summary);
}

async function copySummary() {
    if (!(await requireLogin())) {
        return;
    }

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
        subject: summary.subject || "unknown",
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
    if (!(await requireLogin())) {
        return;
    }

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
    if (!(await requireLogin())) {
        return;
    }

    await chrome.runtime.sendMessage({
        type: "clearFocusHistory"
    });

    renderCompletedSummary(null);
    renderFocusHistory([]);
    statusText.textContent = "Focus history cleared.";
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        showPopupTab(button.dataset.tab);
    });
});

remindersEnabled.addEventListener("change", saveReminderToggle);
focusSubject.addEventListener("change", () => {
    renderFocusWebsitesForSubject(focusSubject.value);
});
strictFocusEnabled.addEventListener("change", saveSettings);
pomodoroEnabledInput.addEventListener("change", saveSettings);
saveButton.addEventListener("click", saveSettings);
testButton.addEventListener("click", testNotification);
refreshSubjectsButton.addEventListener("click", refreshSubjects);
startFocusButton.addEventListener("click", startFocus);
stopFocusButton.addEventListener("click", stopFocus);
copySummaryButton.addEventListener("click", copySummary);
copyJsonButton.addEventListener("click", copySummaryJson);
clearHistoryButton.addEventListener("click", clearFocusHistory);
loginButton.addEventListener("click", loginToServer);
logoutButton.addEventListener("click", logoutFromServer);

setInterval(refreshFocusStatus, 2000);

loadSettings();
