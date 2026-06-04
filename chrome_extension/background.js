const DAILY_REMINDER_ALARM = "studystreak-daily-reminder";

const DEFAULT_SETTINGS = {
    remindersEnabled: true,
    reminderTime: "17:00"
};

const ICON_URL = chrome.runtime.getURL("icon128.png");

async function getSettings() {
    const saved = await chrome.storage.local.get(DEFAULT_SETTINGS);
    return {...DEFAULT_SETTINGS, ...saved};
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

chrome.runtime.onInstalled.addListener(async () => {
    const saved = await chrome.storage.local.get(DEFAULT_SETTINGS);
    await chrome.storage.local.set({...DEFAULT_SETTINGS, ...saved});
    await scheduleDailyReminder();
});

chrome.runtime.onStartup.addListener(scheduleDailyReminder);

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === DAILY_REMINDER_ALARM) {
        showStudyReminder(false);
    }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    async function handleMessage() {
        if (message.type === "getReminderSettings") {
            return await getSettings();
        }

        if (message.type === "saveReminderSettings") {
            await chrome.storage.local.set(message.settings);
            await scheduleDailyReminder();
            return { ok: true };
        }

        if (message.type === "testNotification") {
            await showStudyReminder(true);
            return { ok: true };
        }

        return { ok: false };
    }

    handleMessage().then(sendResponse);
    return true;
});



