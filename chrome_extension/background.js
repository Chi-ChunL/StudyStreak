const DAILY_REMINDER_ALARM = "studystreak-daily-reminder";
const API_BASE_URL = "https://chichi.hackclub.app";
const FOCUS_TICK_ALARM = "studystreak-focus-tick";


const DEFAULT_STATS = {
    focusedSeconds: 0,
    distractedSeconds: 0,
    idleSeconds: 0,
    lastDomain: "none",
    lastCategory: "idle",
    distractedDomains: {}
};

const DEFAULT_SETTINGS = {
    remindersEnabled: true,
    reminderTime: "17:00",
    allowedDomains: ["pearsonactivelearn.com", "quizlet.com", "senecalearning.com"],
    focusActive: false,
    focusStartedAt: null,
    focusLastCheckedAt: null,
    focusStats: DEFAULT_STATS,
    lastCompletedFocusSession: null,
    focusHistory: [],
    focusSubject: "",
    syncedSubjects: [],
    serverUsername: "",
    serverToken: ""
};

const ICON_URL = chrome.runtime.getURL("icon128.png");

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
        serverUsername: typeof saved.serverUsername === "string" ? saved.serverUsername : "",
        serverToken: typeof saved.serverToken ==="string" ? saved.serverToken: "",
        focusSubject: typeof saved.focusSubject === "string" ? saved.focusSubject: "",
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

    await chrome.storage.local.set({
        syncedSubjects: subjects
    });

    return {
        ok: true,
        subjects
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
        header: {
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

async function loginToServer(username, password) {
    const cleanUsername = username.trim().toLowerCase();

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

    try {
        subjects = await fetchSubjectsFromServer(data.access_token);
    } catch {
        subjects = [];
    }

    await chrome.storage.local.set({
        serverUsername: cleanUsername,
        serverToken: data.access_token,
        syncedSubjects: subjects
    });

    return { ok: true, serverUsername: cleanUsername, subjects };
}

async function logoutFromServer() {
    await chrome.alarms.clear(FOCUS_TICK_ALARM);

    await chrome.storage.local.set({
        serverUsername: "",
        serverToken: "",
        focusActive: false,
        focusLastCheckedAt: null,
        focusSubject: "",
        syncedSubjects: []
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

async function getActiveTabDomain() {
    const [tab] = await chrome.tabs.query({
        active: true,
        lastFocusedWindow: true
    });

    return getDomainFromUrl(tab?.url || "");
}

async function getCurrentFocusCategory(settings) {
    const idleState = await chrome.idle.queryState(60);

    if (idleState !== "active") {
        return { category: "idle", domain: "idle" };
    }

    const domain = await getActiveTabDomain();

    if (!domain) {
        return { category: "distracted", domain: "browser page" };
    }

    if (isAllowedDomain(domain, settings.allowedDomains)) {
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
        score,
        totalSeconds,
        topDistractedDomain,
        ...stats
    };
} 

async function recordFocusElapsed() {
    const settings = await getSettings();

    if (!settings.focusActive) {
        return getFocusSummary(settings);
    }

    const now = Date.now();
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

async function startFocus(subject) {
    const settings = await getSettings();
    const now = Date.now();
    const current = await getCurrentFocusCategory(settings);
    const cleanSubject = String(subject || "").trim().toLowerCase()

    const stats = {
        ...DEFAULT_STATS,
        lastCategory: current.category,
        lastDomain: current.domain
    };

    await chrome.storage.local.set({
        focusActive: true,
        focusSubject: cleanSubject,
        focusStartedAt: now,
        focusLastCheckedAt: now,
        focusStats: stats
    });

    await chrome.alarms.clear(FOCUS_TICK_ALARM);
    await chrome.alarms.create(FOCUS_TICK_ALARM, {
        periodInMinutes: 1
    });

    return getFocusSummary({
        ...settings,
        focusActive: true,
        focusSubject: cleanSubject,
        focusStats: stats
    });
}

async function stopFocus() {
    const completedSummary = {
        ...(await recordFocusElapsed()),
        focusActive: false,
        completedAt: new Date().toISOString()
    };

    const settings = await getSettings();

    let serverUpload = { ok: false, error: "Not uploaded."};
    let qualityUpload = { ok: false, error: "Not synced"};

    try {
        serverUpload = await uploadCompletedFocusSession(
            completedSummary,
            settings.serverToken
        );
    } catch (error) {
        serverUpload = {
            ok: false,
            error: error.message || "Upload failed."
        };
    }

    try {
        qualityUpload = await uploadFocusQualitySession(
            completedSummary,
            settings.serverToken
        );
    } catch(error) {
        qualityUpload = {
            ok: false,
            error: error.message || "Quality sync failed."
        };
    }

    const completedSummaryWithUpload = {
        ...completedSummary,
        serverUpload,
        qualityUpload
    };

    const focusHistory = [
        completedSummaryWithUpload,
        ...(settings.focusHistory || [])
    ].slice(0,3);

    await chrome.alarms.clear(FOCUS_TICK_ALARM);
    await chrome.storage.local.set({
        focusActive: false,
        focusLastCheckedAt: null,
        lastCompletedFocusSession: completedSummaryWithUpload,
        focusHistory,
        focusSubject: "",
    });

    return completedSummaryWithUpload;
}

function getNextReminderTime(timeValue) {
    const [hours, minutes] = timeValue.split(":").map(Number);
    const next = new Date();

    next.setHours(hours, minutes, 0, 0);

    if (next.getTime() <= Date.now()) {
        next.setDate(next.getDate() + 1);
    }

    return next.getTime();
}

async function scheduleDailyReminder() {
    const settings = await getSettings();

    await chrome.alarms.clear(DAILY_REMINDER_ALARM);

    if (!settings.remindersEnabled) {
        return;
    }

    await chrome.alarms.create(DAILY_REMINDER_ALARM, {
        when: getNextReminderTime(settings.reminderTime),
        periodInMinutes: 1440
    });
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

async function restoreExtension() {
    await scheduleDailyReminder();

    const settings = await getSettings();

    if (settings.focusActive) {
        await chrome.alarms.create(FOCUS_TICK_ALARM, {
            periodInMinutes: 1
        });
    }
}

chrome.runtime.onInstalled.addListener(restoreExtension);
chrome.runtime.onStartup.addListener(restoreExtension);

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === DAILY_REMINDER_ALARM) {
        showStudyReminder(false);
    }

    if (alarm.name === FOCUS_TICK_ALARM) {
        recordFocusElapsed();
    }
});

chrome.tabs.onActivated.addListener(() => {
    recordFocusElapsed();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url || changeInfo.status === "complete") {
        recordFocusElapsed();
    }
});

chrome.idle.onStateChanged.addListener(() => {
    recordFocusElapsed();
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
                ? await recordFocusElapsed()
                : getFocusSummary(settings);

            return {
                settings: await getSettings(),
                summary
            };
        }

        if (message.type === "saveSettings") {
            await chrome.storage.local.set(message.settings);
            await scheduleDailyReminder();
            return { ok: true };
        }

        if (message.type === "loginToServer") {
            try {
                return await loginToServer(message.username || "", message.password || "");
            } catch(error) {
                return { ok: false, error: error.message || "Login failed."};
            }
        }
        
        if (message.type === "logoutFromServer") {
            return await logoutFromServer();
        }

        if (message.type === "refreshSubjects") {
            try {
                return await refreshSubjectsFromServer();
            } catch(error) {
                return { ok: false, error: error.message || "Could not refresh subjects.", subjects: [] };
            }
        }

        if (message.type === "testNotification") {
            await showStudyReminder(true);
            return { ok: true };
        }

        if (message.type === "startFocus") {
            return await startFocus(message.subject || "") ;
        }

        if (message.type === "stopFocus") {
            return await stopFocus();
        }

        if (message.type === "getFocusStatus") {
            const settings = await getSettings();
            return settings.focusActive
                ? await recordFocusElapsed()
                : getFocusSummary(settings);
        }

        return { ok: false };
    }

    handleMessage().then(sendResponse);
    return true;
});
