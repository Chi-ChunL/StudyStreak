<p align="center">
  <img src="https://raw.githubusercontent.com/Chi-ChunL/StudyStreak/main/assets/studystreak-banner.png" alt="StudyStreak banner" width="100%">
</p>

# StudyStreak

StudyStreak is a terminal study tracker for building consistent study habits. It tracks daily streaks, study sessions, subjects, timetable plans, focus mode, achievements, leaderboard streaks, and browser focus quality through the companion extension.

## Preview

<p align="center">
  <img src="https://raw.githubusercontent.com/Chi-ChunL/StudyStreak/main/assets/studystreak-dashboard.png" alt="StudyStreak dashboard screenshot" width="85%">
</p>

## Install

StudyStreak requires Python 3.10 or newer.

```bash
pip install studystreak
```

Open the app:

```bash
studystreak ui
```

Update to the newest PyPI version:

```bash
pip install --upgrade studystreak
```

## Quick Start

1. Run `studystreak ui`.
2. Create an account or log in.
3. Add your subjects in Settings > Subjects.
4. Add the websites you use for each subject.
5. Log a study session, start Focus Mode, or add timetable sessions.
6. Press Sync Now if you want the terminal app and browser extension to share cloud data.

StudyStreak can be used locally, but account login enables cloud sync, Chrome/Firefox extension sync, leaderboard streaks, and cross-device data.

## Main App Guide

### Dashboard

The dashboard shows your current streak, whether today is protected, minutes studied today, weekly goal progress, setup checklist, and recent sessions.

### Subjects and Websites

Open Settings > Subjects to add subjects and save focus websites for each subject. These websites are used by Focus Mode and by the browser extension.

Each subject can have multiple websites. For example:

```text
https://pearsonactivelearn.com
https://quizlet.com
https://senecalearning.com
```

When synced, the extension can auto-fill websites for the selected subject. Websites saved in the extension can also sync back into the terminal app.

### Log Sessions

Use the Session tab to log study manually. A session protects your streak for the day. StudyStreak prevents the same day from incorrectly becoming multiple streak days.

You can also log from the command line:

```bash
studystreak log maths 30
studystreak today
studystreak streak
```

### Manage Sessions

Use Manage Session to delete incorrect study sessions. If nothing is selected, the app shows a message instead of crashing.

### Timetable

Use Timetable to add planned study sessions. The browser extension can sync today's timetable and send browser notifications when a planned session starts.

### Focus Mode

Focus Mode times a study session for a selected subject. If that subject has saved websites, the app can open all of them for you.

Focus Mode also has Pomodoro 50/10:

- Work runs for 50 minutes.
- Break runs for 10 minutes.
- Completed work blocks are logged automatically.
- The cycle repeats until you stop focus.

### Leaderboard

The leaderboard shows users by current streak day. Focus sessions from the browser extension and sessions logged in the app both help protect the streak, but the same date only counts once.

### Achievements

Achievements unlock as you build subjects, log sessions, use focus mode, and keep your streak going.

### Settings and Sync

Use Settings > Sync > Sync Now to upload local changes and download browser focus updates, subject websites, and other cloud-backed data.

Cloud sync includes:

- encrypted profile data
- subjects
- subject websites
- timetable sessions
- current streak for the leaderboard
- browser focus-quality summaries

## Browser Extension

The companion browser extension adds focus-quality tracking and tighter study workflows.

It can:

- start and stop focus sessions
- show a timer overlay on study webpages
- show Work or Break during Pomodoro 50/10
- upload each completed Pomodoro work block
- detect focused, distracted, and idle time
- use an 8 minute idle threshold
- sync full focus-quality summaries to the app
- sync subject websites from the account
- save subject websites back to the server
- remember the last selected focus subject
- show today's timetable sessions
- send timetable notifications
- use Strict Focus to redirect distracting websites to one of the allowed websites

### Chrome Install

Clone the repository:

```bash
git clone https://github.com/Chi-ChunL/StudyStreak.git
cd StudyStreak
```

Load the extension:

1. Open `chrome://extensions`.
2. Turn on Developer mode.
3. Click Load unpacked.
4. Choose the `chrome_extension` folder.
5. Open the StudyStreak extension popup and log in.
6. Click Refresh Subjects.

### Firefox or Zen Temporary Install

Firefox and Zen need the Firefox-specific extension folder:

```bash
python scripts/build_firefox_extension.py
```

Then:

1. Open `about:debugging#/runtime/this-firefox`.
2. Click Load Temporary Add-on.
3. Choose `dist/firefox_extension/manifest.json`.
4. Open the StudyStreak extension popup and log in.
5. Click Refresh Subjects.

Temporary add-ons disappear after restarting Firefox or Zen.

## Using the Extension

1. Log in with the same StudyStreak account as the terminal app.
2. Press Refresh Subjects.
3. Choose a subject.
4. Check that the Focus websites box fills with that subject's saved websites.
5. Edit the websites if needed and press Save Focus Websites.
6. Turn on Strict Focus if you only want allowed websites during focus.
7. Turn on Pomodoro 50/10 if you want automatic 50 minute work blocks and 10 minute breaks.
8. Press Start Focus.
9. Use Stop Focus in the popup or on the overlay.

When focus stops, the extension reports whether leaderboard upload and quality sync succeeded.

## Cloud Sync

StudyStreak uses `https://chichi.hackclub.app` by default.

If you run your own backend, set:

```bash
STUDYSTREAK_API_URL=https://your-backend-url
```

Then start the app normally:

```bash
studystreak ui
```

The browser extension currently points at the deployed StudyStreak server. If you want it to use a different backend, change `API_BASE_URL` in `chrome_extension/background.js` before loading or packaging the extension.

## Local Data

Installed StudyStreak stores app data in the user app data folder, not inside the project directory. This keeps normal installs cleaner and avoids losing data when the package is updated.

On Windows, the app data is under:

```text
%LOCALAPPDATA%\StudyStreak
```

## Commands

```bash
studystreak ui
studystreak log maths 30
studystreak today
studystreak streak
studystreak create-user alex
studystreak login alex
studystreak logout
studystreak users
```

Most users should use `studystreak ui`; the other commands are useful for quick logging and account checks.

## Development

Clone the repo:

```bash
git clone https://github.com/Chi-ChunL/StudyStreak.git
cd StudyStreak
```

Install locally:

```bash
pip install -e .
```

Run the app:

```bash
studystreak ui
```

Run tests:

```bash
python -m unittest discover -s tests
```

Build the package:

```bash
python -m build
```

Build the Firefox/Zen extension folder:

```bash
python scripts/build_firefox_extension.py
```

## Backend Development

Install backend requirements, then run the FastAPI server:

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The backend creates its SQLite tables on startup.

## Troubleshooting

### The extension has no subjects

Log in to the extension, then click Refresh Subjects. In the terminal app, add subjects in Settings > Subjects and press Sync Now.

### Websites saved in the extension do not show in the app

Open the terminal app and press Settings > Sync > Sync Now, or open Settings > Subjects again. The app downloads subject websites from the server.

### Firefox says the extension is temporary

That is expected when loading through `about:debugging`. For a permanent Firefox or Zen install, use a signed self-distributed `.xpi`.

### The overlay does not appear immediately in Firefox or Zen

Open or refresh a normal website tab. Browser-protected pages such as `about:`, `chrome://`, and extension pages do not allow the overlay.

### Sync failed

Check that you are logged in, the backend is online, and `STUDYSTREAK_API_URL` points to the right server if you are using a custom backend.

## Privacy

StudyStreak stores local study data on your machine. Cloud sync sends the data needed for account sync, leaderboard streaks, timetable reminders, subject websites, and focus-quality summaries.

The browser extension may send focus summary data to the StudyStreak backend when you are logged in. Signed JSON export remains available as an offline/debug fallback.

## Status

StudyStreak is in active development. Expect improvements to packaging, sync, browser support, and onboarding over time.
