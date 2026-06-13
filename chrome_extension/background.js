const DAILY_REMINDER_ALARM = "studystreak-daily-reminder";
const API_BASE_URL = "https://chichi.hackclub.app";
const FOCUS_TICK_ALARM = "studystreak-focus-tick";
const TIMETABLE_ALARM_PREFIX = "studystreak-timetable-";
const POMODORO_WORK_SECONDS = 50 * 60;
const POMODORO_BREAK_SECONDS = 10 * 60;
const IDLE_DETECTION_SECONDS = 8 * 60;


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
    syncedTimetable: [],
    serverUsername: "",
    serverToken: "",
    strictFocusEnabled: false,
    pomodoroEnabled: false,
    pomodoroPhase: "work",
    pomodoroPhaseStartedAt: null,
    pomodoroPhaseDurationSeconds: POMODORO_WORK_SECONDS,
    pomodoroWorkBlocksCompleted: 0,
};

const ICON_URL = chrome.runtime.getURL("icon128.png");
let pomodoroTransitionRunning = false;

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
    const timetable = await fetchTimetableFromServer(settings.serverToken);
    const selectedFocusSubject = getSelectedSubjectForList(
        subjects,
        settings.selectedFocusSubject || settings.focusSubject
    );

    await chrome.storage.local.set({
        syncedSubjects: subjects,
        syncedSubjectWebsites: subjectWebsites,
        syncedTimetable: timetable,
        selectedFocusSubject
    });
    await scheduleTimetableReminders(timetable);

    return {
        ok: true,
        subjects,
        subjectWebsites,
        timetable,
        selectedFocusSubject
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

async function uploadAndStoreCompletedSummary(completedSummary, settings) {
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
    ].slice(0, 3);

    await chrome.storage.local.set({
        lastCompletedFocusSession: completedSummaryWithUpload,
        focusHistory
    });

    return completedSummaryWithUpload;
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
    let timetable = [];

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
        timetable = await fetchTimetableFromServer(data.access_token);
    } catch {
        timetable = [];
    }

    const selectedFocusSubject = sameAccount
        ? getSelectedSubjectForList(
            subjects,
            previousSettings.selectedFocusSubject || previousSettings.focusSubject
        )
        : "";

    if (!sameAccount) {
        await chrome.alarms.clear(FOCUS_TICK_ALARM);
        await clearTimetableReminders();
    }

    await chrome.storage.local.set({
        serverUsername: cleanUsername,
        serverToken: data.access_token,
        syncedSubjects: subjects,
        syncedSubjectWebsites: subjectWebsites,
        syncedTimetable: timetable,
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
            : 0
    });
    await scheduleTimetableReminders(timetable);

    return {
        ok: true,
        serverUsername: cleanUsername,
        subjects,
        subjectWebsites,
        timetable,
        selectedFocusSubject
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
        syncedSubjects: [],
        syncedSubjectWebsites: {},
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

async function injectFocusOverlayIntoOpenTabs() {
    if (!chrome.scripting?.executeScript) {
        return;
    }

    const tabs = await chrome.tabs.query({});

    await Promise.all(
        tabs
            .filter((tab) => tab.id && canInjectOverlayIntoUrl(tab.url || ""))
            .map(async (tab) => {
                try {
                    await chrome.scripting.executeScript({
                        target: { tabId: tab.id },
                        files: ["focus_overlay.js"]
                    });
                } catch {
                    // Some pages reject extension injection; content_scripts handles future page loads.
                }
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

chrome.tabs.onActivated.addListener(() => {
    refreshFocusState().catch(() => {});
    enforceStrictFocus().catch(() => {});
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.url || changeInfo.status === "complete") {
        refreshFocusState().catch(() => {});
        enforceStrictFocus().catch(() => {});
    }
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

        if (message.type === "saveSettings") {
            await chrome.storage.local.set(message.settings);
            await scheduleDailyReminder();
            await scheduleTimetableReminders();
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

        if (message.type === "saveSubjectWebsites") {
            try {
                return await saveSubjectWebsitesForSubject(
                    message.subject || "",
                    message.websites || []
                );
            } catch(error) {
                return { ok: false, error: error.message || "Could not save focus websites." };
            }
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
        return;
    }

    if (settings.pomodoroEnabled && settings.pomodoroPhase === "break") {
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

    if (!currentDomain || isAllowedDomain(currentDomain, allowedDomains)) {
        return;
    }

    const redirectDomain = allowedDomains[
        Math.floor(Math.random() * allowedDomains.length)
    ];
    const redirectUrl = redirectDomain.startsWith("http://") ||
        redirectDomain.startsWith("https://")
        ? redirectDomain
        : `https://${redirectDomain}`;

    await chrome.tabs.update(tab.id, {
        url: redirectUrl
    });
}
