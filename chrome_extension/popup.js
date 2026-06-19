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
const todoOverlayEnabled = document.querySelector("#todo-overlay-enabled");
const newTodoInput = document.querySelector("#new-todo-input");
const addTodoButton = document.querySelector("#add-todo-button");
const todoList = document.querySelector("#todo-list");
const clearCompletedTodosButton = document.querySelector("#clear-completed-todos-button");
const focusReviewPanel = document.querySelector("#focus-review-panel");
const focusReviewTopic = document.querySelector("#focus-review-topic");
const focusReviewNote = document.querySelector("#focus-review-note");
const saveFocusReviewButton = document.querySelector("#save-focus-review-button");
const skipFocusReviewButton = document.querySelector("#skip-focus-review-button");
const serverStatus = document.querySelector("#server-status");
const syncAccountStatus = document.querySelector("#sync-account-status");
const syncStatusLabel = document.querySelector("#sync-status-label");
const retrySyncButton = document.querySelector("#retry-sync-button");
const setupGuide = document.querySelector("#setup-guide");
const homeKicker = document.querySelector("#home-kicker");
const homeTitle = document.querySelector("#home-title");
const homeDetail = document.querySelector("#home-detail");
const homePrimaryButton = document.querySelector("#home-primary-button");
const homeFocusSetupButton = document.querySelector("#home-focus-setup-button");
const homeTodoButton = document.querySelector("#home-todo-button");
const homeSubject = document.querySelector("#home-subject");
const homeMode = document.querySelector("#home-mode");
const homeTodoSummary = document.querySelector("#home-todo-summary");
const homeTodaySummary = document.querySelector("#home-today-summary");

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

let latestCompletedFocusSession = null;
let currentSettings = {
    serverUsername: "",
    serverToken: "",
    focusActive: false,
    pomodoroEnabled: false,
    selectedFocusSubject: "",
    syncedSubjects: [],
    syncedSubjectWebsites: {},
    syncedSubjectTopics: {},
    todoOverlayEnabled: true,
    todoItems: [],
    todoSyncPending: false,
    offlineUploadQueue: [],
    lastSyncStatus: {
        state: "idle",
        message: "Not synced yet.",
        at: null
    }
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

function createTodoId() {
    if (crypto?.randomUUID) {
        return crypto.randomUUID();
    }

    return `todo-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
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

function formatRelativeTime(isoValue) {
    if (!isoValue) {
        return "never";
    }

    const then = Date.parse(isoValue);

    if (!Number.isFinite(then)) {
        return "unknown";
    }

    const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));

    if (seconds < 60) {
        return "just now";
    }

    const minutes = Math.floor(seconds / 60);

    if (minutes < 60) {
        return `${minutes} min ago`;
    }

    const hours = Math.floor(minutes / 60);
    return `${hours} hr ago`;
}

function formatFocusSummaryText(summary) {
    const lines = [
        "StudyStreak focus summary",
        `Subject: ${summary.subject || "unknown"}`,
        `Topic: ${summary.topic || "none"}`,
        `Score: ${summary.score}%`,
        `Focused: ${formatSeconds(summary.focusedSeconds)}`,
        `Distracted: ${formatSeconds(summary.distractedSeconds)}`,
        `Idle: ${formatSeconds(summary.idleSeconds)}`,
        `Server upload: ${formatServerUpload(summary)}`,
        `Quality sync: ${formatQualityUpload(summary)}`,
        `Queue: ${summary.offlineQueued ? "Waiting for retry" : "none"}`,
        `Top distraction: ${summary.topDistractedDomain || "none"}`
    ];

    const completedTodos = cleanTodoItems(summary.completedTodos || summary.todoSnapshot || [])
        .filter((item) => item.done);

    if (completedTodos.length > 0) {
        lines.push("Completed todos:");
        completedTodos.forEach((item) => lines.push(`- ${item.text}`));
    }

    if (summary.reviewNote) {
        lines.push(`Review note: ${summary.reviewNote}`);
    }

    return lines.join("\n");
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

function getSubjectTopics(subject, settings = currentSettings) {
    const subjectTopics = settings?.syncedSubjectTopics || {};
    const cleanSubject = String(subject || "").trim().toLowerCase();
    const topics = subjectTopics[cleanSubject];

    return Array.isArray(topics) ? topics : [];
}

function renderFocusWebsitesForSubject(subject) {
    const websites = getSubjectWebsites(subject);

    allowedDomains.value = websites.join("\n");
}

function hideFocusReviewPanel() {
    if (focusReviewPanel) {
        focusReviewPanel.hidden = true;
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

function showFocusReviewPanel(summary) {
    if (!focusReviewPanel || !summary?.completedAt) {
        return;
    }

    const topics = getSubjectTopics(summary.subject);

    focusReviewTopic.replaceChildren();

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "No topic";
    focusReviewTopic.append(emptyOption);

    topics.forEach((topic) => {
        const option = document.createElement("option");
        option.value = topic;
        option.textContent = topic;
        focusReviewTopic.append(option);
    });

    focusReviewTopic.value = topics.includes(summary.topic) ? summary.topic : "";
    focusReviewNote.value = summary.reviewNote || getDefaultReviewNote(summary);
    focusReviewPanel.dataset.completedAt = summary.completedAt;
    focusReviewPanel.hidden = false;
}

function showPendingFocusReviewIfNeeded(summary) {
    if (summary?.reviewPending) {
        showFocusReviewPanel(summary);
    } else {
        hideFocusReviewPanel();
    }
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

    todaySessions.replaceChildren();

    sessions.forEach((session) => {
        const item = document.createElement("div");
        const subject = document.createElement("strong");
        const details = document.createElement("span");
        const startTime = session.start_time || "--:--";
        const minutes = Number(session.minutes) || 0;

        item.className = "today-session-item";
        subject.textContent = session.subject || "unknown";
        details.textContent = `${startTime} - ${minutes} min`;

        item.append(subject, details);
        todaySessions.append(item);
    });
}

function hasAnySavedWebsite(settings = currentSettings) {
    const subjectWebsites = settings?.syncedSubjectWebsites || {};

    return Object.values(subjectWebsites).some((websites) => {
        return Array.isArray(websites) && websites.length > 0;
    });
}

function setSetupStep(stepName, complete) {
    const item = setupGuide?.querySelector(`[data-step="${stepName}"]`);

    if (item) {
        item.classList.toggle("complete", complete);
    }
}

function renderSetupGuide(settings = currentSettings) {
    if (!setupGuide) {
        return;
    }

    const loggedIn = isLoggedIn(settings);
    const hasSubjects = getSyncedSubjects(settings).length > 0;
    const hasWebsites = hasAnySavedWebsite(settings);
    const hasFocused = Boolean(settings.focusActive || settings.lastCompletedFocusSession);
    const setupComplete = loggedIn && hasSubjects && hasWebsites && hasFocused;

    setupGuide.hidden = setupComplete;

    setSetupStep("login", loggedIn);
    setSetupStep("subjects", hasSubjects);
    setSetupStep("websites", hasWebsites);
    setSetupStep("focus", hasFocused);
}

function renderSyncOverview(settings = currentSettings) {
    const loggedIn = isLoggedIn(settings);
    const queueCount = Array.isArray(settings.offlineUploadQueue)
        ? settings.offlineUploadQueue.length
        : 0;
    const todoPending = Boolean(settings.todoSyncPending);
    const syncStatus = settings.lastSyncStatus || {};
    const state = queueCount > 0 || todoPending
        ? "pending"
        : (syncStatus.state || "idle");
    const statusTextMap = {
        synced: "Synced",
        pending: "Pending upload",
        failed: "Failed",
        idle: "Idle"
    };
    const detail = syncStatus.message || "Not synced yet.";
    const when = syncStatus.at ? ` (${formatRelativeTime(syncStatus.at)})` : "";

    serverStatus.textContent = state === "failed" ? "Check needed" : "Ready";
    serverStatus.className = state === "failed" ? "bad" : "good";
    syncAccountStatus.textContent = loggedIn
        ? `Logged in as ${settings.serverUsername}`
        : "Logged out";
    syncStatusLabel.textContent = `${statusTextMap[state] || "Idle"} - ${detail}${when}`;
    syncStatusLabel.className = state;
    retrySyncButton.disabled = !loggedIn || (queueCount === 0 && !todoPending && state !== "failed");

    renderSetupGuide(settings);
}

function getPreferredSubject(settings = currentSettings) {
    const subjects = getSyncedSubjects(settings);
    const selectedSubject = String(
        settings.selectedFocusSubject || settings.focusSubject || ""
    ).trim().toLowerCase();
    const matchingSubject = subjects.find((subject) => {
        return String(subject).trim().toLowerCase() === selectedSubject;
    });

    if (matchingSubject) {
        return matchingSubject;
    }

    const subjectWebsites = settings.syncedSubjectWebsites || {};
    const subjectWithWebsite = subjects.find((subject) => {
        const websites = subjectWebsites[subject] || subjectWebsites[String(subject).toLowerCase()];
        return Array.isArray(websites) && websites.length > 0;
    });

    return subjectWithWebsite || subjects[0] || "";
}

function getHomeTodoText(settings = currentSettings) {
    const todoItems = cleanTodoItems(settings.todoItems);
    const remaining = todoItems.filter((item) => !item.done).length;

    if (remaining === 0) {
        return todoItems.length === 0 ? "No tasks yet" : "All done";
    }

    return `${remaining} active task${remaining === 1 ? "" : "s"}`;
}

function getHomeTodayText(settings = currentSettings) {
    const sessions = getTodayTimetableSessions(settings);

    if (sessions.length === 0) {
        return "No sessions today";
    }

    const nextSession = sessions[0];
    const subject = nextSession.subject || "session";
    const startTime = nextSession.start_time || "--:--";
    return `${startTime} ${subject}`;
}

function renderHomePanel(summary = EMPTY_SUMMARY) {
    if (!homePrimaryButton) {
        return;
    }

    const safeSummary = {
        ...EMPTY_SUMMARY,
        ...(summary || {})
    };
    const loggedIn = isLoggedIn(currentSettings);
    const subjects = getSyncedSubjects(currentSettings);
    const preferredSubject = getPreferredSubject(currentSettings);
    const websites = getSubjectWebsites(preferredSubject, currentSettings);
    const hasSubjects = subjects.length > 0;
    const hasWebsites = websites.length > 0;
    const modeText = currentSettings.pomodoroEnabled || safeSummary.pomodoroEnabled
        ? "Pomodoro 50/10"
        : "Custom focus";
    let action = "start";

    homeSubject.textContent = preferredSubject || "none";
    homeMode.textContent = safeSummary.focusActive ? "Focus running" : modeText;
    homeTodoSummary.textContent = getHomeTodoText(currentSettings);
    homeTodaySummary.textContent = getHomeTodayText(currentSettings);

    if (!loggedIn) {
        action = "account";
        homeKicker.textContent = "Account needed";
        homeTitle.textContent = "Log in to sync your study setup";
        homeDetail.textContent = "Use your StudyStreak account to load subjects, websites, todos, and timetable reminders.";
        homePrimaryButton.textContent = "Go to Account";
    } else if (safeSummary.focusActive) {
        action = "stop";
        homeKicker.textContent = "In focus";
        homeTitle.textContent = safeSummary.pomodoroEnabled
            ? `${safeSummary.pomodoroPhase === "break" ? "Break" : "Work"} ${formatClock(safeSummary.pomodoroSecondsLeft)}`
            : `Focused ${formatSeconds(safeSummary.focusedSeconds)}`;
        homeDetail.textContent =
            `${preferredSubject || "Focus"} is running. Stop when you are done, then add a quick review note.`;
        homePrimaryButton.textContent = "Stop Focus";
    } else if (!hasSubjects) {
        action = "refresh";
        homeKicker.textContent = "Setup";
        homeTitle.textContent = "Sync your subjects";
        homeDetail.textContent = "Bring in subjects, topics, websites, timetable sessions, and todos from your StudyStreak account.";
        homePrimaryButton.textContent = "Refresh Subjects";
    } else if (!preferredSubject || !hasWebsites) {
        action = "setup";
        homeKicker.textContent = "Setup";
        homeTitle.textContent = "Add focus websites";
        homeDetail.textContent = "Choose a subject and save the websites you want available during focus.";
        homePrimaryButton.textContent = "Set Up Focus";
    } else {
        action = "start";
        homeKicker.textContent = "Ready";
        homeTitle.textContent = `Start ${preferredSubject}`;
        homeDetail.textContent = `${websites.length} allowed website${websites.length === 1 ? "" : "s"} ready. Todo overlay and timetable reminders will follow your current settings.`;
        homePrimaryButton.textContent = "Start Focus";
    }

    homePrimaryButton.dataset.action = action;
    homePrimaryButton.disabled = false;
    homeFocusSetupButton.disabled = !loggedIn;
    homeTodoButton.disabled = !loggedIn;
}

function renderTodoList(items = currentSettings.todoItems) {
    const safeItems = cleanTodoItems(items);
    const loggedIn = isLoggedIn(currentSettings);
    currentSettings.todoItems = safeItems;

    if (!todoList) {
        return;
    }

    todoList.replaceChildren();

    if (safeItems.length === 0) {
        const empty = document.createElement("div");
        empty.className = "todo-empty";
        empty.textContent = "No tasks yet. Add what you want visible on the overlay.";
        todoList.append(empty);
        clearCompletedTodosButton.disabled = true;
        return;
    }

    safeItems.forEach((item) => {
        const row = document.createElement("div");
        const checkbox = document.createElement("input");
        const text = document.createElement("span");
        const removeButton = document.createElement("button");

        row.className = item.done ? "todo-item done" : "todo-item";
        row.dataset.todoId = item.id;

        checkbox.type = "checkbox";
        checkbox.checked = item.done;
        checkbox.disabled = !loggedIn;
        checkbox.title = "Mark task complete";

        text.className = "todo-text";
        text.textContent = item.text;

        removeButton.className = "todo-delete-button";
        removeButton.type = "button";
        removeButton.textContent = "X";
        removeButton.disabled = !loggedIn;
        removeButton.title = "Remove task";

        row.append(checkbox, text, removeButton);
        todoList.append(row);
    });

    clearCompletedTodosButton.disabled = !loggedIn || !safeItems.some((item) => item.done);
}

async function saveTodoItems(items, message = "Todo list saved.") {
    const safeItems = cleanTodoItems(items);

    const result = await sendRuntimeMessage({
        type: "saveTodoItems",
        todoItems: safeItems
    });

    if (!result?.ok) {
        statusText.textContent = result?.error || "Could not save todo list.";
        return false;
    }

    currentSettings.todoItems = safeItems;
    renderTodoList(safeItems);
    await refreshLocalStateFromBackground();
    statusText.textContent = result.message || message;
    return true;
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

    focusHistory.replaceChildren();

    recentHistory.forEach((session) => {
        const item = document.createElement("div");
        const subject = document.createElement("span");
        const topic = document.createElement("span");
        const score = document.createElement("strong");
        const focused = document.createElement("span");
        const topDistraction = document.createElement("span");
        const note = document.createElement("span");

        item.className = "history-item";
        subject.textContent = `Subject: ${session.subject || "unknown"}`;
        topic.textContent = `Topic: ${session.topic || "none"}`;
        score.textContent = `${session.score}%`;
        focused.textContent = `${formatSeconds(session.focusedSeconds)} focused`;
        topDistraction.textContent = `Top distraction: ${session.topDistractedDomain || "none"}`;
        note.textContent = session.reviewNote ? `Note: ${session.reviewNote}` : "";

        item.append(subject, topic, score, focused, topDistraction);
        if (session.reviewNote) {
            item.append(note);
        }
        focusHistory.append(item);
    });
}

function getSyncedSubjects(settings = currentSettings) {
    return Array.isArray(settings?.syncedSubjects) ? settings.syncedSubjects : [];
}

function hasSyncedSubjects(settings = currentSettings) {
    return getSyncedSubjects(settings).length > 0;
}

function renderSubjectOptions(subjects, selectedSubject = "") {
    const safeSubjects = Array.isArray(subjects) ? subjects : [];
    const cleanSelectedSubject = String(
        selectedSubject || currentSettings.selectedFocusSubject || currentSettings.focusSubject || ""
    ).trim().toLowerCase();
    focusSubject.replaceChildren();

    if (safeSubjects.length === 0) {
        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "No synced subjects";
        focusSubject.append(emptyOption);
        allowedDomains.value = "";
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

    focusSubject.value = safeSubjects.includes(cleanSelectedSubject)
        ? cleanSelectedSubject
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
    renderHomePanel(safeSummary);
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
    renderSyncOverview(currentSettings);
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
        const publicTabs = ["home", "account"];
        button.disabled = !publicTabs.includes(button.dataset.tab) && !loggedIn;
    });

    saveButton.disabled = !loggedIn || currentSettings.focusActive || !hasSyncedSubjects(settings);
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
    todoOverlayEnabled.disabled = !loggedIn;
    newTodoInput.disabled = !loggedIn;
    addTodoButton.disabled = !loggedIn;
    clearCompletedTodosButton.disabled =
        !loggedIn || !cleanTodoItems(currentSettings.todoItems).some((item) => item.done);

    const activePanel = document.querySelector(".tab-panel.active")?.dataset.panel || "home";

    if (!loggedIn && !["home", "account"].includes(activePanel)) {
        showPopupTab("account");
    }
}

async function requireLogin() {
    const state = await sendRuntimeMessage({
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

async function refreshLocalStateFromBackground() {
    const state = await sendRuntimeMessage({
        type: "getCompanionState"
    });

    currentSettings = {
        ...currentSettings,
        ...(state?.settings || {})
    };

    renderTodaySessions(currentSettings);
    renderSubjectOptions(
        currentSettings.syncedSubjects,
        currentSettings.selectedFocusSubject || currentSettings.focusSubject
    );
    renderFocusSummary(state?.summary || EMPTY_SUMMARY);
    renderCompletedSummary(currentSettings.lastCompletedFocusSession);
    renderFocusHistory(currentSettings.focusHistory);
    renderTodoList(currentSettings.todoItems);
    showPendingFocusReviewIfNeeded(currentSettings.lastCompletedFocusSession);
    renderAccount(currentSettings);
    return state;
}

async function retrySyncNow(showMessage = true) {
    if (!(await requireLogin())) {
        return;
    }

    retrySyncButton.disabled = true;
    syncStatusLabel.textContent = "Retrying sync...";

    const result = await sendRuntimeMessage({
        type: "retryOfflineUploads"
    });

    await refreshLocalStateFromBackground();

    if (showMessage) {
        statusText.textContent = result?.ok
            ? (result.message || "Everything is synced.")
            : (result?.message || "Some changes are still waiting to sync.");
    }
}

async function loadSettings() {
    try {
        const state = await sendRuntimeMessage({
            type: "getCompanionState"
        });

        if (!state?.settings || !state?.summary) {
            throw new Error("Background worker did not return companion state.");
        }

        remindersEnabled.checked = state.settings.remindersEnabled;
        strictFocusEnabled.checked = Boolean(state.settings.strictFocusEnabled);
        pomodoroEnabledInput.checked = Boolean(state.settings.pomodoroEnabled);
        todoOverlayEnabled.checked = state.settings.todoOverlayEnabled !== false;

        currentSettings = {
            ...currentSettings,
            ...state.settings
        };

        renderTodaySessions(currentSettings);
        renderSubjectOptions(
            currentSettings.syncedSubjects,
            currentSettings.selectedFocusSubject || currentSettings.focusSubject
        );
        renderFocusSummary(state.summary);
        renderCompletedSummary(state.settings.lastCompletedFocusSession);
        renderFocusHistory(state.settings.focusHistory);
        renderTodoList(state.settings.todoItems);
        showPendingFocusReviewIfNeeded(state.settings.lastCompletedFocusSession);
        renderAccount(currentSettings);

        if (
            isLoggedIn(currentSettings) &&
            (
                currentSettings.todoSyncPending ||
                (currentSettings.offlineUploadQueue || []).length > 0
            )
        ) {
            await retrySyncNow(false);
        }
    } catch (error) {
        console.error(error);
        renderFocusSummary(EMPTY_SUMMARY);
        renderAccount({});
        statusText.textContent = `Reload the extension. ${error?.message || "Background did not respond."}`;
    }
}

async function loginToServer() {
    const username = loginUsername.value.trim();
    const password = loginPassword.value;

    if (!username || !password) {
        statusText.textContent = "Enter username and password.";
        return;
    }

    const result = await sendRuntimeMessage({
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
    await refreshLocalStateFromBackground();
    statusText.textContent = currentSettings.syncedSubjects.length > 0
        ? "Logged in."
        : "Logged in. Sync subjects in the terminal app, then refresh.";
    showPopupTab("home");
}

async function logoutFromServer() {
    await sendRuntimeMessage({ type: "logoutFromServer"});
    loginPassword.value = "";
    currentSettings = {
        ...currentSettings,
        serverUsername: "",
        serverToken: "",
        focusActive: false,
        pomodoroEnabled: false,
        syncedSubjects: [],
        syncedSubjectWebsites: {},
        syncedSubjectTopics: {},
        syncedTimetable: [],
        focusSubject: "",
        selectedFocusSubject: "",
        lastCompletedFocusSession: null,
        focusHistory: [],
        todoItems: []
    };

    allowedDomains.value = "";
    renderTodaySessions(currentSettings);
    renderSubjectOptions([], "");
    renderFocusSummary(EMPTY_SUMMARY);
    renderCompletedSummary(null);
    renderFocusHistory([]);
    renderTodoList([]);
    hideFocusReviewPanel();
    renderAccount(currentSettings);
    statusText.textContent = "Logged out.";
    showPopupTab("account");
}

async function refreshSubjects() {
    if (!(await requireLogin())) {
        return;
    }

    const result = await sendRuntimeMessage({
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
        syncedSubjectTopics: result.subjectTopics || {},
        syncedTimetable: result.timetable || [],
        todoItems: result.todoItems || currentSettings.todoItems || [],
        selectedFocusSubject: result.selectedFocusSubject || ""
    };

    await refreshLocalStateFromBackground();
    renderTodaySessions(currentSettings);
    renderSubjectOptions(
        currentSettings.syncedSubjects,
        currentSettings.selectedFocusSubject || currentSettings.focusSubject
    );
    setAccountGate(currentSettings);
    renderTodoList(currentSettings.todoItems);
    const timetableCount = Array.isArray(result.timetable) ? result.timetable.length : 0;
    const todoCount = cleanTodoItems(currentSettings.todoItems).length;
    const topicSetCount = Object.keys(currentSettings.syncedSubjectTopics || {}).length;
    statusText.textContent = currentSettings.syncedSubjects.length > 0
        ? `Subjects refreshed. ${topicSetCount} topic set(s), ${timetableCount} timetable reminder(s), ${todoCount} todo task(s) synced.`
        : "No synced subjects yet.";
}

async function saveSettings(showMessage = true) {
    if (!(await requireLogin())) {
        return;
    }

    await sendRuntimeMessage({
        type: "saveSettings",
        settings: {
            remindersEnabled: remindersEnabled.checked,
            strictFocusEnabled: strictFocusEnabled.checked,
            pomodoroEnabled: pomodoroEnabledInput.checked,
            todoOverlayEnabled: todoOverlayEnabled.checked
        }
    });

    currentSettings = {
        ...currentSettings,
        remindersEnabled: remindersEnabled.checked,
        strictFocusEnabled: strictFocusEnabled.checked,
        pomodoroEnabled: pomodoroEnabledInput.checked,
        todoOverlayEnabled: todoOverlayEnabled.checked
    };
    renderHomePanel();

    if (showMessage) {
        statusText.textContent = "Saved.";
    }
}

async function saveReminderToggle() {
    if (!(await requireLogin())) {
        return;
    }

    await sendRuntimeMessage({
        type: "saveSettings",
        settings: {
            remindersEnabled: remindersEnabled.checked,
            strictFocusEnabled: strictFocusEnabled.checked,
            pomodoroEnabled: pomodoroEnabledInput.checked
        }
    });

    currentSettings.remindersEnabled = remindersEnabled.checked;
    renderHomePanel();

    statusText.textContent = remindersEnabled.checked
        ? "Timetable notifications enabled."
        : "Timetable notifications disabled.";
}

async function saveTodoOverlayToggle() {
    const result = await sendRuntimeMessage({
        type: "setTodoOverlayEnabled",
        enabled: todoOverlayEnabled.checked
    });

    if (!result?.ok) {
        statusText.textContent = result?.error || "Could not update todo overlay.";
        return;
    }

    currentSettings.todoOverlayEnabled = todoOverlayEnabled.checked;
    renderHomePanel();
    statusText.textContent = todoOverlayEnabled.checked
        ? "Todo overlay enabled."
        : "Todo overlay hidden.";
}

async function rememberSelectedSubject(subject) {
    const cleanSubject = String(subject || "").trim().toLowerCase();
    currentSettings.selectedFocusSubject = cleanSubject;

    await sendRuntimeMessage({
        type: "saveSettings",
        settings: {
            selectedFocusSubject: cleanSubject
        }
    });
}

async function saveFocusWebsites(showMessage = true) {
    if (!(await requireLogin())) {
        return false;
    }

    const subject = focusSubject.value.trim().toLowerCase();

    if (!subject) {
        statusText.textContent = "Choose a synced subject first.";
        return false;
    }

    const websites = parseDomains(allowedDomains.value);

    const result = await sendRuntimeMessage({
        type: "saveSubjectWebsites",
        subject,
        websites
    });

    if (!result?.ok) {
        statusText.textContent = result?.error || "Could not save focus websites.";
        return false;
    }

    currentSettings = {
        ...currentSettings,
        syncedSubjectWebsites: result.subjectWebsites || {},
        selectedFocusSubject: result.selectedFocusSubject || subject
    };

    renderSubjectOptions(currentSettings.syncedSubjects, currentSettings.selectedFocusSubject);
    renderHomePanel();

    if (showMessage) {
        const count = Array.isArray(result.websites) ? result.websites.length : 0;
        statusText.textContent = `Saved ${count} website(s) for ${subject}.`;
    }

    return true;
}

async function testNotification() {
    if (!(await requireLogin())) {
        return;
    }

    await sendRuntimeMessage({
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

    if (parseDomains(allowedDomains.value).length === 0) {
        statusText.textContent = "Add at least one focus website for this subject.";
        return;
    }

    if (!(await saveFocusWebsites(false))) {
        return;
    }

    await saveSettings(false);
    const summary = await sendRuntimeMessage({
        type: "startFocus",
        subject,
        pomodoroEnabled: pomodoroEnabledInput.checked
    });

    renderFocusSummary(summary);
    hideFocusReviewPanel();
    statusText.textContent = pomodoroEnabledInput.checked
        ? "Pomodoro started. Work blocks upload every 50 minutes."
        : "Focus started.";
}

async function stopFocus() {
    if (!(await requireLogin())) {
        return;
    }

    const summary = await sendRuntimeMessage({
        type: "stopFocus"
    });

    renderFocusSummary(summary);
    const state = await sendRuntimeMessage({
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

    if (summary.offlineQueued) {
        statusText.textContent = "Focus stopped. Saved offline and will upload automatically when sync works.";
        showFocusReviewPanel(summary);
        await refreshLocalStateFromBackground();
        return;
    }

    const leaderboardStatus = summary.serverUpload?.ok
        ? `Leaderboard uploaded ${summary.serverUpload.minutes} min`
        : `Leaderboard failed: ${summary.serverUpload?.error || "Unknown error."}`;

    const qualityStatus = summary.qualityUpload?.ok
        ? "Quality synced"
        : `Quality failed: ${summary.qualityUpload?.error || "Unknown error."}`;

    statusText.textContent = `Focus stopped. ${leaderboardStatus}. ${qualityStatus}.`;
    showFocusReviewPanel(summary);
}

async function saveFocusReview() {
    if (!(await requireLogin())) {
        return;
    }

    const completedAt = focusReviewPanel?.dataset.completedAt || "";

    if (!completedAt) {
        statusText.textContent = "Stop a focus session first.";
        return;
    }

    const result = await sendRuntimeMessage({
        type: "saveFocusReview",
        completedAt,
        topic: focusReviewTopic.value,
        reviewNote: focusReviewNote.value
    });

    if (result?.summary) {
        latestCompletedFocusSession = result.summary;
        renderCompletedSummary(result.summary);
        const state = await sendRuntimeMessage({
            type: "getCompanionState"
        });
        renderFocusHistory(state.settings.focusHistory);
    }

    hideFocusReviewPanel();

    if (!result?.ok) {
        statusText.textContent = result?.error || "Review saved locally, but sync failed.";
        return;
    }

    statusText.textContent = "Review synced.";
}

async function skipFocusReview() {
    const completedAt = focusReviewPanel?.dataset.completedAt || "";

    if (completedAt) {
        await sendRuntimeMessage({
            type: "skipFocusReview",
            completedAt
        });
    }

    hideFocusReviewPanel();
    statusText.textContent = "Review skipped.";
}

async function refreshFocusStatus() {
    const summary = await sendRuntimeMessage({
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

    await sendRuntimeMessage({
        type: "clearFocusHistory"
    });

    renderCompletedSummary(null);
    renderFocusHistory([]);
    statusText.textContent = "Focus history cleared.";
}

async function addTodoItem() {
    const text = newTodoInput.value.trim();

    if (!text) {
        statusText.textContent = "Type a task first.";
        return;
    }

    const nextItems = [
        ...cleanTodoItems(currentSettings.todoItems),
        {
            id: createTodoId(),
            text,
            done: false
        }
    ];

    if (await saveTodoItems(nextItems, "Task added to overlay.")) {
        newTodoInput.value = "";
        newTodoInput.focus();
    }
}

async function updateTodoItem(todoId, changes) {
    const nextItems = cleanTodoItems(currentSettings.todoItems).map((item) => {
        if (item.id !== todoId) {
            return item;
        }

        return {
            ...item,
            ...changes
        };
    });

    await saveTodoItems(nextItems, "Todo list updated.");
}

async function removeTodoItem(todoId) {
    const nextItems = cleanTodoItems(currentSettings.todoItems)
        .filter((item) => item.id !== todoId);

    await saveTodoItems(nextItems, "Task removed.");
}

async function clearCompletedTodos() {
    const nextItems = cleanTodoItems(currentSettings.todoItems)
        .filter((item) => !item.done);

    await saveTodoItems(nextItems, "Completed tasks cleared.");
}

async function handleHomePrimaryAction() {
    const action = homePrimaryButton.dataset.action || "start";

    if (action === "account") {
        showPopupTab("account");
        loginUsername.focus();
        return;
    }

    if (action === "refresh") {
        await refreshSubjects();
        return;
    }

    if (action === "setup") {
        showPopupTab("focus");
        focusSubject.focus();
        return;
    }

    if (action === "stop") {
        await stopFocus();
        return;
    }

    const subject = getPreferredSubject(currentSettings);

    if (!subject) {
        showPopupTab("focus");
        statusText.textContent = "Choose a subject first.";
        return;
    }

    focusSubject.value = subject;
    renderFocusWebsitesForSubject(subject);
    await rememberSelectedSubject(subject);
    await startFocus();
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        showPopupTab(button.dataset.tab);
    });
});

remindersEnabled.addEventListener("change", saveReminderToggle);
todoOverlayEnabled.addEventListener("change", saveTodoOverlayToggle);
focusSubject.addEventListener("change", async () => {
    renderFocusWebsitesForSubject(focusSubject.value);
    await rememberSelectedSubject(focusSubject.value);
    renderHomePanel();
});
strictFocusEnabled.addEventListener("change", saveSettings);
pomodoroEnabledInput.addEventListener("change", saveSettings);
saveButton.addEventListener("click", saveFocusWebsites);
testButton.addEventListener("click", testNotification);
refreshSubjectsButton.addEventListener("click", refreshSubjects);
startFocusButton.addEventListener("click", startFocus);
stopFocusButton.addEventListener("click", stopFocus);
saveFocusReviewButton.addEventListener("click", saveFocusReview);
skipFocusReviewButton.addEventListener("click", skipFocusReview);
copySummaryButton.addEventListener("click", copySummary);
copyJsonButton.addEventListener("click", copySummaryJson);
clearHistoryButton.addEventListener("click", clearFocusHistory);
addTodoButton.addEventListener("click", addTodoItem);
clearCompletedTodosButton.addEventListener("click", clearCompletedTodos);
homePrimaryButton.addEventListener("click", handleHomePrimaryAction);
homeFocusSetupButton.addEventListener("click", () => showPopupTab("focus"));
homeTodoButton.addEventListener("click", () => showPopupTab("todo"));
newTodoInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        event.preventDefault();
        addTodoItem();
    }
});
todoList.addEventListener("change", (event) => {
    if (event.target?.matches('input[type="checkbox"]')) {
        const todoId = event.target.closest(".todo-item")?.dataset.todoId;

        if (todoId) {
            updateTodoItem(todoId, { done: event.target.checked });
        }
    }
});
todoList.addEventListener("click", (event) => {
    if (event.target?.matches(".todo-delete-button")) {
        const todoId = event.target.closest(".todo-item")?.dataset.todoId;

        if (todoId) {
            removeTodoItem(todoId);
        }
    }
});
loginButton.addEventListener("click", loginToServer);
logoutButton.addEventListener("click", logoutFromServer);
retrySyncButton.addEventListener("click", () => retrySyncNow(true));

setInterval(refreshFocusStatus, 2000);

loadSettings();
