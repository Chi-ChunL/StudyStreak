const DAILY_REMINDER_ALARM = "studystreak-daily-reminder";
const API_BASE_URL = "https://chichi.hackclub.app";
const FOCUS_TICK_ALARM = "studystreak-focus-tick";
const TIMETABLE_ALARM_PREFIX = "studystreak-timetable-";
const POMODORO_WORK_SECONDS = 50 * 60;
const POMODORO_BREAK_SECONDS = 10 * 60;
const IDLE_DETECTION_SECONDS = 8 * 60;
const STRICT_FOCUS_REDIRECT_COOLDOWN_MS = 4000;


const DEFAULT_STATS = {
    focusedSeconds: 0,
    distractedSeconds: 0,
    idleSeconds: 0,
    lastDomain: "none",
    lastCategory: "idle",
    distractedDomains: {}
};

const DEFAULT_SYNC_STATUS = {
    state: "idle",
    message: "Not synced yet.",
    at: null
};

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

function cleanUploadSummary(summary) {
    if (!summary || typeof summary !== "object") {
        return null;
    }

    const completedAt = String(summary.completedAt || "").trim();
    const subject = String(summary.subject || "").trim().toLowerCase();

    if (!completedAt || !subject || subject === "unknown") {
        return null;
    }

    const todoSnapshot = cleanTodoItems(summary.todoSnapshot || []);

    return {
        ...summary,
        completedAt,
        subject,
        score: Math.max(0, Math.min(100, Number(summary.score) || 0)),
        focusedSeconds: Math.max(0, Number(summary.focusedSeconds) || 0),
        distractedSeconds: Math.max(0, Number(summary.distractedSeconds) || 0),
        idleSeconds: Math.max(0, Number(summary.idleSeconds) || 0),
        topDistractedDomain: String(summary.topDistractedDomain || "none"),
        topic: String(summary.topic || "").trim() || undefined,
        reviewNote: String(summary.reviewNote || "").trim() || undefined,
        todoSnapshot,
        completedTodos: todoSnapshot.filter((item) => item.done)
    };
}

function cleanOfflineUploadQueue(queue) {
    if (!Array.isArray(queue)) {
        return [];
    }

    const byCompletedAt = new Map();

    queue.forEach((summary) => {
        const cleanSummary = cleanUploadSummary(summary);

        if (cleanSummary) {
            byCompletedAt.set(cleanSummary.completedAt, cleanSummary);
        }
    });

    return [...byCompletedAt.values()].slice(-20);
}

function cleanSyncStatus(status) {
    if (!status || typeof status !== "object") {
        return DEFAULT_SYNC_STATUS;
    }

    return {
        state: ["idle", "synced", "pending", "failed"].includes(status.state)
            ? status.state
            : "idle",
        message: String(status.message || DEFAULT_SYNC_STATUS.message).slice(0, 180),
        at: status.at ? String(status.at) : null
    };
}

function friendlyNetworkError(error, fallback = "Network error.") {
    const message = String(error?.message || "");

    if (/Failed to fetch|NetworkError|Load failed/i.test(message)) {
        return `${fallback} Check your internet, server deployment, and extension CORS permissions.`;
    }

    return message || fallback;
}

const DEFAULT_SETTINGS = {
    remindersEnabled: true,
    allowedDomains: ["pearsonactivelearn.com", "quizlet.com", "senecalearning.com"],
    focusActive: false,
    focusStartedAt: null,
    focusLastCheckedAt: null,
    focusStats: DEFAULT_STATS,
    lastCompletedFocusSession: null,
    focusHistory: [],
    focusSubject: "",
    selectedFocusSubject: "",
    syncedSubjects: [],
    syncedSubjectWebsites: {},
    syncedSubjectTopics: {},
    syncedTimetable: [],
    serverUsername: "",
    serverToken: "",
    strictFocusEnabled: false,
    pomodoroEnabled: false,
    pomodoroPhase: "work",
    pomodoroPhaseStartedAt: null,
    pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
    pomodoroWorkBlocksCompleted: 0,
    todoOverlayEnabled: true,
    todoItems: [],
    completedTodoItems: [],
    todoSyncPending: false,
    offlineUploadQueue: [],
    lastSyncStatus: DEFAULT_SYNC_STATUS,
    focusOverlayPosition: null,
    todoOverlayPosition: null,
};

const ICON_URL = chrome.runtime.getURL("icon128.png");
let pomodoroTransitionRunning = false;
const strictFocusRedirects = new Map();

async function getSettings() {
    const saved = await chrome.storage.local.get(DEFAULT_SETTINGS);

    return {
        ...DEFAULT_SETTINGS,
        ...saved,
        allowedDomains: Array.isArray(saved.allowedDomains)
            ? saved.allowedDomains
            : DEFAULT_SETTINGS.allowedDomains,
        focusStats: {
            ...DEFAULT_STATS,
            ...(saved.focusStats || {}),
            distractedDomains: {
                ...DEFAULT_STATS.distractedDomains,
                ...((saved.focusStats || {}).distractedDomains || {})
            }
        },
        focusHistory: Array.isArray(saved.focusHistory)
            ? saved.focusHistory
            : [],
        syncedSubjects: Array.isArray(saved.syncedSubjects)
            ? saved.syncedSubjects
            : [],
        syncedSubjectWebsites: (
            saved.syncedSubjectWebsites &&
            typeof saved.syncedSubjectWebsites === "object" &&
            !Array.isArray(saved.syncedSubjectWebsites)
        )
            ? saved.syncedSubjectWebsites
            : {},
        syncedSubjectTopics: cleanSubjectTopicMap(saved.syncedSubjectTopics),
        syncedTimetable: Array.isArray(saved.syncedTimetable)
            ? saved.syncedTimetable
            : [],
        serverUsername: typeof saved.serverUsername === "string" ? saved.serverUsername : "",
        serverToken: typeof saved.serverToken ==="string" ? saved.serverToken: "",
        focusSubject: typeof saved.focusSubject === "string" ? saved.focusSubject: "",
        selectedFocusSubject: typeof saved.selectedFocusSubject === "string" ? saved.selectedFocusSubject : "",
        strictFocusEnabled: Boolean(saved.strictFocusEnabled),
        pomodoroEnabled: Boolean(saved.pomodoroEnabled),
        pomodoroPhase: saved.pomodoroPhase === "break" ? "break" : "work",
        pomodoroPhaseStartedAt: Number(saved.pomodoroPhaseStartedAt) || null,
        pomodoroPhaseDurationSeconds: Number(saved.pomodoroPhaseDurationSeconds) || POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: Number(saved.pomodoroWorkBlocksCompleted) || 0,
        todoOverlayEnabled: saved.todoOverlayEnabled !== false,
        todoItems: cleanTodoItems(saved.todoItems),
        completedTodoItems: cleanTodoItems(saved.completedTodoItems),
        todoSyncPending: Boolean(saved.todoSyncPending),
        offlineUploadQueue: cleanOfflineUploadQueue(saved.offlineUploadQueue),
        lastSyncStatus: cleanSyncStatus(saved.lastSyncStatus),
        focusOverlayPosition: (
            saved.focusOverlayPosition &&
            Number.isFinite(Number(saved.focusOverlayPosition.left)) &&
            Number.isFinite(Number(saved.focusOverlayPosition.top))
        )
            ? {
                left: Number(saved.focusOverlayPosition.left),
                top: Number(saved.focusOverlayPosition.top)
            }
            : null,
        todoOverlayPosition: (
            saved.todoOverlayPosition &&
            Number.isFinite(Number(saved.todoOverlayPosition.left)) &&
            Number.isFinite(Number(saved.todoOverlayPosition.top))
        )
            ? {
                left: Number(saved.todoOverlayPosition.left),
                top: Number(saved.todoOverlayPosition.top)
            }
            : null,
    };
}

function getServerErrorMessage(data) {
    const detail = data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail.map((item) => item?.msg || String(item)).join("; ");
    }

    return "Server login failed.";

}

function cleanSubjectList(subjects) {
    if (!Array.isArray(subjects)) {
        return [];
    }

    return subjects
        .map((subject) => String(subject).trim().toLowerCase())
        .filter(Boolean);
}

function cleanSubjectWebsiteMap(subjectWebsites) {
    const cleaned = {};

    if (!subjectWebsites || typeof subjectWebsites !== "object" || Array.isArray(subjectWebsites)) {
        return cleaned;
    }

    Object.entries(subjectWebsites).forEach(([subject, websites]) => {
        const cleanSubject = String(subject || "").trim().toLowerCase();
        const websiteList = Array.isArray(websites) ? websites : [websites];

        if (!cleanSubject) {
            return;
        }

        cleaned[cleanSubject] = websiteList
            .map((website) => cleanDomain(String(website || "")))
            .filter(Boolean)
            .filter((website, index, list) => list.indexOf(website) === index)
            .slice(0, 10);
    });

    return cleaned;
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

function cleanTimetableList(timetable) {
    const validDays = new Set(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]);

    if (!Array.isArray(timetable)) {
        return [];
    }

    return timetable
        .map((item) => {
            return {
                subject: String(item?.subject || "").trim().toLowerCase(),
                day: String(item?.day || "").trim(),
                start_time: String(item?.start_time || "").trim(),
                minutes: Number(item?.minutes) || 0
            };
        })
        .filter((item) => {
            return (
                item.subject &&
                validDays.has(item.day) &&
                /^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(item.start_time) &&
                item.minutes > 0
            );
        })
        .slice(0, 100);
}

async function fetchSubjectsFromServer(token) {
    const response = await fetch(`${API_BASE_URL}/subjects`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return cleanSubjectList(data.subjects);
}

async function fetchSubjectWebsitesFromServer(token) {
    const response = await fetch(`${API_BASE_URL}/subject-websites`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return cleanSubjectWebsiteMap(data.subject_websites);
}

async function fetchSubjectTopicsFromServer(token) {
    const response = await fetch(`${API_BASE_URL}/subject-topics`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return cleanSubjectTopicMap(data.subject_topics);
}

async function fetchTodoItemsFromServer(token) {
    const response = await fetch(`${API_BASE_URL}/todo-items`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return cleanTodoItems(data.todo_items);
}

async function uploadSubjectWebsitesToServer(token, subjectWebsites) {
    const response = await fetch(`${API_BASE_URL}/subject-websites`, {
        method: "PUT",
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            subject_websites: cleanSubjectWebsiteMap(subjectWebsites)
        })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return data;
}

async function uploadTodoItemsToServer(token, todoItems) {
    const response = await fetch(`${API_BASE_URL}/todo-items`, {
        method: "PUT",
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            todo_items: cleanTodoItems(todoItems)
        })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return data;
}

async function fetchTimetableFromServer(token) {
    const response = await fetch(`${API_BASE_URL}/timetable`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return cleanTimetableList(data.timetable);
}

function getSelectedSubjectForList(subjects, selectedSubject) {
    const cleanSelectedSubject = String(selectedSubject || "").trim().toLowerCase();

    return Array.isArray(subjects) && subjects.includes(cleanSelectedSubject)
        ? cleanSelectedSubject
        : "";
}

async function refreshSubjectsFromServer() {
    const settings = await getSettings();

    if (!settings.serverToken) {
        return {
            ok: false,
            error: "Log in first.",
            subjects: []
        };
    }

    const subjects = await fetchSubjectsFromServer(settings.serverToken);
    const subjectWebsites = await fetchSubjectWebsitesFromServer(settings.serverToken);
    const subjectTopics = await fetchSubjectTopicsFromServer(settings.serverToken);
    const timetable = await fetchTimetableFromServer(settings.serverToken);
    const todoItems = await fetchTodoItemsFromServer(settings.serverToken);
    const selectedFocusSubject = getSelectedSubjectForList(
        subjects,
        settings.selectedFocusSubject || settings.focusSubject
    );

    await chrome.storage.local.set({
        syncedSubjects: subjects,
        syncedSubjectWebsites: subjectWebsites,
        syncedSubjectTopics: subjectTopics,
        syncedTimetable: timetable,
        todoItems,
        selectedFocusSubject
    });
    await scheduleTimetableReminders(timetable);
    await injectFocusOverlayIntoOpenTabs();
    const syncResult = await retryOfflineUploads();

    return {
        ok: true,
        subjects,
        subjectWebsites,
        subjectTopics,
        timetable,
        todoItems,
        selectedFocusSubject,
        syncResult
    };
}

async function saveSubjectWebsitesForSubject(subject, websites) {
    const settings = await getSettings();

    if (!settings.serverToken) {
        return { ok: false, error: "Log in first." };
    }

    const cleanSubject = String(subject || "").trim().toLowerCase();
    const subjects = cleanSubjectList(settings.syncedSubjects);

    if (!cleanSubject) {
        return { ok: false, error: "Choose a synced subject first." };
    }

    if (!subjects.includes(cleanSubject)) {
        return { ok: false, error: "That subject is not synced to this account." };
    }

    const cleanedEntry = cleanSubjectWebsiteMap({
        [cleanSubject]: Array.isArray(websites) ? websites : []
    });
    const cleanedWebsites = cleanedEntry[cleanSubject] || [];
    let latestSubjectWebsites = settings.syncedSubjectWebsites || {};

    try {
        latestSubjectWebsites = await fetchSubjectWebsitesFromServer(settings.serverToken);
    } catch {
        latestSubjectWebsites = settings.syncedSubjectWebsites || {};
    }

    const subjectWebsites = cleanSubjectWebsiteMap({
        ...latestSubjectWebsites,
        [cleanSubject]: cleanedWebsites
    });

    await uploadSubjectWebsitesToServer(settings.serverToken, subjectWebsites);

    await chrome.storage.local.set({
        syncedSubjectWebsites: subjectWebsites,
        selectedFocusSubject: cleanSubject
    });
    await setSyncStatus("synced", `Saved ${cleanedWebsites.length} focus website(s) for ${cleanSubject}.`);

    return {
        ok: true,
        subject: cleanSubject,
        websites: cleanedWebsites,
        subjectWebsites,
        selectedFocusSubject: cleanSubject
    };
}

function getLeaderboardMinutes(summary) {
    const focusedSeconds = Number(summary.focusedSeconds) || 0;

    if (focusedSeconds <= 0) {
        return 0;
    }

    return Math.max(1, Math.round(focusedSeconds / 60));
}

async function uploadCompletedFocusSession(summary, token) {
    const minutes = getLeaderboardMinutes(summary);

    if (!token) {
        return { ok: false, error: "Log in first."};
    }

    if (!summary.subject || summary.subject === "unknown") {
        return { ok: false, error: "Missing subject."};
    }

    if (minutes <= 0) {
        return { ok: false, error: "No focused time to upload."};
    }

    const response = await fetch(`${API_BASE_URL}/focus-sessions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            subject: summary.subject,
            minutes,
            website: null,
            topic: summary.topic || null,
            review_note: summary.reviewNote || null,
            completed_at: summary.completedAt || null,
            completed: true,
            source: "chrome_extension"
        })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return { ok: true, minutes };

}

async function uploadFocusQualitySession(summary, token) {
    if (!token) {
        return { ok: false, error: "Log in first."};
    }

    if (!summary.subject || summary.subject === "unknown") {
        return { ok: false, error: "Missing subject."};
    }

    if (!summary.completedAt) {
        return { ok: false, error: "Missing completion time." };
    }

    const response = await fetch(`${API_BASE_URL}/focus-quality-sessions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            source: "chrome_extension",
            subject: summary.subject,
            score: summary.score,
            focused_seconds: summary.focusedSeconds,
            distracted_seconds: summary.distractedSeconds,
            idle_seconds: summary.idleSeconds,
            top_distracted_domain: summary.topDistractedDomain || "none",
            completed_at: summary.completedAt
        })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    return { ok: true };
}

async function setSyncStatus(state, message) {
    const lastSyncStatus = {
        state,
        message,
        at: new Date().toISOString()
    };

    await chrome.storage.local.set({ lastSyncStatus });
    return lastSyncStatus;
}

async function storeQueuedSummary(summary) {
    const settings = await getSettings();
    const cleanSummary = cleanUploadSummary({
        ...summary,
        offlineQueued: true
    });

    if (!cleanSummary) {
        return settings.offlineUploadQueue;
    }

    const queue = cleanOfflineUploadQueue([
        ...settings.offlineUploadQueue.filter((item) => item.completedAt !== cleanSummary.completedAt),
        cleanSummary
    ]);

    await chrome.storage.local.set({
        offlineUploadQueue: queue
    });
    await setSyncStatus("pending", `${queue.length} focus session(s) waiting to upload.`);

    return queue;
}

function mergeUploadedSummaryIntoHistory(settings, completedAt, serverUpload, qualityUpload) {
    const updateSession = (session) => {
        if (session?.completedAt !== completedAt) {
            return session;
        }

        return {
            ...session,
            offlineQueued: false,
            serverUpload,
            qualityUpload
        };
    };

    return {
        lastCompletedFocusSession: updateSession(settings.lastCompletedFocusSession),
        focusHistory: (settings.focusHistory || []).map(updateSession)
    };
}

async function retryOfflineUploads() {
    const settings = await getSettings();
    let queue = cleanOfflineUploadQueue(settings.offlineUploadQueue);
    let todoSynced = !settings.todoSyncPending;

    if (!settings.serverToken) {
        if (queue.length > 0 || settings.todoSyncPending) {
            await setSyncStatus("pending", "Log in to upload saved extension changes.");
        }

        return {
            ok: false,
            queue,
            todoSynced,
            message: "Log in first."
        };
    }

    if (settings.todoSyncPending) {
        try {
            await uploadTodoItemsToServer(settings.serverToken, settings.todoItems);
            todoSynced = true;
            await chrome.storage.local.set({ todoSyncPending: false });
        } catch (error) {
            await setSyncStatus("pending", friendlyNetworkError(error, "Todo sync saved for retry."));
            return {
                ok: false,
                queue,
                todoSynced: false,
                message: friendlyNetworkError(error, "Todo sync saved for retry.")
            };
        }
    }

    if (queue.length === 0) {
        await setSyncStatus("synced", todoSynced ? "Everything is synced." : "Focus sessions synced.");
        return {
            ok: true,
            queue: [],
            todoSynced,
            message: "Everything is synced."
        };
    }

    const remaining = [];
    let uploadedCount = 0;

    for (const summary of queue) {
        try {
            const serverUpload = await uploadCompletedFocusSession(summary, settings.serverToken);
            const qualityUpload = await uploadFocusQualitySession(summary, settings.serverToken);
            const latestSettings = await getSettings();
            const merged = mergeUploadedSummaryIntoHistory(
                latestSettings,
                summary.completedAt,
                serverUpload,
                qualityUpload
            );

            await chrome.storage.local.set(merged);
            uploadedCount += 1;
        } catch (error) {
            remaining.push({
                ...summary,
                serverUpload: summary.serverUpload?.ok
                    ? summary.serverUpload
                    : { ok: false, error: friendlyNetworkError(error, "Upload queued for retry.") },
                qualityUpload: summary.qualityUpload?.ok
                    ? summary.qualityUpload
                    : { ok: false, error: friendlyNetworkError(error, "Quality sync queued for retry.") }
            });
        }
    }

    await chrome.storage.local.set({
        offlineUploadQueue: remaining
    });

    if (remaining.length > 0) {
        await setSyncStatus(
            "pending",
            `${uploadedCount} uploaded. ${remaining.length} still waiting for retry.`
        );
        return {
            ok: false,
            queue: remaining,
            todoSynced,
            message: `${remaining.length} session(s) still queued.`
        };
    }

    await setSyncStatus("synced", `Uploaded ${uploadedCount} queued session(s).`);
    return {
        ok: true,
        queue: [],
        todoSynced,
        message: `Uploaded ${uploadedCount} queued session(s).`
    };
}

async function saveTodoItemsWithSync(todoItems, settings) {
    let todoSyncPending = !settings.serverToken;
    let syncMessage = todoSyncPending
        ? "Todo list saved locally. Log in to sync."
        : "Todo list saved.";

    await chrome.storage.local.set({
        todoItems,
        todoSyncPending
    });

    if (settings.serverToken) {
        try {
            await uploadTodoItemsToServer(settings.serverToken, todoItems);
            todoSyncPending = false;
            syncMessage = "Todo list synced.";
            await chrome.storage.local.set({ todoSyncPending: false });
            await setSyncStatus("synced", syncMessage);
        } catch (error) {
            todoSyncPending = true;
            syncMessage = friendlyNetworkError(error, "Todo list saved locally for retry.");
            await chrome.storage.local.set({ todoSyncPending: true });
            await setSyncStatus("pending", syncMessage);
        }
    }

    await injectFocusOverlayIntoOpenTabs();

    return {
        ok: true,
        pending: todoSyncPending,
        message: syncMessage
    };
}

async function completeAllTodoItems() {
    const settings = await getSettings();
    const activeItems = cleanTodoItems(settings.todoItems);
    const completedItems = activeItems.map((item) => ({
        ...item,
        done: true
    }));

    if (completedItems.length === 0) {
        return {
            ok: true,
            completedCount: 0,
            message: "No todo tasks to complete."
        };
    }

    if (settings.focusActive) {
        await chrome.storage.local.set({
            completedTodoItems: cleanTodoItems([
                ...settings.completedTodoItems,
                ...completedItems
            ])
        });
    }

    const result = await saveTodoItemsWithSync([], settings);

    return {
        ...result,
        completedCount: completedItems.length,
        message: result.pending
            ? `${completedItems.length} task(s) completed locally. Todo sync will retry.`
            : `${completedItems.length} task(s) completed and cleared.`
    };
}

async function uploadAndStoreCompletedSummary(completedSummary, settings) {
    let serverUpload = { ok: false, error: "Not uploaded."};
    let qualityUpload = { ok: false, error: "Not synced"};
    const todoSnapshot = cleanTodoItems([
        ...settings.completedTodoItems,
        ...settings.todoItems
    ]);
    const completedSummaryWithTodos = {
        ...completedSummary,
        todoSnapshot,
        completedTodos: todoSnapshot.filter((item) => item.done)
    };

    try {
        serverUpload = await uploadCompletedFocusSession(
            completedSummaryWithTodos,
            settings.serverToken
        );
    } catch (error) {
        serverUpload = {
            ok: false,
            error: friendlyNetworkError(error, "Upload saved for retry.")
        };
    }

    try {
        qualityUpload = await uploadFocusQualitySession(
            completedSummaryWithTodos,
            settings.serverToken
        );
    } catch(error) {
        qualityUpload = {
            ok: false,
            error: friendlyNetworkError(error, "Quality sync saved for retry.")
        };
    }

    const completedSummaryWithUpload = {
        ...completedSummaryWithTodos,
        reviewPending: true,
        offlineQueued: !serverUpload.ok || !qualityUpload.ok,
        serverUpload,
        qualityUpload
    };

    const focusHistory = [
        completedSummaryWithUpload,
        ...(settings.focusHistory || [])
    ].slice(0, 3);

    await chrome.storage.local.set({
        lastCompletedFocusSession: completedSummaryWithUpload,
        focusHistory,
        completedTodoItems: []
    });

    if (completedSummaryWithUpload.offlineQueued) {
        await storeQueuedSummary(completedSummaryWithUpload);
    } else {
        await setSyncStatus(
            "synced",
            `Uploaded ${serverUpload.minutes} min and synced focus quality.`
        );
    }

    return completedSummaryWithUpload;
}

async function saveFocusReview(completedAt, topic, reviewNote) {
    const settings = await getSettings();
    const cleanCompletedAt = String(completedAt || "").trim();
    const cleanTopic = String(topic || "").trim().slice(0, 80);
    const cleanReviewNote = String(reviewNote || "").trim().slice(0, 1000);

    if (!cleanCompletedAt) {
        return { ok: false, error: "No completed focus session selected." };
    }

    const history = Array.isArray(settings.focusHistory) ? settings.focusHistory : [];
    const matchedSummary = (
        settings.lastCompletedFocusSession?.completedAt === cleanCompletedAt
            ? settings.lastCompletedFocusSession
            : history.find((session) => session.completedAt === cleanCompletedAt)
    );

    if (!matchedSummary) {
        return { ok: false, error: "Could not find that focus session." };
    }

    let updatedSummary = {
        ...matchedSummary,
        reviewPending: false,
        offlineQueued: false,
        topic: cleanTopic || undefined,
        reviewNote: cleanReviewNote || undefined
    };

    try {
        updatedSummary = {
            ...updatedSummary,
            serverUpload: await uploadCompletedFocusSession(updatedSummary, settings.serverToken)
        };
    } catch (error) {
        updatedSummary = {
            ...updatedSummary,
            offlineQueued: true,
            serverUpload: {
                ok: false,
                error: friendlyNetworkError(error, "Review saved locally for retry.")
            }
        };
    }

    const nextHistory = history.map((session) => {
        if (session.completedAt !== cleanCompletedAt) {
            return session;
        }

        return updatedSummary;
    });

    if (!nextHistory.some((session) => session.completedAt === cleanCompletedAt)) {
        nextHistory.unshift(updatedSummary);
    }

    await chrome.storage.local.set({
        lastCompletedFocusSession: (
            settings.lastCompletedFocusSession?.completedAt === cleanCompletedAt
                ? updatedSummary
                : settings.lastCompletedFocusSession
        ),
        focusHistory: nextHistory.slice(0, 3)
    });

    if (updatedSummary.offlineQueued) {
        await storeQueuedSummary(updatedSummary);
    } else {
        await setSyncStatus("synced", "Review synced.");
    }

    if (!updatedSummary.serverUpload?.ok) {
        return {
            ok: false,
            error: updatedSummary.serverUpload?.error || "Review saved locally, but sync failed.",
            summary: updatedSummary
        };
    }

    return {
        ok: true,
        summary: updatedSummary
    };
}

async function skipFocusReview(completedAt) {
    const settings = await getSettings();
    const cleanCompletedAt = String(completedAt || "").trim();

    if (!cleanCompletedAt) {
        return { ok: false, error: "No completed focus session selected." };
    }

    const history = Array.isArray(settings.focusHistory) ? settings.focusHistory : [];
    const lastCompletedFocusSession = (
        settings.lastCompletedFocusSession?.completedAt === cleanCompletedAt
            ? {
                ...settings.lastCompletedFocusSession,
                reviewPending: false
            }
            : settings.lastCompletedFocusSession
    );
    const focusHistory = history.map((session) => {
        if (session.completedAt !== cleanCompletedAt) {
            return session;
        }

        return {
            ...session,
            reviewPending: false
        };
    });

    await chrome.storage.local.set({
        lastCompletedFocusSession,
        focusHistory
    });

    return { ok: true };
}

async function loginToServer(username, password) {
    const cleanUsername = username.trim().toLowerCase();
    const previousSettings = await getSettings();
    const sameAccount = previousSettings.serverUsername === cleanUsername;

    const response = await fetch(`${API_BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: cleanUsername, password })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(getServerErrorMessage(data));
    }

    let subjects = [];
    let subjectWebsites = {};
    let subjectTopics = {};
    let timetable = [];
    let todoItems = [];

    try {
        subjects = await fetchSubjectsFromServer(data.access_token);
    } catch {
        subjects = [];
    }

    try {
        subjectWebsites = await fetchSubjectWebsitesFromServer(data.access_token);
    } catch {
        subjectWebsites = {};
    }

    try {
        subjectTopics = await fetchSubjectTopicsFromServer(data.access_token);
    } catch {
        subjectTopics = {};
    }

    try {
        timetable = await fetchTimetableFromServer(data.access_token);
    } catch {
        timetable = [];
    }

    try {
        todoItems = await fetchTodoItemsFromServer(data.access_token);
    } catch {
        todoItems = [];
    }

    const selectedFocusSubject = sameAccount
        ? getSelectedSubjectForList(
            subjects,
            previousSettings.selectedFocusSubject || previousSettings.focusSubject
        )
        : "";
    const storedTodoItems = sameAccount
        ? cleanTodoItems(todoItems.length > 0 ? todoItems : previousSettings.todoItems)
        : cleanTodoItems(todoItems);

    if (sameAccount && todoItems.length === 0 && storedTodoItems.length > 0) {
        try {
            await uploadTodoItemsToServer(data.access_token, storedTodoItems);
        } catch {
            // Keep local todo items even if the first cloud upload cannot complete.
        }
    }

    if (!sameAccount) {
        await chrome.alarms.clear(FOCUS_TICK_ALARM);
        await clearTimetableReminders();
    }

    await chrome.storage.local.set({
        serverUsername: cleanUsername,
        serverToken: data.access_token,
        syncedSubjects: subjects,
        syncedSubjectWebsites: subjectWebsites,
        syncedSubjectTopics: subjectTopics,
        syncedTimetable: timetable,
        todoItems: storedTodoItems,
        selectedFocusSubject,
        focusActive: sameAccount ? previousSettings.focusActive : false,
        focusSubject: sameAccount && previousSettings.focusActive
            ? previousSettings.focusSubject
            : "",
        focusLastCheckedAt: sameAccount ? previousSettings.focusLastCheckedAt : null,
        focusStats: sameAccount ? previousSettings.focusStats : { ...DEFAULT_STATS },
        lastCompletedFocusSession: sameAccount
            ? previousSettings.lastCompletedFocusSession
            : null,
        focusHistory: sameAccount ? previousSettings.focusHistory : [],
        allowedDomains: sameAccount
            ? previousSettings.allowedDomains
            : DEFAULT_SETTINGS.allowedDomains,
        pomodoroEnabled: sameAccount ? previousSettings.pomodoroEnabled : false,
        pomodoroPhase: sameAccount ? previousSettings.pomodoroPhase : "work",
        pomodoroPhaseStartedAt: sameAccount ? previousSettings.pomodoroPhaseStartedAt : null,
        pomodoroPhaseDurationSeconds: sameAccount
            ? previousSettings.pomodoroPhaseDurationSeconds
            : POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: sameAccount
            ? previousSettings.pomodoroWorkBlocksCompleted
            : 0,
        completedTodoItems: sameAccount ? previousSettings.completedTodoItems : [],
        offlineUploadQueue: sameAccount ? previousSettings.offlineUploadQueue : [],
        todoSyncPending: sameAccount ? previousSettings.todoSyncPending : false,
        lastSyncStatus: sameAccount
            ? previousSettings.lastSyncStatus
            : {
                state: "synced",
                message: "Logged in. Ready to sync.",
                at: new Date().toISOString()
            },
        todoOverlayEnabled: previousSettings.todoOverlayEnabled,
        focusOverlayPosition: previousSettings.focusOverlayPosition,
        todoOverlayPosition: previousSettings.todoOverlayPosition
    });
    await scheduleTimetableReminders(timetable);
    await injectFocusOverlayIntoOpenTabs();
    const syncResult = sameAccount
        ? await retryOfflineUploads()
        : { ok: true, queue: [], todoSynced: true, message: "Logged in." };

    return {
        ok: true,
        serverUsername: cleanUsername,
        subjects,
        subjectWebsites,
        subjectTopics,
        timetable,
        todoItems: storedTodoItems,
        selectedFocusSubject,
        syncResult
    };
}

async function logoutFromServer() {
    await chrome.alarms.clear(FOCUS_TICK_ALARM);
    await clearTimetableReminders();

    await chrome.storage.local.set({
        serverUsername: "",
        serverToken: "",
        focusActive: false,
        focusLastCheckedAt: null,
        focusSubject: "",
        selectedFocusSubject: "",
        allowedDomains: DEFAULT_SETTINGS.allowedDomains,
        focusStats: { ...DEFAULT_STATS },
        lastCompletedFocusSession: null,
        focusHistory: [],
        pomodoroEnabled: false,
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: null,
        pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: 0,
        todoItems: [],
        completedTodoItems: [],
        todoSyncPending: false,
        offlineUploadQueue: [],
        lastSyncStatus: {
            state: "idle",
            message: "Logged out.",
            at: new Date().toISOString()
        },
        syncedSubjects: [],
        syncedSubjectWebsites: {},
        syncedSubjectTopics: {},
        syncedTimetable: []
    });

    return { ok: true };
}


function cleanDomain(value) {
    if (!value) {
        return "";
    }

    const rawValue = value.trim().toLowerCase();

    try {
        const urlValue = rawValue.includes("://") ? rawValue : `https://${rawValue}`;
        return new URL(urlValue).hostname.replace(/^www\./, "").split("/")[0];
    } catch {
        return "";
    }
}

function getDomainFromUrl(url) {
    try {
        return new URL(url).hostname.replace(/^www\./, "");
    } catch {
        return "";
    }
}

function isNewTabPageUrl(url) {
    if (!url) {
        return true;
    }

    return (
        url === "about:blank" ||
        url === "chrome://newtab/" ||
        url === "edge://newtab/" ||
        url === "brave://newtab/" ||
        url === "zen://newtab/"
    );
}

function canInjectOverlayIntoUrl(url) {
    return (
        typeof url === "string" &&
        (url.startsWith("http://") || url.startsWith("https://"))
    );
}

function executeLegacyOverlayScript(tabId) {
    return new Promise((resolve, reject) => {
        if (!chrome.tabs?.executeScript) {
            resolve(false);
            return;
        }

        let settled = false;
        const finish = (ok, error = null) => {
            if (settled) {
                return;
            }

            settled = true;
            if (ok) {
                resolve(true);
            } else {
                reject(error || new Error("Legacy overlay injection failed."));
            }
        };
        const timeoutId = setTimeout(() => finish(true), 1500);

        try {
            const result = chrome.tabs.executeScript(
                tabId,
                {
                    file: "/focus_overlay.js",
                    runAt: "document_idle"
                },
                () => {
                    clearTimeout(timeoutId);
                    const error = chrome.runtime.lastError;
                    finish(!error, error ? new Error(error.message) : null);
                }
            );

            if (result?.then) {
                result.then(
                    () => {
                        clearTimeout(timeoutId);
                        finish(true);
                    },
                    (error) => {
                        clearTimeout(timeoutId);
                        finish(false, error);
                    }
                );
            }
        } catch (error) {
            clearTimeout(timeoutId);
            finish(false, error);
        }
    });
}

async function injectFocusOverlayIntoTab(tabId, url = "") {
    if (!tabId) {
        return;
    }

    let targetUrl = url;

    if (!targetUrl) {
        try {
            const tab = await chrome.tabs.get(tabId);
            targetUrl = tab?.url || "";
        } catch {
            return;
        }
    }

    if (!canInjectOverlayIntoUrl(targetUrl)) {
        return;
    }

    try {
        await chrome.tabs.sendMessage(tabId, {
            type: "refreshStudyStreakOverlay"
        });
        return;
    } catch {
        // The page may not have the content script yet, especially during navigation.
    }

    if (!chrome.scripting?.executeScript) {
        try {
            await executeLegacyOverlayScript(tabId);
        } catch {
            // Some pages reject extension injection; content_scripts handles future page loads.
        }
        return;
    }

    try {
        await chrome.scripting.executeScript({
            target: { tabId },
            files: ["focus_overlay.js"]
        });
        return;
    } catch {
        // Firefox can be fussier about extension-root paths, so try one more form.
    }

    try {
        await chrome.scripting.executeScript({
            target: { tabId },
            files: ["/focus_overlay.js"]
        });
        return;
    } catch {
        // Fall through to the Firefox legacy API if it is available.
    }

    try {
        await executeLegacyOverlayScript(tabId);
    } catch {
        // Browser pages, PDFs, stores, and protected pages can reject injection.
    }
}

function scheduleOverlayInjection(tabId, delayMs = 0) {
    if (!tabId) {
        return;
    }

    setTimeout(() => {
        injectFocusOverlayIntoTab(tabId).catch(() => {});
    }, delayMs);
}

async function injectFocusOverlayIntoOpenTabs() {
    const tabs = await chrome.tabs.query({});

    await Promise.all(
        tabs
            .filter((tab) => tab.id && canInjectOverlayIntoUrl(tab.url || ""))
            .map(async (tab) => {
                await injectFocusOverlayIntoTab(tab.id, tab.url || "");
            })
    );
}

function isAllowedDomain(domain, allowedDomains) {
    const cleanCurrentDomain = cleanDomain(domain);

    return allowedDomains.some((allowedDomain) => {
        const cleanAllowedDomain = cleanDomain(allowedDomain);
        return (
            cleanCurrentDomain === cleanAllowedDomain || 
            cleanCurrentDomain.endsWith(`.${cleanAllowedDomain}`)
        );
    });
}

function getAllowedDomainsForFocus(settings) {
    const subject = String(settings.focusSubject || "").trim().toLowerCase();
    const subjectWebsites = settings.syncedSubjectWebsites || {};
    const subjectDomains = Array.isArray(subjectWebsites[subject])
        ? subjectWebsites[subject]
        : [];

    if (subject) {
        return subjectDomains;
    }

    return settings.allowedDomains;
}

function getStrictFocusRedirectUrl(allowedDomains) {
    const cleanAllowedDomains = allowedDomains
        .map((domain) => String(domain || "").trim())
        .filter(Boolean);

    if (cleanAllowedDomains.length === 0) {
        return "";
    }

    const redirectDomain = cleanAllowedDomains[
        Math.floor(Math.random() * cleanAllowedDomains.length)
    ];

    return redirectDomain.startsWith("http://") ||
        redirectDomain.startsWith("https://")
        ? redirectDomain
        : `https://${redirectDomain}`;
}

function getStrictFocusBlockedUrl(redirectUrl, subject) {
    const params = new URLSearchParams({
        redirect: redirectUrl,
        subject: String(subject || "your focus session")
    });

    return chrome.runtime.getURL(`strict_focus_blocked.html?${params.toString()}`);
}

function strictFocusRedirectIsPending(tabId) {
    const pendingRedirect = strictFocusRedirects.get(tabId);

    if (!pendingRedirect) {
        return false;
    }

    const now = Date.now();

    if (now - pendingRedirect.startedAt > STRICT_FOCUS_REDIRECT_COOLDOWN_MS) {
        strictFocusRedirects.delete(tabId);
        return false;
    }

    return true;
}

async function getActiveTabDomain() {
    const [tab] = await chrome.tabs.query({
        active: true,
        lastFocusedWindow: true
    });

    return getDomainFromUrl(tab?.url || "");
}

async function getCurrentFocusCategory(settings) {
    const idleState = await chrome.idle.queryState(IDLE_DETECTION_SECONDS);

    if (idleState !== "active") {
        return { category: "idle", domain: "idle" };
    }

    const domain = await getActiveTabDomain();

    if (!domain) {
        return { category: "distracted", domain: "browser page" };
    }

    if (isAllowedDomain(domain, getAllowedDomainsForFocus(settings))) {
        return { category: "focused", domain };
    }

    return { category: "distracted", domain };
}

function getTopDistractedDomain(stats) {
    const entries = Object.entries(stats.distractedDomains || {});

    if (entries.length === 0) {
        return "none";
    }

    return entries.sort((first, second) => second[1] - first[1])[0][0];
}

function getPomodoroSecondsLeft(settings) {
    if (!settings.pomodoroEnabled || !settings.pomodoroPhaseStartedAt) {
        return null;
    }

    const elapsedSeconds = Math.floor((Date.now() - settings.pomodoroPhaseStartedAt) / 1000);
    const durationSeconds = Number(settings.pomodoroPhaseDurationSeconds) || POMODORO_WORK_SECONDS;
    return Math.max(0, durationSeconds - elapsedSeconds);
}

function getFocusSummary(settings) {
    const stats = {
        ...DEFAULT_STATS,
        ...(settings.focusStats || {})
    };

    const totalSeconds = stats.focusedSeconds + stats.distractedSeconds + stats.idleSeconds;
    const score = totalSeconds > 0 ? Math.round((stats.focusedSeconds / totalSeconds) * 100): 0;
    const topDistractedDomain = getTopDistractedDomain(stats);

    return {
        focusActive: settings.focusActive,
        subject: settings.focusSubject || "unknown",
        pomodoroEnabled: Boolean(settings.pomodoroEnabled),
        pomodoroPhase: settings.pomodoroPhase || "work",
        pomodoroSecondsLeft: getPomodoroSecondsLeft(settings),
        pomodoroWorkBlocksCompleted: Number(settings.pomodoroWorkBlocksCompleted) || 0,
        score,
        totalSeconds,
        topDistractedDomain,
        ...stats
    };
} 

async function getFreshFocusStats(settings) {
    const current = await getCurrentFocusCategory(settings);

    return {
        ...DEFAULT_STATS,
        lastCategory: current.category,
        lastDomain: current.domain
    };
}

async function showPomodoroNotification(title, message) {
    await chrome.notifications.create({
        type: "basic",
        iconUrl: ICON_URL,
        title,
        message,
        priority: 1
    });
}

async function recordFocusElapsed() {
    const settings = await getSettings();

    if (!settings.focusActive) {
        return getFocusSummary(settings);
    }

    const now = Date.now();

    if (settings.pomodoroEnabled && settings.pomodoroPhase === "break") {
        await chrome.storage.local.set({
            focusLastCheckedAt: now
        });

        return getFocusSummary({
            ...settings,
            focusLastCheckedAt: now
        });
    }

    const stats = {
        ...DEFAULT_STATS,
        ...settings.focusStats
    };

    const elapsedSeconds = settings.focusLastCheckedAt ? Math.max(0, Math.min(300, Math.floor((now - settings.focusLastCheckedAt) / 1000))): 0;

    if (elapsedSeconds > 0) {
        if (stats.lastCategory === "focused") {
            stats.focusedSeconds += elapsedSeconds;
        } else if (stats.lastCategory === "distracted") {
            stats.distractedSeconds += elapsedSeconds;

            if (stats.lastDomain && stats.lastDomain !== "browser page") {
                stats.distractedDomains[stats.lastDomain] = (stats.distractedDomains[stats.lastDomain] || 0) + elapsedSeconds;
            }
        } else {
            stats.idleSeconds += elapsedSeconds;
        }
    }

    const current = await getCurrentFocusCategory(settings);
    stats.lastCategory = current.category;
    stats.lastDomain = current.domain;

    await chrome.storage.local.set({
        focusStats: stats,
        focusLastCheckedAt: now
    });

    return getFocusSummary({
        ...settings,
        focusStats: stats
    });
}

async function startFocus(subject, pomodoroEnabled = false) {
    const settings = await getSettings();
    const now = Date.now();
    const cleanSubject = String(subject || "").trim().toLowerCase()
    const focusSettings = {
        ...settings,
        focusActive: true,
        focusSubject: cleanSubject,
        pomodoroEnabled: Boolean(pomodoroEnabled),
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: now,
        pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: 0
    };

    const stats = await getFreshFocusStats(focusSettings);

    await chrome.storage.local.set({
        focusActive: true,
        focusSubject: cleanSubject,
        selectedFocusSubject: cleanSubject,
        focusStartedAt: now,
        focusLastCheckedAt: now,
        focusStats: stats,
        pomodoroEnabled: Boolean(pomodoroEnabled),
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: now,
        pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: 0
    });

    await chrome.alarms.clear(FOCUS_TICK_ALARM);
    await chrome.alarms.create(FOCUS_TICK_ALARM, {
        periodInMinutes: 1
    });

    await injectFocusOverlayIntoOpenTabs();
    await enforceStrictFocus(focusSettings);
    
    return getFocusSummary({
        ...settings,
        focusActive: true,
        focusSubject: cleanSubject,
        focusStats: stats,
        pomodoroEnabled: Boolean(pomodoroEnabled),
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: now,
        pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: 0
    });
}

async function handlePomodoroTick(settings = null) {
    settings = settings || await getSettings();

    if (!settings.focusActive || !settings.pomodoroEnabled) {
        return settings.focusActive
            ? await recordFocusElapsed()
            : getFocusSummary(settings);
    }

    if (pomodoroTransitionRunning) {
        return getFocusSummary(settings);
    }

    const secondsLeft = getPomodoroSecondsLeft(settings);

    if (secondsLeft === null || secondsLeft > 0) {
        return await recordFocusElapsed();
    }

    pomodoroTransitionRunning = true;

    try {
        if (settings.pomodoroPhase === "work") {
            const completedSummary = {
                ...(await recordFocusElapsed()),
                focusActive: false,
                completedAt: new Date().toISOString(),
                pomodoroAutoUploaded: true
            };
            const latestSettings = await getSettings();
            const completedSummaryWithUpload = await uploadAndStoreCompletedSummary(
                completedSummary,
                latestSettings
            );
            const now = Date.now();
            const nextSettings = {
                ...latestSettings,
                focusActive: true,
                pomodoroEnabled: true,
                pomodoroPhase: "break",
                pomodoroPhaseStartedAt: now,
                pomodoroPhaseDurationSeconds: POMODORO_BREAK_SECONDS,
                pomodoroWorkBlocksCompleted: (latestSettings.pomodoroWorkBlocksCompleted || 0) + 1,
                focusStats: { ...DEFAULT_STATS },
                focusLastCheckedAt: now
            };

            await chrome.storage.local.set({
                pomodoroPhase: "break",
                pomodoroPhaseStartedAt: now,
                pomodoroPhaseDurationSeconds: POMODORO_BREAK_SECONDS,
                pomodoroWorkBlocksCompleted: nextSettings.pomodoroWorkBlocksCompleted,
                focusStats: { ...DEFAULT_STATS },
                focusLastCheckedAt: now
            });

            await showPomodoroNotification(
                "Pomodoro work complete",
                `Uploaded ${completedSummaryWithUpload.serverUpload?.minutes || 0} min. Break started.`
            );

            return getFocusSummary(nextSettings);
        }

        const now = Date.now();
        const nextSettings = {
            ...settings,
            focusActive: true,
            pomodoroEnabled: true,
            pomodoroPhase: "work",
            pomodoroPhaseStartedAt: now,
            pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
            focusLastCheckedAt: now
        };
        const freshStats = await getFreshFocusStats(nextSettings);

        await chrome.storage.local.set({
            pomodoroPhase: "work",
            pomodoroPhaseStartedAt: now,
            pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
            focusStats: freshStats,
            focusLastCheckedAt: now
        });

        await showPomodoroNotification(
            "Pomodoro break finished",
            "Work started."
        );

        await enforceStrictFocus({
            ...nextSettings,
            focusStats: freshStats
        });

        return getFocusSummary({
            ...nextSettings,
            focusStats: freshStats
        });
    } finally {
        pomodoroTransitionRunning = false;
    }
}

async function refreshFocusState() {
    const settings = await getSettings();

    if (!settings.focusActive) {
        return getFocusSummary(settings);
    }

    if (settings.pomodoroEnabled) {
        return await handlePomodoroTick(settings);
    }

    return await recordFocusElapsed();
}

async function stopFocus() {
    const settings = await getSettings();
    const shouldUploadOnStop = !settings.pomodoroEnabled || settings.pomodoroPhase === "work";
    let completedSummaryWithUpload = {
        ...getFocusSummary(settings),
        focusActive: false,
        serverUpload: {
            ok: false,
            error: "Pomodoro stopped. Completed work blocks were already uploaded."
        },
        qualityUpload: {
            ok: false,
            error: "Pomodoro stopped."
        }
    };

    if (shouldUploadOnStop) {
        const completedSummary = {
            ...(await recordFocusElapsed()),
            focusActive: false,
            completedAt: new Date().toISOString()
        };
        completedSummaryWithUpload = await uploadAndStoreCompletedSummary(
            completedSummary,
            await getSettings()
        );
    }

    await chrome.alarms.clear(FOCUS_TICK_ALARM);
    await chrome.storage.local.set({
        focusActive: false,
        focusLastCheckedAt: null,
        selectedFocusSubject: settings.focusSubject || settings.selectedFocusSubject || "",
        focusSubject: "",
        pomodoroEnabled: false,
        pomodoroPhase: "work",
        pomodoroPhaseStartedAt: null,
        pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
        pomodoroWorkBlocksCompleted: 0,
    });

    return completedSummaryWithUpload;
}

function getNextTimetableTime(dayValue, timeValue) {
    const dayIndex = {
        Sun: 0,
        Mon: 1,
        Tue: 2,
        Wed: 3,
        Thu: 4,
        Fri: 5,
        Sat: 6
    }[dayValue];
    const [hours, minutes] = timeValue.split(":").map(Number);
    const next = new Date();

    next.setHours(hours, minutes, 0, 0);

    const daysUntilSession = (dayIndex - next.getDay() + 7) % 7;
    next.setDate(next.getDate() + daysUntilSession);

    if (next.getTime() <= Date.now()) {
        next.setDate(next.getDate() + 7);
    }

    return next.getTime();
}

async function clearTimetableReminders() {
    const alarms = await chrome.alarms.getAll();

    await Promise.all(
        alarms
            .filter((alarm) => alarm.name.startsWith(TIMETABLE_ALARM_PREFIX))
            .map((alarm) => chrome.alarms.clear(alarm.name))
    );
}

async function scheduleTimetableReminders(timetable = null) {
    const settings = await getSettings();
    const sessions = cleanTimetableList(timetable || settings.syncedTimetable);

    await clearTimetableReminders();

    if (!settings.remindersEnabled) {
        return;
    }

    sessions.forEach((session, index) => {
        chrome.alarms.create(`${TIMETABLE_ALARM_PREFIX}${index}`, {
            when: getNextTimetableTime(session.day, session.start_time),
            periodInMinutes: 10080
        });
    });
}

async function scheduleDailyReminder() {
    await chrome.alarms.clear(DAILY_REMINDER_ALARM);
}

async function showStudyReminder(isTest = false) {
    await chrome.notifications.create({
        type: "basic",
        iconUrl: ICON_URL,
        title: isTest ? "StudyStreak test reminder" : "StudyStreak reminder",
        message: "Time to protect the streak and do a study session.",
        priority: 1
    });
}

async function showTimetableReminder(alarmName) {
    const settings = await getSettings();
    const index = Number(alarmName.replace(TIMETABLE_ALARM_PREFIX, ""));
    const session = cleanTimetableList(settings.syncedTimetable)[index];

    if (!settings.remindersEnabled || !session) {
        return;
    }

    await chrome.notifications.create({
        type: "basic",
        iconUrl: ICON_URL,
        title: "StudyStreak timetable",
        message: `${session.subject} starts now. Planned for ${session.minutes} min.`,
        priority: 1
    });
}

async function restoreExtension() {
    await scheduleDailyReminder();
    await scheduleTimetableReminders();

    const settings = await getSettings();

    if (settings.focusActive) {
        await chrome.alarms.create(FOCUS_TICK_ALARM, {
            periodInMinutes: 1
        });
    }

    if (settings.focusActive || (settings.serverToken && settings.todoOverlayEnabled !== false)) {
        await injectFocusOverlayIntoOpenTabs();
    }
}

chrome.runtime.onInstalled.addListener(restoreExtension);
chrome.runtime.onStartup.addListener(restoreExtension);

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === DAILY_REMINDER_ALARM) {
        showStudyReminder(false);
    }

    if (alarm.name.startsWith(TIMETABLE_ALARM_PREFIX)) {
        showTimetableReminder(alarm.name);
    }

    if (alarm.name === FOCUS_TICK_ALARM) {
        refreshFocusState().catch(() => {});
    }
});

chrome.tabs.onActivated.addListener((activeInfo) => {
    refreshFocusState().catch(() => {});
    enforceStrictFocus().catch(() => {});
    injectFocusOverlayIntoTab(activeInfo.tabId).catch(() => {});
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url || changeInfo.status === "loading" || changeInfo.status === "complete") {
        refreshFocusState().catch(() => {});
        enforceStrictFocus().catch(() => {});
        injectFocusOverlayIntoTab(tabId).catch(() => {});

        if (changeInfo.status !== "complete") {
            scheduleOverlayInjection(tabId, 750);
        }
    }
});

if (chrome.webNavigation?.onCommitted) {
    chrome.webNavigation.onCommitted.addListener((details) => {
        if (details.frameId !== 0) {
            return;
        }

        refreshFocusState().catch(() => {});
        injectFocusOverlayIntoTab(details.tabId, details.url).catch(() => {});
        scheduleOverlayInjection(details.tabId, 300);
    });
}

if (chrome.webNavigation?.onDOMContentLoaded) {
    chrome.webNavigation.onDOMContentLoaded.addListener((details) => {
        if (details.frameId !== 0) {
            return;
        }

        injectFocusOverlayIntoTab(details.tabId, details.url).catch(() => {});
        scheduleOverlayInjection(details.tabId, 600);
    });
}

chrome.tabs.onRemoved.addListener((tabId) => {
    strictFocusRedirects.delete(tabId);
});

chrome.idle.onStateChanged.addListener(() => {
    refreshFocusState().catch(() => {});
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    async function handleMessage() {
        if (message.type === "clearFocusHistory") {
            await chrome.storage.local.set({
                focusHistory: [],
                lastCompletedFocusSession: null
            });

            return { ok: true };
        }

        if (message.type === "getCompanionState") {
            const settings = await getSettings();
            const summary = settings.focusActive
                ? await refreshFocusState()
                : getFocusSummary(settings);

            return {
                settings: await getSettings(),
                summary
            };
        }

        if (message.type === "retryOfflineUploads") {
            return await retryOfflineUploads();
        }

        if (message.type === "saveSettings") {
            const nextSettings = { ...(message.settings || {}) };
            const shouldRefreshOverlays = (
                Object.prototype.hasOwnProperty.call(nextSettings, "todoItems") ||
                Object.prototype.hasOwnProperty.call(nextSettings, "todoOverlayEnabled")
            );

            if (Object.prototype.hasOwnProperty.call(nextSettings, "todoItems")) {
                nextSettings.todoItems = cleanTodoItems(nextSettings.todoItems);
            }

            if (Object.prototype.hasOwnProperty.call(nextSettings, "todoOverlayEnabled")) {
                nextSettings.todoOverlayEnabled = nextSettings.todoOverlayEnabled !== false;
            }

            await chrome.storage.local.set(nextSettings);
            await scheduleDailyReminder();
            await scheduleTimetableReminders();

            if (shouldRefreshOverlays) {
                await injectFocusOverlayIntoOpenTabs();
            }

            return { ok: true };
        }

        if (message.type === "saveTodoItems") {
            const settings = await getSettings();
            const todoItems = cleanTodoItems(message.todoItems);

            return await saveTodoItemsWithSync(todoItems, settings);
        }

        if (message.type === "completeAllTodoItems") {
            return await completeAllTodoItems();
        }

        if (message.type === "setTodoOverlayEnabled") {
            await chrome.storage.local.set({
                todoOverlayEnabled: message.enabled !== false
            });
            await injectFocusOverlayIntoOpenTabs();
            return { ok: true };
        }

        if (message.type === "loginToServer") {
            try {
                return await loginToServer(message.username || "", message.password || "");
            } catch(error) {
                await setSyncStatus("failed", friendlyNetworkError(error, "Login failed."));
                return { ok: false, error: friendlyNetworkError(error, "Login failed.")};
            }
        }
        
        if (message.type === "logoutFromServer") {
            return await logoutFromServer();
        }

        if (message.type === "refreshSubjects") {
            try {
                return await refreshSubjectsFromServer();
            } catch(error) {
                await setSyncStatus("failed", friendlyNetworkError(error, "Could not refresh subjects."));
                return {
                    ok: false,
                    error: friendlyNetworkError(error, "Could not refresh subjects."),
                    subjects: []
                };
            }
        }

        if (message.type === "saveSubjectWebsites") {
            try {
                return await saveSubjectWebsitesForSubject(
                    message.subject || "",
                    message.websites || []
                );
            } catch(error) {
                await setSyncStatus("failed", friendlyNetworkError(error, "Could not save focus websites."));
                return {
                    ok: false,
                    error: friendlyNetworkError(error, "Could not save focus websites.")
                };
            }
        }

        if (message.type === "saveFocusReview") {
            return await saveFocusReview(
                message.completedAt || "",
                message.topic || "",
                message.reviewNote || ""
            );
        }

        if (message.type === "skipFocusReview") {
            return await skipFocusReview(message.completedAt || "");
        }

        if (message.type === "testNotification") {
            await showStudyReminder(true);
            return { ok: true };
        }

        if (message.type === "startFocus") {
            return await startFocus(
                message.subject || "",
                Boolean(message.pomodoroEnabled)
            ) ;
        }

        if (message.type === "stopFocus") {
            return await stopFocus();
        }

        if (message.type === "getFocusStatus") {
            const settings = await getSettings();
            return settings.focusActive
                ? await refreshFocusState()
                : getFocusSummary(settings);
        }

        return { ok: false };
    }

    handleMessage().then(sendResponse);
    return true;
});

async function enforceStrictFocus(settings = null) {
    settings = settings || await getSettings();

    if (!settings.focusActive || !settings.strictFocusEnabled) {
        strictFocusRedirects.clear();
        return;
    }

    if (settings.pomodoroEnabled && settings.pomodoroPhase === "break") {
        strictFocusRedirects.clear();
        return;
    }

    const allowedDomains = getAllowedDomainsForFocus(settings);

    if (allowedDomains.length === 0) {
        return;
    }

    const [tab] = await chrome.tabs.query({
        active: true,
        lastFocusedWindow: true
    });

    if (!tab?.id || !tab?.url) {
        return;
    }

    if (isNewTabPageUrl(tab.url)) {
        return;
    }

    const currentDomain = getDomainFromUrl(tab.url);

    if (!currentDomain) {
        return;
    }

    if (isAllowedDomain(currentDomain, allowedDomains)) {
        strictFocusRedirects.delete(tab.id);
        return;
    }

    if (strictFocusRedirectIsPending(tab.id)) {
        return;
    }

    const redirectUrl = getStrictFocusRedirectUrl(allowedDomains);

    if (!redirectUrl) {
        return;
    }

    strictFocusRedirects.set(tab.id, {
        url: redirectUrl,
        startedAt: Date.now()
    });

    await chrome.tabs.update(tab.id, {
        url: getStrictFocusBlockedUrl(redirectUrl, settings.focusSubject)
    });
}
