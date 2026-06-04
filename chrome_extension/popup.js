const remindersEnabled = document.querySelector("#reminders-enabled");
const reminderTime = document.querySelector("#reminder-time");
const saveButton = document.querySelector("#save-button");
const testButton = document.querySelector("#test-button");
const statusText = document.querySelector("#status");

async function loadSettings() {
    const settings = await chrome.runtime.sendMessage({
        type: "getReminderSettings"
    });

    remindersEnabled.checked = settings.remindersEnabled;
    reminderTime.value = settings.reminderTime;
}

async function saveSettings() {
    await chrome.runtime.sendMessage({
        type: "saveReminderSettings",
        settings: {
            remindersEnabled: remindersEnabled.checked,
            reminderTime: reminderTime.value || "17:00"
        }
    });

    statusText.textContent = "Saved.";
}

async function testNotification() {
    await chrome.runtime.sendMessage({
        type: "testNotification"
    });

    statusText.textContent = "Test sent.";
}

saveButton.addEventListener("click", saveSettings);
testButton.addEventListener("click", testNotification);

loadSettings();
