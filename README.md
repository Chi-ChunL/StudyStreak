<p align="center">
  <img src="https://raw.githubusercontent.com/Chi-ChunL/StudyStreak/main/assets/studystreak-banner.png" alt="StudyStreak banner" width="100%">
</p>

# StudyStreak

StudyStreak is a terminal study tracker that helps students build consistent study habits. It includes streak tracking, session logging, timetable planning, focus mode, achievements, leaderboard sync, and a Chrome companion extension for focus-quality tracking.

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

## Features

- Track daily study streaks
- Log study sessions by subject
- Plan timetable sessions
- Use Focus Mode to time study sessions
- Track Chrome focus quality with the companion extension
- Sync subjects, timetable sessions, streaks, and focus-quality summaries
- View leaderboard streak rankings
- Unlock achievements
- Export and import focus-quality data as an offline fallback

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

## Browser Extension

The companion browser extension adds focus tracking. It can:

- Start and stop focus sessions
- Detect focused, distracted, and idle time
- Sync focus-quality summaries to the app
- Show today's timetable sessions
- Send timetable reminders
- Optionally enable Strict Focus to redirect distracting sites

To install it locally, clone this repository first:

```bash
git clone https://github.com/Chi-ChunL/StudyStreak.git
```

Chrome:

1. Open `chrome://extensions`
2. Turn on `Developer mode`
3. Click `Load unpacked`
4. Choose the `chrome_extension` folder

Firefox or Zen:

1. Open `about:debugging#/runtime/this-firefox`
2. Click `Load Temporary Add-on`
3. Choose `chrome_extension/manifest.json`

Temporary Firefox/Zen add-ons need to be loaded again after restarting the browser. A signed release will make this smoother later.

## Cloud Sync

StudyStreak works locally without sync. Online account sync and leaderboard features require a StudyStreak backend account and server.

If you are running your own backend, set:

```bash
STUDYSTREAK_API_URL=https://your-backend-url
```

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

Build the package:

```bash
python -m build
```

## Privacy

StudyStreak stores local study data on your machine. Cloud sync only sends data needed for account sync, leaderboard streaks, timetable data, subject websites, and focus-quality summaries.

## Status

StudyStreak is in early development. Expect improvements to setup, sync, packaging, and browser support over time.
