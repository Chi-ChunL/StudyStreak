import json
import webbrowser
from datetime import date, timedelta, datetime
from functools import partial
from importlib.metadata import PackageNotFoundError, version as package_version

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    TextArea,
    Button,
    TabbedContent,
    TabPane,
    Select,
    Checkbox,
)

from studystreak.storage import (
    clean_topic_list,
    clean_website_list,
    get_default_data,
    get_utc_now_text,
    load_data,
    merge_focus_quality_sessions,
    merge_cloud_focus_sessions,
    merge_subject_websites,
    merge_subject_topics,
    merge_todo_items,
    protect_streak_today,
    repair_data,
    save_data,
    save_focus_quality_json,
    save_local_data_without_sync,
)
from studystreak.accounts import create_account, list_accounts, login_account, logout_account
from studystreak.accounts import normalise_username, validate_password, validate_username
from studystreak.session import set_session, clear_session, get_session_username, save_session_data, set_server_token, get_server_token
from studystreak.auth_cache import (
    save_remembered_login,
    get_remembered_password,
    get_remembered_username,
    clear_remembered_login,
)
from studystreak.api_client import (
    login_to_server, 
    signup_to_server,
    delete_focus_session,
    upload_focus_session, 
    get_leaderboard,
    check_server_status,
    get_profile_data,
    get_focus_sessions,
    get_focus_quality_sessions,
    get_subject_websites,
    get_subject_topics,
    get_todo_items,
    get_latest_package_version,
)
from studystreak.profile_sync import decrypt_profile_data
from studystreak.notification import (
    play_sound,
    show_focus_complete_notification,
    show_sync_failed_notification,
    show_achievement_notification,
)
from studystreak.paths import get_app_data_dir


POMODORO_WORK_MINUTES = 50
POMODORO_BREAK_MINUTES = 10
NO_TOPIC_VALUE = "__no_topic__"

SETUP_TOUR_STEPS = [
    {
        "id": "dashboard",
        "title": "Home",
        "target_label": "Open Home",
        "body": (
            "This is your home base. Check the next best action, setup checklist, "
            "weekly progress, and recent sessions."
        ),
        "hint": "Look around, then press Done.",
        "manual": True,
    },
    {
        "id": "subject",
        "title": "Add A Subject",
        "target_label": "Add Subject",
        "body": (
            "Create the first subject you study, like maths, physics, "
            "or computer science."
        ),
        "hint": "Add a subject to continue.",
    },
    {
        "id": "websites",
        "title": "Save Subject Websites",
        "target_label": "Save Websites",
        "body": (
            "Save the websites you use for that subject. Focus Mode and "
            "the browser extension can auto-fill them later."
        ),
        "hint": "Choose a subject and save at least one website.",
    },
    {
        "id": "timetable",
        "title": "Plan A Session",
        "target_label": "Open Timetable",
        "body": (
            "Add one weekly planned session so StudyStreak and the extension "
            "know when study time is coming up."
        ),
        "hint": "Save one timetable session to continue.",
    },
    {
        "id": "session",
        "title": "Protect Your Streak",
        "target_label": "Log Session",
        "body": (
            "Log a short study session. The first study block of the day "
            "protects your streak."
        ),
        "hint": "Log a session to continue.",
    },
    {
        "id": "focus",
        "title": "Try Focus Mode",
        "target_label": "Open Focus Mode",
        "body": (
            "Focus Mode opens your subject websites, runs timers, and can "
            "use Pomodoro 50/10."
        ),
        "hint": "Try it now, or press Done/Skip if you are not studying yet.",
        "optional": True,
    },
    {
        "id": "sync",
        "title": "Check Sync",
        "target_label": "Open Sync",
        "body": (
            "Sync pulls browser focus data and subject websites from your "
            "account when you are online."
        ),
        "hint": "Press Sync Now if you are online, or Done if you are staying local.",
        "optional": True,
    },
    {
        "id": "finish",
        "title": "Finish",
        "target_label": "Finish Tour",
        "body": (
            "You now know the main loop: subjects, websites, timetable, "
            "study sessions, focus mode, and sync."
        ),
        "hint": "Press Done to finish the tour.",
        "manual": True,
    },
]


plain_fire_art = """
⠀⠀⠀⠀⠀⠀⢱⣆⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⣿⣷⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢸⣿⣿⣷⣧⠀⠀⠀
⠀⠀⠀⠀⡀⢠⣿⡟⣿⣿⣿⡇⠀⠀
⠀⠀⠀⠀⣳⣼⣿⡏⢸⣿⣿⣿⢀⠀
⠀⠀⠀⣰⣿⣿⡿⠁⢸⣿⣿⡟⣼⡆
⢰⢀⣾⣿⣿⠟⠀⠀⣾⢿⣿⣿⣿⣿
⢸⣿⣿⣿⡏⠀⠀⠀⠃⠸⣿⣿⣿⡿
⢳⣿⣿⣿⠀⠀⠀⠀⠀⠀⢹⣿⡿⡁
⠀⠹⣿⣿⡄⠀⠀⠀⠀⠀⢠⣿⡞⠁
⠀⠀⠈⠛⢿⣄⠀⠀⠀⣠⠞⠋⠀⠀
⠀⠀⠀⠀⠀⠀⠉⠀⠀⠀⠀⠀⠀⠀
"""
 
coloured_fire_art = """
[white]⠀⠀⠀⠀⠀⠀⢱⣆⠀⠀⠀⠀⠀⠀[/white]
[white]⠀⠀⠀⠀⠀⠀⠈[/white][orange1]⣿⣷⡀[/orange1][white]⠀⠀⠀⠀[/white]
[orange1]⠀⠀⠀⠀⠀⠀⢸⣿⣿⣷⣧⠀⠀⠀[/orange1]
[orange1]⠀⠀⠀⠀⡀⢠⣿⡟[/orange1][yellow1]⣿⣿[/yellow1][orange1]⣿⡇⠀⠀[/orange1]
[orange1]⠀⠀⠀⠀⣳⣼⣿⡏[/orange1][yellow1]⢸⣿[/yellow1][orange1]⣿⣿⢀⠀[/orange1]
[orange1]⠀⠀⠀⣰⣿⣿⡿⠁[/orange1][yellow1]⢸⣿[/yellow1][orange1]⣿⡟⣼⡆[/orange1]
[red]⢰⢀⣾⣿⣿⠟⠀⠀[/red][orange1]⣾⢿[/orange1][yellow1]⣿⣿[/yellow1][orange1]⣿⣿[/orange1]
[red]⢸⣿⣿⣿⡏⠀⠀⠀[/red][orange1]⠃⠸[/orange1][yellow1]⣿⣿[/yellow1][orange1]⣿⡿[/orange1]
[red]⢳⣿⣿⣿⠀⠀⠀⠀[/red][orange1]⠀⠀[/orange1][yellow1]⢹⣿[/yellow1][orange1]⡿⡁[/orange1]
[red]⠀⠹⣿⣿⡄⠀⠀⠀⠀⠀[/red][orange1]⢠[/orange1][yellow1]⣿⡞[/yellow1][orange1]⠁[/orange1]
[red]⠀⠀⠈⠛⢿⣄⠀⠀⠀⣠⠞⠋⠀⠀[/red]
[red]⠀⠀⠀⠀⠀⠀⠉⠀⠀⠀⠀⠀⠀⠀[/red]
"""
 
 
def format_website_url(website):
    website = website.strip()
 
    if website == "":
        return ""
 
    if not website.startswith("http://") and not website.startswith("https://"):
        website = "https://" + website
 
    return website

def format_website_list_text(websites):
    return "\n".join(clean_website_list(websites))

def get_subject_website_list(data, subject):
    return clean_website_list(data.get("subject_websites", {}).get(str(subject), []))

def get_subject_topic_list(data, subject):
    return clean_topic_list(data.get("subject_topics", {}).get(str(subject), []))

def format_topic_list_text(topics):
    return "\n".join(clean_topic_list(topics))

def get_topic_options(data, subject):
    topics = get_subject_topic_list(data, subject)
    return [(topic, topic) for topic in topics]

def get_optional_topic_options(data, subject):
    return [("No topic", NO_TOPIC_VALUE), *get_topic_options(data, subject)]
 
def calculate_current_streak(data):
    study_dates = set(data.get("streak_days", []))
 
    current_day = date.today()
    streak_count = 0
 
    while str(current_day) in study_dates:
        streak_count += 1
        current_day = current_day - timedelta(days=1)
 
    return streak_count
 
 
def calculate_today_minutes(data):
    today_date = str(date.today())
    total_minutes = 0
 
    for session in data["sessions"]:
        if session["date"] == today_date:
            total_minutes += session["minutes"]
 
    return total_minutes
 
 
def calculate_today_sessions(data):
    today_date = str(date.today())
    total_sessions = 0
 
    for session in data["sessions"]:
        if session["date"] == today_date:
            total_sessions += 1
 
    return total_sessions
 
 
def calculate_weekly_minutes(data):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
 
    total_minutes = 0
 
    for session in data["sessions"]:
        session_date = date.fromisoformat(session["date"])
 
        if start_of_week <= session_date <= today:
            total_minutes += session["minutes"]
 
    return total_minutes
 
 
def create_progress_bar(current, goal, length=20):
    if goal <= 0:
        return "[--------------------] 0%"
 
    progress = current / goal
 
    if progress > 1:
        progress = 1
 
    filled_length = int(progress * length)
    empty_length = length - filled_length
 
    bar = "#" * filled_length + "-" * empty_length
    percentage = int(progress * 100)
 
    return f"[{bar}] {percentage}%"
 
 
def get_weekly_goal_status(current, goal):
    if current >= goal:
        return "[green]Completed[/green]"
 
    return "[bold #0b7a39]Keep going[/bold #0b7a39]"

def get_weekly_goal_nudge(current, goal):
    if goal <= 0:
        return "Set a weekly goal to get a study pace suggestion."

    remaining_minutes = max(0, goal - current)

    if remaining_minutes == 0:
        return "Goal complete. Extra study now builds a buffer for future weeks."

    today = date.today()
    days_left = max(1, 7 - today.weekday())
    minutes_per_day = (remaining_minutes + days_left - 1) // days_left
    return f"{remaining_minutes} min left this week. Aim for about {minutes_per_day} min/day."
 
 
def has_studied_today(data):
    today_date = str(date.today())
    return today_date in data.get("streak_days", [])
 
 
def get_recent_sessions(data, limit=5):
    sessions = data["sessions"]
 
    if len(sessions) == 0:
        return (
            "[bold]Recent Sessions[/bold]\n"
            "No sessions yet.\n"
            "Next: open Log Session or Focus Mode to record your first study block."
        )
 
    recent_sessions = sessions[-limit:]
    recent_sessions.reverse()
 
    lines = ["[bold]Recent Sessions[/bold]", "Subject       Time     Date"]
 
    for session in recent_sessions:
        subject = session["subject"]
        topic = session.get("topic", "")
        minutes = session["minutes"]
        session_date = session["date"]
        subject_text = subject if topic == "" else f"{subject}: {topic}"
        lines.append(f"{subject_text[:20].ljust(20)} {str(minutes).rjust(4)} min  {session_date}")

    tiny_sessions = [
        session for session in sessions[-8:]
        if session.get("minutes", 0) <= 2
    ]

    if len(tiny_sessions) >= 2:
        lines.append("")
        lines.append(
            "[yellow]Pattern spotted:[/yellow] several tiny sessions. "
            "Try one focused 25-35 minute block."
        )
 
    return "\n".join(lines)

def format_minutes_label(minutes):
    minutes = max(0, int(minutes))

    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    remaining = minutes % 60

    if remaining == 0:
        return f"{hours}h"

    return f"{hours}h {remaining}m"

def get_subject_minutes_this_week(data):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    totals = {}

    for session in data.get("sessions", []):
        try:
            session_date = date.fromisoformat(session.get("date", ""))
        except ValueError:
            continue

        if start_of_week <= session_date <= today:
            subject = session.get("subject", "unknown")
            totals[subject] = totals.get(subject, 0) + session.get("minutes", 0)

    return totals

def get_today_subject_totals(data):
    today_text = str(date.today())
    totals = {}

    for session in data.get("sessions", []):
        if session.get("date") != today_text:
            continue

        subject = session.get("subject", "unknown")
        totals[subject] = totals.get(subject, 0) + session.get("minutes", 0)

    return totals

def get_most_common_subject(sessions):
    counts = {}

    for session in sessions:
        subject = session.get("subject")

        if subject:
            counts[subject] = counts.get(subject, 0) + 1

    if not counts:
        return None

    return max(counts.items(), key=lambda item: item[1])[0]

def get_due_review_items(data, limit=3):
    today_text = str(date.today())
    due_items = []

    for item in data.get("review_items", []):
        next_due = str(item.get("next_due", ""))

        if next_due and next_due <= today_text:
            due_items.append(item)

    due_items.sort(key=lambda item: str(item.get("next_due", "")))
    return due_items[:limit]

def get_next_best_action(data):
    subjects = data.get("subjects", [])
    sessions = data.get("sessions", [])
    weekly_goal = data.get("weekly_goal", 300)
    weekly_minutes = calculate_weekly_minutes(data)
    today_minutes = calculate_today_minutes(data)
    subject_week_totals = get_subject_minutes_this_week(data)
    due_reviews = get_due_review_items(data, limit=1)

    if due_reviews:
        item = due_reviews[0]
        subject = item.get("subject", "Choose a subject")
        topic = item.get("topic", "Due review")
        return {
            "subject": subject,
            "topic": topic,
            "method": "Retrieval practice",
            "target_minutes": 25,
            "reason": f"{topic} is due for review today.",
        }

    today_text = str(date.today())
    tiny_today = [
        session for session in sessions
        if session.get("date") == today_text and session.get("minutes", 0) <= 2
    ]

    if len(tiny_today) >= 2:
        subject = get_most_common_subject(tiny_today) or get_most_common_subject(sessions)
        topic = (get_subject_topic_list(data, subject) or ["Core practice block"])[0]
        return {
            "subject": subject or "Choose a subject",
            "topic": topic,
            "method": "Past-paper questions + error correction",
            "target_minutes": 35,
            "reason": "Several tiny sessions today. Try one focused block.",
        }

    if weekly_goal > 0:
        days_left = max(1, 7 - date.today().weekday())
        remaining_minutes = max(0, weekly_goal - weekly_minutes)
        daily_target = (remaining_minutes + days_left - 1) // days_left

        if today_minutes < daily_target and remaining_minutes > 0:
            if subject_week_totals:
                subject = min(subject_week_totals.items(), key=lambda item: item[1])[0]
            elif subjects:
                subject = subjects[0]
            else:
                subject = "Choose a subject"

            return {
                "subject": subject,
                "topic": (get_subject_topic_list(data, subject) or ["Weekly goal progress"])[0],
                "method": "Focused study block",
                "target_minutes": max(25, min(35, daily_target)),
                "reason": f"Aim for about {daily_target} min/day to hit this week's goal.",
            }

    if subjects:
        if subject_week_totals:
            subject = min(subject_week_totals.items(), key=lambda item: item[1])[0]
            reason = "This is one of your least-studied subjects this week."
        elif sessions:
            subject = sessions[-1].get("subject", subjects[0])
            reason = "Continue from your most recent subject."
        else:
            subject = subjects[0]
            reason = "Start building your first real study block."

        return {
            "subject": subject,
            "topic": (get_subject_topic_list(data, subject) or ["Next useful block"])[0],
            "method": "Retrieval practice",
            "target_minutes": 25,
            "reason": reason,
        }

    return {
        "subject": "Choose a subject",
        "topic": "First setup step",
        "method": "Create a subject, then start a 25-minute focus session",
        "target_minutes": 25,
        "reason": "No study subject exists yet.",
    }

def get_review_queue_display(data):
    due_reviews = get_due_review_items(data)
    todo_items = [
        item for item in data.get("todo_items", [])
        if not item.get("done", False)
    ]
    lines = ["[bold]Todo / Review[/bold]"]

    if todo_items:
        lines.append("[bold cyan]Todo[/bold cyan]")

        for item in todo_items[:4]:
            lines.append(f"[ ] {str(item.get('text', 'Untitled task'))[:34]}")

        if len(todo_items) > 4:
            lines.append(f"+ {len(todo_items) - 4} more in the browser overlay")

    if not due_reviews:
        if not todo_items:
            lines.extend([
                "No todo tasks yet.",
                "Add tasks in the browser extension to sync them here.",
            ])
        return "\n".join(lines)

    if todo_items:
        lines.append("")

    lines.append("[bold cyan]Review[/bold cyan]")

    for index, item in enumerate(due_reviews, start=1):
        topic = str(item.get("topic", "Untitled topic"))[:22]
        subject = str(item.get("subject", "unknown"))[:14]
        lines.append(f"{index}. {topic.ljust(22)} {subject}")

    lines.append("[bold]R[/bold] start top review")

    return "\n".join(lines)

def get_focus_readiness_display(data, server_token):
    focus_sessions = data.get("focus_quality_sessions", [])
    subject_websites = data.get("subject_websites", {})
    saved_website_sets = sum(1 for websites in subject_websites.values() if websites)
    extension_status = "[green]ready[/green]" if focus_sessions or server_token else "[yellow]connect account[/yellow]"
    shield_status = "[green]active[/green]" if saved_website_sets else "[yellow]save websites[/yellow]"
    latest_score = "none"
    latest_distraction = "none"

    if focus_sessions:
        latest = focus_sessions[0]
        latest_score = f"{latest.get('score', 0)}%"
        latest_distraction = latest.get("top_distracted_domain", "none")

    lines = [
        "[bold]Focus Readiness[/bold]",
        f"Extension: {extension_status}",
        f"Blocked sites: {shield_status}",
        "Current mode: Custom / Pomodoro",
        f"Last focus quality: {latest_score}",
        f"Last distraction: {latest_distraction}",
    ]

    return "\n".join(lines)

def get_todays_wins_display(data):
    today_minutes = calculate_today_minutes(data)
    today_sessions = calculate_today_sessions(data)
    protected = "Yes" if has_studied_today(data) else "No"
    today_totals = get_today_subject_totals(data)
    best_subject = "none"

    if today_totals:
        best_subject = max(today_totals.items(), key=lambda item: item[1])[0]

    if today_minutes == 0:
        encouragement = "One focused block changes the day."
    elif today_minutes < 25:
        encouragement = "Good start. Make the next block count."
    else:
        encouragement = "Solid progress. Keep the chain alive."

    return "\n".join([
        "[bold]Today's Wins[/bold]",
        f"{format_minutes_label(today_minutes)} studied",
        f"{today_sessions} session(s) completed",
        f"Streak protected: {protected}",
        f"Best subject: {best_subject}",
        encouragement,
    ])

def get_weak_topics_display(data):
    due_reviews = get_due_review_items(data)
    subject_week_totals = get_subject_minutes_this_week(data)
    subjects = data.get("subjects", [])
    sessions = data.get("sessions", [])
    weak_items = []

    for item in due_reviews:
        weak_items.append(
            f"{item.get('subject', 'unknown')}: {item.get('topic', 'review due')}"
        )

    today_text = str(date.today())
    tiny_today = [
        session for session in sessions
        if session.get("date") == today_text and session.get("minutes", 0) <= 2
    ]

    if len(tiny_today) >= 2:
        subject = get_most_common_subject(tiny_today) or "recent study"
        weak_items.append(f"{subject}: needs one longer block")

    for subject in subjects:
        if subject_week_totals.get(subject, 0) == 0:
            weak_items.append(f"{subject}: not studied this week")

    if not weak_items:
        weak_items.append("No weak topics spotted yet.")
        weak_items.append("Log topics after sessions to improve this.")

    lines = ["[bold]Weak Topics[/bold]"]

    for item in weak_items[:3]:
        lines.append(item)

    return "\n".join(lines)

def get_home_status_card(data, logged_in, server_online, server_token):
    streak_count = calculate_current_streak(data)
    weekly_minutes = calculate_weekly_minutes(data)
    weekly_goal = data.get("weekly_goal", 300)
    weekly_progress_bar = create_progress_bar(weekly_minutes, weekly_goal)

    if server_online is True:
        server_status = "Connected"
    elif server_online is False:
        server_status = "Offline"
    else:
        server_status = "Checking"

    sync_status = "Synced" if server_token is not None else "Local only"
    account_status = "Logged in" if logged_in else "Not logged in"

    return "\n".join([
        "[bold white]StudyStreak[/bold white]",
        f"Account: {account_status}   Server: {server_status}   Sync: {sync_status}   Streak: {streak_count}d",
        f"Week goal: {weekly_minutes} / {weekly_goal} min   Progress: {weekly_progress_bar}",
    ])

def get_home_action_card(data):
    recommendation = get_next_best_action(data)

    return "\n".join([
        "[bold white]NEXT BEST ACTION[/bold white]",
        f"Study: {recommendation['subject']} - {recommendation['topic']}",
        f"Method: {recommendation['method']}",
        f"Target: {recommendation['target_minutes']} min",
        f"Why: {recommendation['reason']}",
    ])
 
 
def get_session_options(data):
    sessions = data["sessions"]
 
    options = []
 
    for index, session in enumerate(sessions):
        subject = session["subject"]
        topic = session.get("topic", "")
        minutes = session["minutes"]
        session_date = session["date"]
        note_marker = " + note" if session.get("note") else ""

        subject_text = subject if topic == "" else f"{subject} / {topic}"
        label = f"{session_date} - {subject_text} - {minutes} min{note_marker}"
        options.append((label, str(index)))
 
    options.reverse()
 
    return options
 
 
def get_subject_options(data):
    subjects = data["subjects"]
 
    options = []
 
    for subject in subjects:
        options.append((subject, subject))
 
    return options
 

def get_day_options():
    #get timetable day options
    return [
        ("Mon", "Mon"),
        ("Tue", "Tue"),
        ("Wed", "Wed"),
        ("Thu", "Thu"),
        ("Fri", "Fri"),
        ("Sat", "Sat"),
        ("Sun", "Sun"),
    ]


def normalise_timetable_day(day):
    #turn full day names into short names
    day_map = {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun",
    }

    return day_map.get(day, day)


def get_today_short_name():
    #get today's short day name
    return date.today().strftime("%a")

def get_timetable_session_options(data):
    options = []

    for index, item in enumerate(data.get("timetable", [])):
        subject = item["subject"].title()
        day = normalise_timetable_day(item["day"])
        start_time = item["start_time"]
        end_time = get_timetable_end_time(start_time, item["minutes"])

        label = f"{day} {start_time} - {end_time} | {subject}"
        options.append((label, str(index)))
    return options

def get_timetable_end_time(start_time, minutes):
    start_hour = int(start_time[:2])
    start_minute = int(start_time[3:])

    total_minutes = start_hour * 60 + start_minute + minutes
    crosses_midnight = total_minutes >= 24 * 60
    
    end_hour = (total_minutes // 60) % 24
    end_minute = total_minutes % 60
    end_time = f"{end_hour:02}:{end_minute:02}"

    if crosses_midnight:
        return f"{end_time} (+1 day)"
    
    return end_time
 

def get_timetable_grid(data):
    timetable = data.get("timetable", [])
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_name = get_today_short_name()

    sessions_by_day = {day: [] for day in days}

    for item in timetable:
        day = normalise_timetable_day(item["day"])

        if day in sessions_by_day:
            sessions_by_day[day].append(item)

    lines = ["[bold]Weekly Timetable[/bold]", ""]

    for day in days:
        if day == today_name:
            lines.append(f"[bold cyan]{day} - Today[/bold cyan]")
        else:
            lines.append(f"[bold]{day}[/bold]")

        day_sessions = sessions_by_day[day]
        day_sessions.sort(key=lambda item: item["start_time"])

        if len(day_sessions) == 0:
            lines.append("  [dim]No sessions planned[/dim]")
        else:
            for item in day_sessions:
                subject = item["subject"].title()
                start_time = item["start_time"]
                minutes = item["minutes"]
                end_time = get_timetable_end_time(start_time, minutes)

                lines.append(
                    f"  {start_time} - {end_time}  "
                    f"{subject.ljust(20)} "
                    f"{minutes} min"
                )

        lines.append("")

    return "\n".join(lines)


def get_today_timetable_display(data):
    #show today's timetable as list
    timetable = data.get("timetable", [])
    today_name = get_today_short_name()

    today_items = [
        item for item in timetable
        if normalise_timetable_day(item["day"]) == today_name
    ]

    if len(today_items) == 0:
        return (
            f"No timetable sessions planned for {today_name}.\n"
            "Next: use Add Session to plan your next study block."
        )

    today_items.sort(key=lambda item: item["start_time"])

    lines = [f"[bold]{today_name} Sessions[/bold]"]

    for item in today_items:
        subject = item["subject"]
        start_time = item["start_time"]
        minutes = item["minutes"]

        lines.append(f"{start_time} - {subject} - {minutes} minutes")

    return "\n".join(lines)


def get_subject_stats(data):
    sessions = data["sessions"]
    focus_sessions = data.get("focus_quality_sessions", [])

    subject_total = {}
    subject_weekly_total = {}
    subject_days = {}
    current_week_start = date.today() - timedelta(days=date.today().weekday())

    for session in sessions:
        subject = session["subject"]
        minutes = session["minutes"]
        session_day = date.fromisoformat(session["date"])

        if subject not in subject_total:
            subject_total[subject] = 0

        subject_total[subject] += minutes
        subject_days.setdefault(subject, {})
        subject_days[subject][session["date"]] = subject_days[subject].get(session["date"], 0) + minutes

        if current_week_start <= session_day <= date.today():
            subject_weekly_total[subject] = subject_weekly_total.get(subject, 0) + minutes

    focus_by_subject = {}

    for session in focus_sessions:
        subject = session.get("subject", "unknown")
        focused_seconds = session.get("focused_seconds", 0)
        score = session.get("score", 0)
        top_distraction = session.get("top_distracted_domain", "none")

        if subject not in focus_by_subject:
            focus_by_subject[subject] = {
                "sessions": 0,
                "focused_seconds": 0,
                "total_score": 0,
                "distractions": {},
            }

        focus_by_subject[subject]["sessions"] += 1
        focus_by_subject[subject]["focused_seconds"] += focused_seconds
        focus_by_subject[subject]["total_score"] += score
        if top_distraction and top_distraction != "none":
            focus_by_subject[subject]["distractions"][top_distraction] = (
                focus_by_subject[subject]["distractions"].get(top_distraction, 0) + 1
            )

    lines = ["[bold]Subject Stats[/bold]"]

    if len(subject_total) == 0 and len(focus_by_subject) == 0:
        return (
            "[bold]Subject Stats[/bold]\n"
            "No subject stats yet.\n"
            "Next: log a session or sync a Chrome focus session."
        )

    all_subjects = sorted(set(subject_total) | set(focus_by_subject))

    for subject in all_subjects:
        total_minutes = subject_total.get(subject, 0)
        hours = total_minutes // 60
        remaining_minutes = total_minutes % 60

        if hours > 0:
            time_text = f"{hours}h {remaining_minutes}m"
        else:
            time_text = f"{remaining_minutes}m"

        weekly_minutes = subject_weekly_total.get(subject, 0)
        best_day = "none"

        if subject_days.get(subject):
            best_day = max(
                subject_days[subject].items(),
                key=lambda item: item[1],
            )[0]

        lines.append(f"[bold]{subject}[/bold]")
        lines.append(f"  Total: {time_text}")
        lines.append(f"  This week: {weekly_minutes}m")
        lines.append(f"  Best study day: {best_day}")

        topics = get_subject_topic_list(data, subject)

        if topics:
            lines.append(f"  Topics: {', '.join(topics[:4])}")

        focus_stats = focus_by_subject.get(subject)

        if focus_stats:
            focus_minutes = focus_stats["focused_seconds"] // 60
            average_score = focus_stats["total_score"] // focus_stats["sessions"]
            top_distraction = "none"

            if focus_stats["distractions"]:
                top_distraction = max(
                    focus_stats["distractions"].items(),
                    key=lambda item: item[1],
                )[0]

            lines.append(
                f"  Focus quality: {average_score}% average, {focus_minutes}m focused"
            )
            lines.append(f"  Most common distraction: {top_distraction}")
        lines.append("")

    return "\n".join(lines)

def get_installed_version():
    try:
        return package_version("studystreak")
    except PackageNotFoundError:
        return "local"

def version_tuple(version_text):
    parts = []

    for part in str(version_text).split("."):
        digits = "".join(character for character in part if character.isdigit())
        parts.append(int(digits) if digits else 0)

    while len(parts) < 3:
        parts.append(0)

    return tuple(parts[:3])

def version_is_newer(latest_version, installed_version):
    if installed_version == "local":
        return False

    return version_tuple(latest_version) > version_tuple(installed_version)

def get_update_status_display(data):
    update_check = data.get("update_check", {})
    installed_version = update_check.get("installed_version") or get_installed_version()
    latest_version = update_check.get("latest_version")
    last_checked = update_check.get("last_checked")
    last_error = update_check.get("last_error")

    lines = [
        f"[bold]Installed version:[/bold] {installed_version}",
    ]

    if last_error:
        lines.append(f"[bold]Last check:[/bold] [red]Failed[/red] - {last_error}")
        return "\n".join(lines)

    if latest_version:
        if update_check.get("update_available"):
            lines.append(f"[bold]Latest PyPI version:[/bold] [yellow]{latest_version}[/yellow]")
            lines.append("[yellow]Update with: pip install --upgrade studystreak[/yellow]")
        else:
            lines.append(f"[bold]Latest PyPI version:[/bold] [green]{latest_version}[/green]")
            lines.append("[green]StudyStreak is up to date.[/green]")
    else:
        lines.append("[yellow]Press Check for Updates to compare with PyPI.[/yellow]")

    if last_checked:
        lines.append(f"[bold]Last checked:[/bold] {last_checked}")

    return "\n".join(lines)

def get_extension_status_display(data, server_token):
    subjects = data.get("subjects", [])
    subject_websites = data.get("subject_websites", {})
    website_sets = sum(1 for websites in subject_websites.values() if websites)
    timetable = data.get("timetable", [])
    focus_sessions = data.get("focus_quality_sessions", [])
    latest_focus = focus_sessions[0].get("completed_at", "none") if focus_sessions else "none"
    sync_ready = "[green]Ready[/green]" if server_token is not None else "[yellow]Log in online first[/yellow]"

    return "\n".join([
        f"[bold]Cloud sync:[/bold] {sync_ready}",
        f"[bold]Subjects synced:[/bold] {len(subjects)}",
        f"[bold]Subject website sets:[/bold] {website_sets}",
        f"[bold]Timetable reminders:[/bold] {len(timetable)}",
        f"[bold]Chrome/Firefox focus summaries:[/bold] {len(focus_sessions)}",
        f"[bold]Latest focus sync:[/bold] {latest_focus}",
        "",
        "[bold]Chrome:[/bold] load the chrome_extension folder in chrome://extensions.",
        "[bold]Firefox/Zen:[/bold] use the signed add-on or build dist/firefox_extension.",
    ])

def get_privacy_display(data):
    focus_count = len(data.get("focus_quality_sessions", []))
    session_count = len(data.get("sessions", []))
    subject_count = len(data.get("subjects", []))
    sync_data = data.get("sync", {})

    return "\n".join([
        f"[bold]Study sessions:[/bold] {session_count}",
        f"[bold]Subjects:[/bold] {subject_count}",
        f"[bold]Focus-quality summaries:[/bold] {focus_count}",
        f"[bold]Last cloud sync:[/bold] {sync_data.get('last_cloud_sync') or 'never'}",
        "",
        "Export Data saves a JSON copy to the StudyStreak data folder.",
        "Clear Focus Quality removes browser focus summaries from this device.",
        "Reset Local Study Data clears this profile on this device only.",
    ])

def should_offer_setup_tour(data):
    onboarding = data.get("onboarding", {})

    if onboarding.get("tour_completed") or onboarding.get("tour_declined"):
        return False

    return (
        len(data.get("subjects", [])) == 0
        and len(data.get("sessions", [])) == 0
        and len(data.get("timetable", [])) == 0
    )
 
def is_blank_select_value(value):
    return (
        value is None
        or value is False
        or str(value).lower() in [
            "",
            "none",
            "null",
            "select.null",
            "select.blank",
            NO_TOPIC_VALUE,
        ]
    )

def get_select_index(value):
    if is_blank_select_value(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def calculate_total_minutes(data):
    return sum(session.get("minutes", 0 ) for session in data.get("sessions", []))

def has_focus_session(data):
    for session in data.get("sessions", []):
        if session.get("source") == "focus":
            return True

    return False

def format_focus_quality_time(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes <= 0:
        return f"{remaining_seconds}s"

    return f"{minutes}m {remaining_seconds}s"

def format_countdown_time(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"

def format_focus_countdown_display(seconds_left, phase):
    timer_text = format_countdown_time(seconds_left)
    phase_text = phase.upper()
    return (
        "\n\n\n\n"
        f"[bold white]{timer_text}[/]\n"
        "\n"
        f"[bold white]{phase_text}[/]\n"
        "\n\n"
    )

def get_focus_quality_summary(data):
    sessions = data.get("focus_quality_sessions", [])

    if len(sessions) == 0:
        return (
            "No Chrome focus summaries yet.\n"
            "Next: stop a Chrome focus session online, or import signed JSON as a fallback."
        )

    latest_session = sessions[0]
    return (
        "[bold]Latest Chrome focus summary[/bold]\n"
        f"Score: {latest_session.get('score', 0)}%\n"
        f"Focused: {format_focus_quality_time(latest_session.get('focused_seconds', 0))}\n"
        f"Distracted: {format_focus_quality_time(latest_session.get('distracted_seconds', 0))}\n"
        f"Idle: {format_focus_quality_time(latest_session.get('idle_seconds', 0))}\n"
        f"Top distraction: {latest_session.get('top_distracted_domain', 'none')}\n"
        f"Imported summaries: {len(sessions)}"
    )


def format_setup_item(done, name, next_step):
    status = "[green]Done[/green]" if done else "[bold #005f87]Next[/bold #005f87]"
    if done:
        return f"{status} - {name}"

    return f"{status} - {name}: {next_step}"


def get_setup_checklist(data, logged_in, server_online, server_token):
    subjects = data.get("subjects", [])
    subject_websites = data.get("subject_websites", {})
    has_subject_websites = any(subject_websites.get(subject) for subject in subject_websites)
    has_any_session = len(data.get("sessions", [])) > 0
    has_timetable = len(data.get("timetable", [])) > 0
    has_chrome_data = len(data.get("focus_quality_sessions", [])) > 0
    cloud_ready = server_token is not None and server_online is not False

    items = [
        (logged_in, "Account", "log in or create an account."),
        (cloud_ready, "Cloud sync", "connect to the server so your data can sync."),
        (len(subjects) > 0, "Subjects", "add subjects in Settings > Subjects."),
        (has_subject_websites, "Subject websites", "save allowed websites for each subject."),
        (has_timetable, "Timetable", "add your first planned session."),
        (has_any_session, "First study session", "log a session or complete Focus Mode."),
        (has_chrome_data, "Chrome focus data", "use the Chrome extension and stop a focus session."),
    ]

    incomplete_items = [
        format_setup_item(done, name, next_step)
        for done, name, next_step in items
        if not done
    ]

    if len(incomplete_items) == 0:
        return (
            "[bold]Setup checklist[/bold]\n"
            "[green]Done[/green] - StudyStreak is fully set up on this device."
        )

    return "\n".join([
        "[bold]Setup checklist[/bold]",
        *incomplete_items[:5],
    ])

#show health
def get_setup_health_display(data, logged_in, server_online, server_token):
    sync_data = data.get("sync", {})
    last_sync_error = sync_data.get("last_sync_error")
    last_cloud_sync = sync_data.get("last_cloud_sync")
    subjects = data.get("subjects", [])
    timetable = data.get("timetable", [])
    focus_sessions = data.get("focus_quality_sessions", [])

    if server_online is True:
        server_status = "[green]Connected[/green]"
    elif server_online is False:
        server_status = "[red]Offline[/red]"
    else:
        server_status = "[yellow]Checking[/yellow]"

    if last_sync_error:
        sync_status = f"[red]Failed[/red] - {last_sync_error}"
    elif last_cloud_sync:
        sync_status = "[green]Synced[/green]"
    else:
        sync_status = "[yellow]Not synced yet[/yellow]"

    account_status = "[green]Logged in[/green]" if logged_in else "[yellow]Login needed[/yellow]"
    cloud_status = "[green]Ready[/green]" if server_token is not None else "[yellow]Not logged in online[/yellow]"

    return "\n".join([
        f"[bold]Account:[/bold] {account_status}",
        f"[bold]Server:[/bold] {server_status}",
        f"[bold]Cloud login:[/bold] {cloud_status}",
        f"[bold]Sync:[/bold] {sync_status}",
        f"[bold]Subjects:[/bold] {len(subjects)}",
        f"[bold]Subject website sets:[/bold] {len(data.get('subject_websites', {}))}",
        f"[bold]Timetable sessions:[/bold] {len(timetable)}",
        f"[bold]Chrome focus summaries:[/bold] {len(focus_sessions)}",
        f"[bold]Data folder:[/bold] {get_app_data_dir()}",
    ])

ACHIEVEMENTS = [
    {
        "id": "first-session",
        "name": "First Steps",
        "description": "Log your first study session.",
        "condition": lambda data: len(data.get("sessions", [])) >= 1,
    },
    {
        "id": "ten-minutes",
        "name": "Tiny Grind",
        "description": "Study for 10 minutes total.",
        "condition": lambda data: calculate_total_minutes(data) >= 10,
    },
    {
        "id": "one-hour",
        "name": "One Hour Club",
        "description": "Study for 60 minutes total.",
        "condition": lambda data: calculate_total_minutes(data) >= 60
    },
    {
        "id": "three-day-streak",
        "name": "Three Day Streak",
        "description": "Reach a 3 day study streak.",
        "condition": lambda data: calculate_current_streak(data) >= 3,
    },
    {
        "id": "subject-collector",
        "name": "Subject Collector",
        "description": "Add 3 subjects.",
        "condition": lambda data: len(data.get("subjects", [])) >= 3,
    },
    {
        "id": "focused",
        "name": "Focused",
        "description": "Complete your first focus session",
        "condition": lambda data: has_focus_session(data),
    },
    {
        "id": "planner",
        "name": "Planner",
        "description": "Add your first timetable session.",
        "condition": lambda data: len(data.get("timetable", [])) >= 1,
    },
]

def get_achievement_display(data):
    unlocked_ids = set(data.get("achievements", {}).get("unlocked", []))
    lines = [f"[bold]Achievements[/bold] {len(unlocked_ids)} / {len(ACHIEVEMENTS)} unlocked", ""]

    for achievement in ACHIEVEMENTS:
        if achievement["id"] in unlocked_ids:
            status = "[green]Unlocked[/green]"
        else:
            status = "[dim]Locked[/dim]"

        lines.append(
            f"{status} - [bold]{achievement['name']}[/bold]\n"
            f"  {achievement['description']}"
        )

    return "\n\n".join(lines)


class AchievementEffectScreen(ModalScreen):
    def __init__(self, achievement, remaining_achievements=None):
        super().__init__()
        self.achievement = achievement
        self.remaining_achievements = remaining_achievements or []
    
    def compose(self) -> ComposeResult:
        with Container(id="achievement-effect-box"):
            yield Static("[bold yellow]Achievement unlocked[/bold yellow]", id="achievement-effect-title")
            yield Static(
                f"[bold]{self.achievement['name']}[/bold]",
                id="achievement-effect-name",
            )
            yield Static(
                self.achievement["description"],
                id="achievement-effect-message",
            )
    
    def on_mount(self):
        self.set_timer(0.35, self.app.play_achievement_sound)
        self.set_timer(3, self.close_effect)

    def close_effect(self):
        self.app.pop_screen()

        if len(self.remaining_achievements) > 0:
            self.app.call_later(
                lambda: self.app.show_achievement_effect(self.remaining_achievements)
            )

class StreakEffectScreen(ModalScreen):
    def __init__(self, streak_count):
        super().__init__()
        self.streak_count = streak_count
 
    def compose(self) -> ComposeResult:
        with Container(id="streak-effect-box"):
            yield Static(coloured_fire_art, id="streak-fire")
            yield Static(
                f"[bold orange1]Streak protected: {self.streak_count} days[/bold orange1]",
                id="streak-effect-title",
            )
            yield Static(
                "[green]Your first study session today has been logged.[/green]",
                id="streak-effect-message",
            )


    def on_mount(self):
        self.set_timer(2.5, self.close_effect)
 
    def close_effect(self):
        self.app.pop_screen()
 
 
class FocusSessionScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Container(id="focus-overlay"):
            with Vertical(id="focus-overlay-content"):
                yield Static("", id="focus-overlay-timer")
                with Horizontal(id="focus-overlay-buttons"):
                    yield Button("Open Website", id="focus-overlay-open-website-button")
                    yield Button("Stop Focus", id="focus-overlay-stop-button")

    def on_mount(self):
        self.update_display()
        self.query_one("#focus-overlay-stop-button", Button).focus()

    def update_display(self):
        self.query_one("#focus-overlay-timer", Static).update(
            self.app.get_focus_overlay_display()
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "focus-overlay-open-website-button":
            self.app.play_ui_sound()
            self.app.open_focus_websites(show_message=False)
            return

        if event.button.id == "focus-overlay-stop-button":
            self.app.play_ui_sound()
            self.app.cancel_focus_session()
            return


class FocusSessionNoteScreen(ModalScreen):
    def __init__(self, session_completed_at, subject, topic, minutes, topic_options):
        super().__init__()
        self.session_completed_at = session_completed_at
        self.subject = subject
        self.topic = topic
        self.minutes = minutes
        self.topic_options = [("No topic", NO_TOPIC_VALUE), *topic_options]

    def compose(self) -> ComposeResult:
        with Container(id="focus-note-modal"):
            yield Static("Session complete", id="focus-note-title")
            yield Static(
                f"{self.subject} - {self.topic or 'No topic'} - {self.minutes} min",
                id="focus-note-summary",
            )
            yield Select(
                options=self.topic_options,
                id="focus-note-topic-select",
                prompt="Choose topic (optional)",
            )
            yield TextArea("", id="focus-note-input")
            with Horizontal(id="focus-note-button-row"):
                yield Button("Save Review", id="save-focus-note-button")
                yield Button("Skip", id="skip-focus-note-button")

    def on_mount(self):
        topic_select = self.query_one("#focus-note-topic-select", Select)
        topic_values = {str(value) for _, value in self.topic_options}

        if self.topic and self.topic in topic_values:
            topic_select.value = self.topic

        self.query_one("#focus-note-input", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-focus-note-button":
            topic_value = self.query_one("#focus-note-topic-select", Select).value
            topic = "" if is_blank_select_value(topic_value) else str(topic_value)
            note = self.query_one("#focus-note-input", TextArea).text.strip()
            self.app.save_focus_session_note(self.session_completed_at, note, topic)
            self.app.pop_screen()
            return

        if event.button.id == "skip-focus-note-button":
            self.app.pop_screen()
            return


class DeleteSubjectConfirmScreen(ModalScreen):
    def __init__(self, subject):
        super().__init__()
        self.subject = subject
 
    def compose(self) -> ComposeResult:
        with Container(id="delete-subject-confirm-box"):
            yield Static(
                f"[bold red]Delete subject: {self.subject}?[/bold red]",
                id="delete-subject-confirm-title",
            )
 
            yield Static(
                "This will also delete all study sessions saved under this subject.",
                id="delete-subject-confirm-message",
            )
 
            with Horizontal(id="delete-subject-confirm-buttons"):
                yield Button("Cancel", id="cancel-delete-subject-button")
                yield Button("Delete", id="confirm-delete-subject-button")
 
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-delete-subject-button":
            self.app.pop_screen()
            return
 
        if event.button.id == "confirm-delete-subject-button":
            self.app.delete_subject_and_sessions(self.subject)
            self.app.pop_screen()
            return


class SetupTourPromptScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Container(id="setup-tour-prompt-box"):
            yield Static("[bold]Want a quick tour?[/bold]", id="setup-tour-prompt-title")
            yield Static(
                "StudyStreak can guide you through the real setup while you click around the app.",
                id="setup-tour-prompt-message",
            )
            with Horizontal(id="setup-tour-prompt-buttons"):
                yield Button("Start Tour", id="start-setup-tour-button")
                yield Button("Skip", id="skip-setup-tour-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-setup-tour-button":
            self.app.pop_screen()
            self.app.start_setup_tour()
            return

        if event.button.id == "skip-setup-tour-button":
            self.app.dismiss_setup_tour()
            self.app.pop_screen()
            return


class DataActionConfirmScreen(ModalScreen):
    def __init__(self, action_id, title, message, confirm_label):
        super().__init__()
        self.action_id = action_id
        self.title = title
        self.message = message
        self.confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Container(id="data-action-confirm-box"):
            yield Static(f"[bold red]{self.title}[/bold red]", id="data-action-confirm-title")
            yield Static(self.message, id="data-action-confirm-message")
            with Horizontal(id="data-action-confirm-buttons"):
                yield Button("Cancel", id="cancel-data-action-button")
                yield Button(self.confirm_label, id="confirm-data-action-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-data-action-button":
            self.app.pop_screen()
            return

        if event.button.id == "confirm-data-action-button":
            self.app.run_data_privacy_action(self.action_id)
            self.app.pop_screen()
            return
 
 
class StudyStreakApp(App):
 
    CSS_PATH = "app.tcss"
 
    BINDINGS = [
        ("escape", "escape_quit", "Quit"),
    ]
 
    last_escape_time = None
    focus_timer = None
    sync_status_timer = None
    loading_settings = False
    focus_seconds_left = 0
    focus_subject = None
    focus_topic = ""
    focus_websites = []
    focus_minutes = 0
    focus_mode = "manual"
    focus_overlay_screen = None
    pomodoro_phase = "work"
    pomodoro_completed_work_blocks = 0
    pomodoro_logged_minutes = 0
    logged_in = False
    temp_message_versions = {}
    leaderboard_period = "all"
    last_notified_sync_error = None
    editing_timetable_index = None
    chrome_sync_protected_streak = False
    server_is_online = None
    tour_active = False
    tour_step_index = 0
    checking_tour_progress = False
    suppress_next_tab_sound = False
 
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="login-container"):
            yield Static("Study >_ Streak", id="login-title")
            yield Static("Log in or create an account.", id="login-subtitle")

            yield Input(placeholder="Username", id="login-username-input")
            yield Input(placeholder="Password", id="login-password-input", password=True)
            yield Checkbox("Remember me", id="remember-me-checkbox")

            with Horizontal(id="login-button-row"):
                yield Button("Login", id="login-button")
                yield Button("Create Account", id="create-account-button")
            
            yield Static("", id="login-message")

        with Container(id="main-container"):
            yield Static("", id="server-status-label")
            yield Static("", id="sync-status-label")
            yield Static("Study >_ Streak", id="title")
            yield Static("Track your study streak and log your progress.", id="subtitle")

            with Horizontal(id="account-row"):
                yield Static("", id="account-label")
                yield Button("Logout", id="logout-button")

            with Container(id="tour-guide"):
                yield Static("", id="tour-guide-text")
                with Horizontal(id="tour-guide-buttons"):
                    yield Button("Take Me There", id="tour-go-button")
                    yield Button("Done", id="tour-done-button")
                    yield Button("Skip", id="tour-skip-button")
                    yield Button("End Tour", id="tour-end-button")

            with TabbedContent(initial="dashboard-tab", id="main-tabs"):
                with TabPane("Home", id="dashboard-tab"):
                    yield Static("", id="home-status-card")
                    yield Static("", id="home-action-card")
                    with Horizontal(id="home-action-buttons"):
                        yield Button("Enter  Prepare Focus", id="home-prepare-focus-button")
                        yield Button("F  Focus", id="home-open-focus-button")
                        yield Button("S  Skip", id="home-skip-action-button")
                    with Horizontal(id="home-card-row-one"):
                        yield Static("", id="home-focus-readiness-card")
                        yield Static("", id="home-review-card")
                    with Horizontal(id="home-card-row-two"):
                        yield Static("", id="home-wins-card")
                        yield Static("", id="home-weak-topics-card")
                    yield Static("", id="setup-checklist")
                    yield Static("", id="recent-sessions")
 
                with TabPane("Subjects", id="subject-stats-tab"):
                    yield Static("", id="subject-stats")
 
                with TabPane("Sessions", id="log-tab"):
                    yield Static("Sessions", id="sessions-title")

                    with Horizontal(id="sessions-layout"):
                        with Vertical(id="sessions-sidebar"):
                            yield Button("Log Session", id="sessions-log-tab-button")
                            yield Button("Edit Logs", id="sessions-manage-tab-button")

                        with Vertical(id="sessions-content"):
                            with Vertical(id="log-session-panel"):
                                yield Static("Log a study session.", id="log-title")

                                yield Select(
                                    options=[],
                                    id="subject-select",
                                    prompt="Choose a subject",
                                )

                                yield Select(
                                    options=[],
                                    id="log-topic-select",
                                    prompt="Topic (optional)",
                                )

                                yield Input(placeholder="Minutes, e.g. 30", id="minutes-input")
                                yield TextArea("", id="manual-session-note-input")

                                with Horizontal(id="button-row"):
                                    yield Button("Log Session", id="log-button")
                                    yield Button("Clear", id="clear-button")

                                yield Static("", id="message")

                            with Vertical(id="manage-session-panel"):
                                yield Static("Edit a study session.", id="manage-title")

                                yield Select(
                                    options=[],
                                    id="session-select",
                                    prompt="Choose a session",
                                )

                                yield Static("Choose a session to see its details.", id="session-details-preview")

                                yield Select(
                                    options=[],
                                    id="edit-session-subject-select",
                                    prompt="Subject",
                                )
                                yield Input(placeholder="Minutes", id="edit-session-minutes-input")
                                yield Input(placeholder="Topic (optional)", id="edit-session-topic-input")
                                yield TextArea("", id="edit-session-note-input")

                                with Horizontal(id="manage-button-row"):
                                    yield Button("Save Changes", id="save-session-edit-button")
                                    yield Button("Delete Selected", id="delete-selected-button")

                                yield Static("", id="manage-message")

                with TabPane("Timetable", id="timetable-tab"):
                    yield Static("Weekly study timetable", id="timetable-title")

                    with Horizontal(id="timetable-top-row"):
                        yield Button("Add Session", id="show-timetable-form-button")
                    
                    with Vertical(id="timetable-form-panel"):

                        yield Select(
                            options=[],
                            id="timetable-subject-select",
                            prompt="Choose a subject",
                        )
                    

                        yield Select(
                            options=get_day_options(),
                            id="timetable-day-select",
                            prompt="Choose a day",
                        )

                        yield Input(
                            placeholder="Start time, e.g. 17:00",
                            id="timetable-start-input",
                        )

                        yield Input(
                            placeholder="Duration in minutes, e.g. 60",
                            id="timetable-minutes-input",
                        )

                        with Horizontal(id="timetable-button-row"):
                            yield Button("Save Session", id="add-timetable-button")
                            yield Button("Cancel", id="hide-timetable-form-button")

                    yield Static("", id="timetable-message")
                    yield Static("", id="today-timetable")
                    yield Static("", id="timetable-grid")
                    yield Static("Manage Planned sessions", id="manage-timetable-title")

                    yield Select(
                        options=[],
                        id="manage-timetable-select",
                        prompt="Choose a planned session",
                    )

                    with Horizontal(id="manage-timetable-button-row"):
                        yield Button("Edit Selected", id="edit-timetable-button")
                        yield Button("Delete Selected", id="delete-timetable-button")

                with TabPane("Focus", id="focus-tab"):
                    yield Static("Start a focused study session.", id="focus-title")
 
                    yield Select(
                        options=[],
                        id="focus-subject-select",
                        prompt="Choose a subject",
                    )

                    yield Select(
                        options=[],
                        id="focus-topic-select",
                        prompt="Choose a topic (optional)",
                    )

                    yield Static("Focus websites", classes="field-hint")
                    yield TextArea(
                        "",
                        id="focus-website-input",
                    )
 
                    yield Input(
                        placeholder="Focus duration in minutes, e.g. 25",
                        id="focus-minutes-input",
                    )

                    yield Checkbox("Pomodoro 50/10", id="pomodoro-mode-checkbox")
 
                    with Horizontal(id="focus-button-row"):
                        yield Button("Open Website", id="open-website-button")
                        yield Button("Start Focus", id="start-focus-button")
                        yield Button("Cancel Focus", id="cancel-focus-button")
 
                    yield Static("", id="focus-timer")
                    yield Static("", id="focus-phase")
                    yield Static("", id="focus-message")

                with TabPane("Leaderboard", id="leaderboard-tab"):
                    yield Static("Server leaderboard", id="leaderboard-title")

                    with Horizontal(id="leaderboard-period-row"):
                        yield Button("Today", id="leaderboard-today-button")
                        yield Button("This week", id="leaderboard-week-button")
                        yield Button("All time", id="leaderboard-all-button")

                    with Horizontal(id="leaderboard-refresh-row"):
                        yield Button("Refresh Leaderboard", id="refresh-leaderboard-button")

                    yield Static("", id="leaderboard")

                with TabPane("Achievements", id="achievements-tab"):
                    yield Static("", id="achievements")

                with TabPane("Settings", id="settings-tab"):
                    yield Static("Settings", id="settings-title")
 
                    with Horizontal(id="settings-layout"):
                        with Vertical(id="settings-sidebar"):
                            yield Button("Weekly Goal", id="settings-weekly-button")
                            yield Button("Setup Health", id="settings-health-button")
                            yield Button("Sync", id="settings-sync-button")
                            yield Button("Tour", id="settings-tour-button")
                            yield Button("Updates", id="settings-updates-button")
                            yield Button("Extension", id="settings-extension-button")
                            yield Button("Appearance", id="settings-appearance-button")
                            yield Button("Sounds", id="settings-sounds-button")
                            yield Button("Subjects", id="settings-subjects-button")
                            yield Button("Data & Privacy", id="settings-privacy-button")
                            yield Button("Focus Import", id="settings-focus-import-button")

                        with Vertical(id="settings-content"):
                            with Vertical(id="weekly-goal-panel"):
                                yield Static("Set your weekly study goal.", id="goal-panel-title")
 
                                yield Input(
                                    placeholder="Weekly goal in minutes, e.g. 300",
                                    id="weekly-goal-input",
                                )
 
                                with Horizontal(id="settings-button-row"):
                                    yield Button("Save Goal", id="save-goal-button")
 
                                yield Static("", id="settings-message")

                            with Vertical(id="setup-health-panel"):
                                yield Static("Setup health", id="setup-health-title")
                                yield Static("", id="setup-health-details")

                            with Vertical(id="sync-panel"):
                                yield Static("Cloud sync", id="sync-panel-title")
                                yield Static("", id="sync-details")

                                with Horizontal(id="sync-button-row"):
                                    yield Button("Sync Now", id="sync-now-button")

                                yield Static("", id="sync-message")

                            with Vertical(id="tour-panel"):
                                yield Static("Guided tour", id="tour-panel-title")
                                yield Static("", id="tour-details")

                                with Horizontal(id="tour-button-row"):
                                    yield Button("Start Tour", id="start-tour-button")
                                    yield Button("Mark Complete", id="mark-tour-complete-button")

                                yield Static("", id="tour-message")

                            with Vertical(id="updates-panel"):
                                yield Static("Updates", id="updates-panel-title")
                                yield Static("", id="updates-details")

                                with Horizontal(id="updates-button-row"):
                                    yield Button("Check for Updates", id="check-update-button")

                                yield Static("", id="updates-message")

                            with Vertical(id="extension-panel"):
                                yield Static("Browser extension", id="extension-panel-title")
                                yield Static("", id="extension-details")

                                with Horizontal(id="extension-button-row"):
                                    yield Button("Open Extension Guide", id="open-extension-guide-button")

                                yield Static("", id="extension-message")

                            with Vertical(id="appearance-panel"):
                                yield Static("Appearance", id="appearance-panel-title")
                                yield Checkbox("Light mode", id="light-mode-checkbox")
                                yield Static("", id="appearance-message")

                            with Vertical(id="privacy-panel"):
                                yield Static("Data & privacy", id="privacy-panel-title")
                                yield Static("", id="privacy-details")

                                with Vertical(id="privacy-button-stack"):
                                    with Horizontal(id="privacy-button-row"):
                                        yield Button("Export Data", id="export-data-button")
                                        yield Button("Clear Focus Quality", id="clear-focus-quality-data-button")
                                    with Horizontal(id="privacy-danger-button-row"):
                                        yield Button("Reset Local Study Data", id="reset-local-data-button")

                                yield Static("", id="privacy-message")

                            with Vertical(id="focus-import-panel"):
        
                                yield Static("Chrome focus import", id="focus-quality-title")
                                yield Input(
                                    placeholder="Focus import key",
                                    id="focus-import-secret-input",
                                    password=True,
                                )
                                yield Button("Save import Key", id="save-focus-import-secret-button")
                                yield TextArea("", id="focus-quality-json-input")

                                with Horizontal(id="focus-quality-button-row"):
                                    yield Button("Import JSON", id="import-focus-json-button")
                                    yield Button("Clear JSON", id="clear-focus-json-button")

                                yield Static("", id="focus-quality-message")
                                yield Static("", id="focus-quality-summary")

                            with Vertical(id="sounds-panel"):
                                yield Static("Sound settings", id="sound-panel-title")

                                yield Checkbox("UI sounds", id="ui-sounds-checkbox")
                                yield Checkbox("Focus complete sound", id="focus-sound-checkbox")
                                yield Checkbox("Streak protected sound", id="streak-sound-checkbox")
                                yield Checkbox("Achievement sound", id="achievement-sound-checkbox")
                                yield Checkbox("Focus complete notification", id="focus-notification-checkbox")
                                yield Checkbox("Sync failed notification", id="sync-failed-notification-checkbox")
                                yield Checkbox("Achievement notification", id="achievement-notification-checkbox")

                                yield Static("", id="sounds-message")

                            with Vertical(id="subjects-panel"):
                                yield Static("Subjects", id="subject-panel-title")
 
                                with Horizontal(id="subject-subnav"):
                                    yield Button("Add", id="subject-add-tab")
                                    yield Button("Edit", id="subject-edit-tab")
                                    yield Button("Delete", id="subject-delete-tab")
 
                                with Vertical(id="subject-add-panel"):
                                    yield Static("Add a subject.", id="subject-add-title")
 
                                    yield Input(
                                        placeholder="Subject name, e.g. maths",
                                        id="new-subject-input",
                                    )

                                    yield Static("Websites, one per line", classes="field-hint")
                                    yield TextArea(
                                        "",
                                        id="new-subject-website-input",
                                    )

                                    yield Static("Topics, one per line", classes="field-hint")
                                    yield TextArea(
                                        "",
                                        id="new-subject-topic-input",
                                    )
 
                                    with Horizontal(id="subject-button-row"):
                                        yield Button("Add Subject", id="add-subject-button")
 
                                    yield Static("", id="subject-message")
 
                                with Vertical(id="subject-edit-panel"):
 
                                    yield Static("Edit subject websites and topics.", id="edit-website-title")
 
                                    yield Select(
                                        options=[],
                                        id="edit-website-subject-select",
                                        prompt="Choose a subject",
                                    )

                                    yield Static("Websites, one per line", classes="field-hint")
                                    yield TextArea(
                                        "",
                                        id="edit-website-input",
                                    )

                                    yield Static("Topics, one per line", classes="field-hint")
                                    yield TextArea(
                                        "",
                                        id="edit-topic-input",
                                    )
 
                                    with Horizontal(id="edit-website-button-row"):
                                        yield Button("Update Subject", id="update-website-button")
 
                                    yield Static("", id="edit-website-message")
 
 
                                with Vertical(id="subject-delete-panel"):
 
                                    yield Static("Delete a subject.", id="delete-subject-title")
 
                                    yield Select(
                                        options=[],
                                        id="delete-subject-select",
                                        prompt="Choose a subject",
                                    )
 
                                    with Horizontal(id="delete-subject-button-row"):
                                        yield Button("Delete Subject", id="delete-subject-button")
 
                                    yield Static("", id="delete-subject-message")
 
            yield Static("", id="global-message")
 
        yield Footer()
 
    def on_mount(self):
        #show login first
        login_container = self.query_one("#login-container")
        main_container = self.query_one("#main-container")
        tour_guide = self.query_one("#tour-guide")

        login_container.display = True
        main_container.display = False
        tour_guide.display = False

        subjects_panel = self.query_one("#subjects-panel")
        setup_health_panel = self.query_one("#setup-health-panel")
        sync_panel = self.query_one("#sync-panel")
        tour_panel = self.query_one("#tour-panel")
        updates_panel = self.query_one("#updates-panel")
        extension_panel = self.query_one("#extension-panel")
        appearance_panel = self.query_one("#appearance-panel")
        privacy_panel = self.query_one("#privacy-panel")

        subjects_panel.display = False
        setup_health_panel.display = False
        sync_panel.display = False
        tour_panel.display = False
        updates_panel.display = False
        extension_panel.display = False
        appearance_panel.display = False
        privacy_panel.display = False

        subject_edit_panel = self.query_one("#subject-edit-panel")
        subject_delete_panel = self.query_one("#subject-delete-panel")

        subject_edit_panel.display = False
        subject_delete_panel.display = False

        sound_panel = self.query_one("#sounds-panel")
        sound_panel.display = False

        timetable_form_panel = self.query_one("#timetable-form-panel")
        timetable_form_panel.display = False

        focus_import_panel = self.query_one("#focus-import-panel")
        focus_import_panel.display = False

        manage_session_panel = self.query_one("#manage-session-panel")
        manage_session_panel.display = False

        self.apply_theme()
        self.hide_all_temp_messages()
        self.try_remembered_login()
 
    def update_dashboard(self):
        data = load_data()
        weekly_goal = data.get("weekly_goal", 300)

        home_status_card = self.query_one("#home-status-card", Static)
        home_action_card = self.query_one("#home-action-card", Static)
        home_focus_readiness_card = self.query_one("#home-focus-readiness-card", Static)
        home_review_card = self.query_one("#home-review-card", Static)
        home_wins_card = self.query_one("#home-wins-card", Static)
        home_weak_topics_card = self.query_one("#home-weak-topics-card", Static)
        setup_checklist = self.query_one("#setup-checklist", Static)
        recent_sessions = self.query_one("#recent-sessions", Static)
        subject_stats = self.query_one("#subject-stats", Static)
        session_select = self.query_one("#session-select", Select)
        subject_select = self.query_one("#subject-select", Select)
        log_topic_select = self.query_one("#log-topic-select", Select)
        edit_session_subject_select = self.query_one("#edit-session-subject-select", Select)
        focus_subject_select = self.query_one("#focus-subject-select", Select)
        focus_topic_select = self.query_one("#focus-topic-select", Select)
        weekly_goal_input = self.query_one("#weekly-goal-input", Input)
        delete_subject_select = self.query_one("#delete-subject-select", Select)
        edit_website_subject_select = self.query_one("#edit-website-subject-select", Select)
        timetable_subject_select = self.query_one("#timetable-subject-select", Select)
        today_timetable = self.query_one("#today-timetable", Static)
        timetable_grid = self.query_one("#timetable-grid", Static)
        achievements = self.query_one("#achievements", Static)
        manage_timetable_select = self.query_one("#manage-timetable-select", Select)
        focus_quality_summary = self.query_one("#focus-quality-summary", Static)
        focus_import_secret_input= self.query_one("#focus-import-secret-input", Input)
        focus_import_secret = data.get("focus_import_settings", {}).get("secret", "")
        focus_import_secret_input.placeholder = (
            "Import key saved" if focus_import_secret else "Focus import key"
        )

        weekly_goal_input.placeholder = f"Current goal: {weekly_goal} minutes"
 
        setup_text = get_setup_checklist(
            data,
            self.logged_in,
            self.server_is_online,
            get_server_token(),
        )
        setup_checklist.update(setup_text)
        setup_checklist.display = "fully set up" not in setup_text

        home_status_card.update(
            get_home_status_card(
                data,
                self.logged_in,
                self.server_is_online,
                get_server_token(),
            )
        )
        home_action_card.update(get_home_action_card(data))
        home_focus_readiness_card.update(get_focus_readiness_display(data, get_server_token()))
        home_review_card.update(get_review_queue_display(data))
        home_wins_card.update(get_todays_wins_display(data))
        home_weak_topics_card.update(get_weak_topics_display(data))
 
        recent_sessions.update(get_recent_sessions(data))
        recent_sessions.display = False
        subject_stats.update(get_subject_stats(data))
        focus_quality_summary.update(get_focus_quality_summary(data))
 
        session_select.set_options(get_session_options(data))
        session_select.clear()
 
        subject_select.set_options(get_subject_options(data))
        subject_select.clear()

        log_topic_select.set_options([])
        log_topic_select.clear()

        edit_session_subject_select.set_options(get_subject_options(data))
        edit_session_subject_select.clear()
        self.clear_session_edit_form()
 
        focus_subject_select.set_options(get_subject_options(data))
        focus_subject_select.clear()

        focus_topic_select.set_options([])
        focus_topic_select.clear()
 
        delete_subject_select.set_options(get_subject_options(data))
        delete_subject_select.clear()
 
        edit_website_subject_select.set_options(get_subject_options(data))
        edit_website_subject_select.clear()

        timetable_subject_select.set_options(get_subject_options(data))
        timetable_subject_select.clear()

        manage_timetable_select.set_options(get_timetable_session_options(data))
        manage_timetable_select.clear()

        today_timetable.update(get_today_timetable_display(data))
        timetable_grid.update(get_timetable_grid(data))

        achievements.update(get_achievement_display(data))

        self.update_sync_status()
        self.update_setup_health_panel()
        self.update_extension_panel()
        self.update_privacy_panel()
        self.update_tour_panel()
        self.update_updates_panel()
        self.check_tour_progress()

    def update_sync_status(self):
        sync_status_label = self.query_one("#sync-status-label", Static)

        data = load_data()
        sync_data = data.get("sync", {})

        last_local_update = sync_data.get("last_local_update")
        last_cloud_sync = sync_data.get("last_cloud_sync")
        last_sync_error = sync_data.get("last_sync_error")
        sync_details = self.query_one("#sync-details", Static)

        if last_sync_error is not None:
            sync_status_label.update("[red]Sync: Failed[/red]")
            sync_details.update(f"[red]{last_sync_error}[/red]")
            self.update_setup_health_panel()
            
            if self.last_notified_sync_error != last_sync_error:
                self.last_notified_sync_error = last_sync_error
                self.notify_sync_failed(last_sync_error)
            
            return

        if last_cloud_sync is None:
            sync_status_label.update("[yellow]Sync: Not synced yet[/yellow]")
            sync_details.update("[yellow]This device has not uploaded cloud data yet.[/yellow]")
            self.update_setup_health_panel()
            return
        
        if last_local_update is None:
            sync_status_label.update("[green]Sync: Synced[/green]")
            sync_details.update("[green]Cloud sync is up to date.[/green]")
            self.update_setup_health_panel()
            return
        
        if last_cloud_sync >= last_local_update:
            sync_status_label.update("[green]Sync: Synced[/green]")
            sync_details.update("[green]Cloud sync is up to date.[/green]")
            self.last_notified_sync_error = None
        else:
            sync_status_label.update("[yellow]Sync: Pending upload[/yellow]")
            sync_details.update("[yellow]A recent local change is waiting to upload.[/yellow]")

        self.update_setup_health_panel()

    def update_setup_health_panel(self):
        setup_health_details = self.query_one("#setup-health-details", Static)
        setup_health_details.update(
            get_setup_health_display(
                load_data(),
                self.logged_in,
                self.server_is_online,
                get_server_token(),
            )
        )

    def update_tour_panel(self):
        data = load_data()
        onboarding = data.get("onboarding", {})
        tour_details = self.query_one("#tour-details", Static)

        if onboarding.get("tour_completed"):
            status = "[green]Completed[/green]"
        elif onboarding.get("tour_declined"):
            status = "[yellow]Skipped[/yellow]"
        else:
            status = "[yellow]Not viewed yet[/yellow]"

        tour_details.update(
            "\n".join([
                f"[bold]Tour status:[/bold] {status}",
                "The tour now stays inside the app while you click through setup.",
                "It guides Home, Subjects, websites, Timetable, Log Session, Focus, and Sync.",
                "You can replay it any time from here.",
            ])
        )

    def update_updates_panel(self):
        self.query_one("#updates-details", Static).update(
            get_update_status_display(load_data())
        )

    def update_extension_panel(self):
        self.query_one("#extension-details", Static).update(
            get_extension_status_display(load_data(), get_server_token())
        )

    def update_privacy_panel(self):
        self.query_one("#privacy-details", Static).update(
            get_privacy_display(load_data())
        )

    def apply_theme(self):
        data = load_data()
        appearance_settings = data.get("appearance_settings", {})
        theme = appearance_settings.get("theme", "dark")

        if theme == "light":
            self.screen.add_class("light-mode")
        else:
            self.screen.remove_class("light-mode")

    def update_appearance_settings_panel(self):
        data = load_data()
        appearance_settings = data.get("appearance_settings", {})
        theme = appearance_settings.get("theme", "dark")

        self.query_one("#light-mode-checkbox", Checkbox).value = theme == "light"
    
    def update_sound_settings_panel(self):
        self.loading_settings = True
        
        data = load_data()
        sound_settings = data.get("sound_settings", {})
        notification_settings = data.get("notification-settings", {})

        self.query_one("#ui-sounds-checkbox", Checkbox).value = sound_settings.get("ui", True)
        self.query_one("#focus-sound-checkbox", Checkbox).value = sound_settings.get("focus_complete", True)
        self.query_one("#streak-sound-checkbox", Checkbox).value = sound_settings.get("streak_protected", True)
        self.query_one("#achievement-sound-checkbox", Checkbox).value = sound_settings.get("achievement", True)
        self.query_one("#focus-notification-checkbox", Checkbox).value = (
            notification_settings.get("focus_complete", True)
        )
        self.query_one("#sync-failed-notification-checkbox", Checkbox).value = (
            notification_settings.get("sync_failed", True)
        )
        self.query_one("#achievement-notification-checkbox", Checkbox).value = (
            notification_settings.get("achievement", True)
        )
        self.set_timer(
            0.1,
            lambda: setattr(self, "loading_settings", False),
        )

    def show_settings_panel(self, active_panel_id):
        panel_ids = [
            "#weekly-goal-panel",
            "#setup-health-panel",
            "#sync-panel",
            "#tour-panel",
            "#updates-panel",
            "#extension-panel",
            "#appearance-panel",
            "#privacy-panel",
            "#sounds-panel",
            "#subjects-panel",
            "#focus-import-panel",
        ]

        for panel_id in panel_ids:
            self.query_one(panel_id).display = panel_id == active_panel_id

        if active_panel_id == "#setup-health-panel":
            self.update_setup_health_panel()

        if active_panel_id == "#sync-panel":
            self.update_sync_status()

        if active_panel_id == "#tour-panel":
            self.update_tour_panel()

        if active_panel_id == "#updates-panel":
            self.update_updates_panel()

        if active_panel_id == "#extension-panel":
            self.update_extension_panel()

        if active_panel_id == "#appearance-panel":
            self.update_appearance_settings_panel()

        if active_panel_id == "#privacy-panel":
            self.update_privacy_panel()

        if active_panel_id == "#sounds-panel":
            self.update_sound_settings_panel()

        if active_panel_id == "#subjects-panel":
            try:
                subject_sync = self.sync_subject_websites_from_server()
                if subject_sync["updates"] > 0:
                    self.update_dashboard()
            except ValueError:
                pass

            self.query_one("#subject-add-panel").display = True
            self.query_one("#subject-edit-panel").display = False
            self.query_one("#subject-delete-panel").display = False

        if active_panel_id == "#focus-import-panel":
            self.update_dashboard()
        
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if self.loading_settings:
            return
        
        checkbox_sound_map = {
            "ui-sounds-checkbox": "ui",
            "focus-sound-checkbox": "focus_complete",
            "streak-sound-checkbox": "streak_protected",
            "achievement-sound-checkbox": "achievement"
        }

        notification_checkbox_map = {
            "focus-notification-checkbox": "focus_complete",
            "sync-failed-notification-checkbox": "sync_failed",
            "achievement-notification-checkbox": "achievement",
        }

        if event.checkbox.id == "light-mode-checkbox":
            data = load_data()

            if event.value:
                data["appearance_settings"]["theme"] = "light"
            else:
                data["appearance_settings"]["theme"] = "dark"

            save_data(data)
            self.apply_theme()

            self.show_temp_message(
                "#appearance-message",
                "[green]Appearance updated.[/green]",
                seconds=2,
            )
            return

        sound_name = checkbox_sound_map.get(event.checkbox.id)

        if sound_name is not None:
            data = load_data()
            data["sound_settings"][sound_name] = event.value
            save_data(data)

            self.show_temp_message(
                "#sounds-message",
                "[green]Sound settings updated.[/green]",
                seconds=2,
            )
            return

        notification_name = notification_checkbox_map.get(event.checkbox.id)
        
        if notification_name is not None:
            data = load_data()
            data["notification-settings"][notification_name] = event.value
            save_data(data)

            self.show_temp_message(
                "#sounds-message",
                "[green]Notification settings updated.[/green]",
                seconds=2,
            )
            return


    def show_temp_message(self, widget_id, text, seconds=5):
        #show message then hide it
        widget = self.query_one(widget_id, Static)

        version = self.temp_message_versions.get(widget_id, 0) + 1
        self.temp_message_versions[widget_id] = version

        widget.display = True
        widget.update(text)

        self.set_timer(seconds, lambda: self.hide_temp_message(widget_id, version))

    def hide_temp_message(self, widget_id, version):
        #hide temporary message
        if self.temp_message_versions.get(widget_id) != version:
            return

        widget = self.query_one(widget_id, Static)
        widget.update("")
        widget.display = False

    def hide_all_temp_messages(self):
        #hide empty message boxes
        temp_widget_ids = [
            "#message",
            "#manage-message",
            "#settings-message",
            "#sync-message",
            "#tour-message",
            "#updates-message",
            "#extension-message",
            "#appearance-message",
            "#privacy-message",
            "#subject-message",
            "#edit-website-message",
            "#delete-subject-message",
            "#focus-message",
            "#focus-quality-message",
            "#focus-timer",
            "#focus-phase",
            "#global-message",
            "#login-message",
            "#timetable-message",
        ]

        for widget_id in temp_widget_ids:
            self.query_one(widget_id, Static).display = False

    
    def sound_is_enabled(self, sound_name):
        data = load_data()
        sound_settings = data.get("sound_settings", {})
        return sound_settings.get(sound_name, True)

    def play_app_sound(self, sound_name):
        if not self.sound_is_enabled(sound_name):
            return
        
        self.run_worker(
            partial(play_sound, sound_name),
            thread=True,
            group="sound-effects",
        )

    def play_achievement_sound(self):
        if not self.sound_is_enabled("achievement"):
            return

        # The achievement modal owns this sound so every queued popup plays it.
        play_sound("achievement", wait=True)

    def play_ui_sound(self):
        if not self.sound_is_enabled("ui"):
            return

        # UI sounds are tiny and async on Windows; playing them directly keeps
        # their order from racing achievement/focus sounds.
        play_sound("ui")

    def play_focus_complete_sound(self):
        self.play_app_sound("focus_complete")

    def play_streak_protected(self):
        self.play_app_sound("streak_protected")

    def show_focus_notification(self, subject, minutes):

        if not self.notification_is_enabled("focus_complete"):
            return

        self.run_worker(
            partial(show_focus_complete_notification, subject, minutes),
            thread=True,
            group="desktop-notifications",
        )
    
    def notification_is_enabled(self, notification_name):
        data = load_data()
        notification_settings = data.get("notification-settings", {})
        return notification_settings.get(notification_name, True)

    def notify_sync_failed(self, error_message):
        if not self.notification_is_enabled("sync_failed"):
            return
        
        self.run_worker(
            partial(show_sync_failed_notification, error_message),
            thread=True,
            group="desktop-notifications",
        )


    def notify_achievement_unlocked(self, achievement):
        if not self.notification_is_enabled("achievement"):
            return

        self.run_worker(
            partial(
                show_achievement_notification,
                achievement["name"],
                achievement["description"],
            ),
            thread=True,
            group="desktop-notifications",
        )

    def show_achievement_effect(self, achievements):
        if len(achievements) == 0:
            return
        
        current_achievement = achievements[0]
        remaining_achievements = achievements[1:]

        self.notify_achievement_unlocked(current_achievement)

        self.push_screen(
            AchievementEffectScreen(
                current_achievement,
                remaining_achievements,
            )
        )

    def unlock_earned_achievements(self):
        data = load_data()
        unlocked_ids = data["achievements"]["unlocked"]
        new_achievements = []

        for achievement in ACHIEVEMENTS:
            if achievement["id"] in unlocked_ids:
                continue

            if achievement["condition"](data):
                unlocked_ids.append(achievement["id"])
                new_achievements.append(achievement)

        if len(new_achievements) == 0:
            return False

        save_data(data)
        self.update_dashboard()

        self.show_achievement_effect(new_achievements)

        return True

    def action_escape_quit(self):
        current_time = datetime.now()
 
        if self.last_escape_time is None:
            self.last_escape_time = current_time
            self.show_temp_message("#global-message", "[yellow]Press Esc again to quit.[/yellow]")
            return
 
        time_difference = current_time - self.last_escape_time
 
        if time_difference.total_seconds() <= 2:
            self.exit()
        else:
            self.last_escape_time = current_time
            self.show_temp_message("#global-message", "[yellow]Press Esc again to quit.[/yellow]")

    def home_is_active(self):
        if not self.logged_in or self.focus_overlay_screen is not None:
            return False

        try:
            return self.query_one("#main-tabs", TabbedContent).active == "dashboard-tab"
        except Exception:
            return False

    def on_key(self, event):
        if not self.home_is_active():
            return

        key = event.key.lower()

        if key == "enter":
            event.prevent_default()
            event.stop()
            self.prepare_recommended_focus()
            return

        if key == "f":
            event.prevent_default()
            event.stop()
            self.play_ui_sound()
            self.set_main_tab("focus-tab")
            self.focus_tour_widget("#focus-minutes-input")
            return

        if key == "s":
            event.prevent_default()
            event.stop()
            self.skip_home_action()
            return

        if key == "r":
            event.prevent_default()
            event.stop()
            self.open_home_review_action()
            return

    def fill_focus_form(self, subject, minutes, message, topic=None):
        data = load_data()

        if subject not in data.get("subjects", []):
            self.set_main_tab("settings-tab")
            self.show_settings_panel("#subjects-panel")
            self.show_temp_message(
                "#global-message",
                "[yellow]Add a subject before starting focus.[/yellow]",
            )
            return False

        self.set_main_tab("focus-tab")

        focus_subject_select = self.query_one("#focus-subject-select", Select)
        focus_topic_select = self.query_one("#focus-topic-select", Select)
        focus_minutes_input = self.query_one("#focus-minutes-input", Input)
        website_input = self.query_one("#focus-website-input", TextArea)

        focus_subject_select.value = subject
        focus_topic_select.set_options(get_topic_options(data, subject))
        focus_topic_select.clear()

        if topic in get_subject_topic_list(data, subject):
            focus_topic_select.value = topic

        focus_minutes_input.value = str(minutes)
        website_input.load_text(format_website_list_text(get_subject_website_list(data, subject)))

        self.show_temp_message("#focus-message", message)
        self.focus_tour_widget("#start-focus-button")
        return True

    def prepare_recommended_focus(self, play_sound_effect=True):
        if play_sound_effect:
            self.play_ui_sound()

        data = load_data()
        recommendation = get_next_best_action(data)
        subject = recommendation["subject"]
        minutes = recommendation["target_minutes"]

        if self.fill_focus_form(
            subject,
            minutes,
            (
                "[green]Recommended focus block prepared. "
                "Press Start Focus when you are ready.[/green]"
            ),
        ):
            self.query_one("#pomodoro-mode-checkbox", Checkbox).value = False

    def skip_home_action(self, play_sound_effect=True):
        if play_sound_effect:
            self.play_ui_sound()

        action_card = self.query_one("#home-action-card", Static)
        action_card.update(
            "\n".join([
                "[bold white]NEXT BEST ACTION[/bold white]",
                "Skipped for now.",
                "Press [bold]F[/bold] to open Focus, or log a session when you finish studying.",
            ])
        )

    def open_home_review_action(self):
        self.play_ui_sound()
        data = load_data()
        due_reviews = get_due_review_items(data, limit=1)

        if not due_reviews:
            self.show_temp_message(
                "#global-message",
                "[yellow]No review topics yet. Add topics after sessions to unlock reviews.[/yellow]",
            )
            return

        item = due_reviews[0]
        subject = item.get("subject", "")
        topic = item.get("topic", "review")

        self.fill_focus_form(
            subject,
            25,
            f"[green]Review focus prepared for {topic}.[/green]",
            topic=topic,
        )
 
    def show_streak_effect(self, streak_count):
        if streak_count > 0:
            self.play_streak_protected()
            self.push_screen(StreakEffectScreen(streak_count))
        else:
            self.show_temp_message("#global-message", "[green]Your study session has been logged.[/green]")
 
    def delete_subject_and_sessions(self, subject):
        data = load_data()
 
        if subject not in data["subjects"]:
            self.show_temp_message("#delete-subject-message", "[red]That subject could not be found.[/red]")
            self.update_dashboard()
            return
 
        original_session_count = len(data["sessions"])
        original_timetable_count = len(data.get("timetable", []))

        data["subjects"].remove(subject)
 
        if subject in data["subject_websites"]:
            del data["subject_websites"][subject]

        if subject in data["subject_topics"]:
            del data["subject_topics"][subject]
 
        data["sessions"] = [
            session for session in data["sessions"]
            if session["subject"] != subject
        ]
        data["timetable"] = [
            item for item in data.get("timetable", [])
            if item["subject"] != subject
        ]
 
        deleted_session_count = original_session_count - len(data["sessions"])
        deleted_timetable_count = original_timetable_count - len(data["timetable"])

        save_data(data)
        self.update_dashboard()
 
        self.show_temp_message(
            "#delete-subject-message",
            f"[yellow]Deleted subject: {subject}. "
            f"Removed {deleted_session_count} linked session(s) "
            f"and {deleted_timetable_count} timetable item(s).[/yellow]",
        )

    def get_focus_websites_for_subject(self, subject, prefer_focus_input=True):
        websites = []

        if prefer_focus_input:
            try:
                website_input = self.query_one("#focus-website-input", TextArea)
                websites = clean_website_list(website_input.text)
            except Exception:
                websites = []

        if len(websites) == 0:
            websites = get_subject_website_list(load_data(), subject)

        return websites

    def open_focus_websites(self, subject=None, show_message=True):
        if subject is None:
            if self.focus_subject is not None:
                subject = self.focus_subject
            else:
                focus_subject_select = self.query_one("#focus-subject-select", Select)
                subject = focus_subject_select.value

        if is_blank_select_value(subject):
            if show_message:
                self.show_temp_message("#focus-message", "[red]Please choose a subject first.[/red]")
            return False

        if self.focus_subject == str(subject) and len(self.focus_websites) > 0:
            websites = self.focus_websites
        else:
            websites = self.get_focus_websites_for_subject(subject)

        if len(websites) == 0:
            if show_message:
                self.show_temp_message(
                    "#focus-message",
                    "[red]No websites saved for this subject. Please enter one manually.[/red]",
                )
            return False

        for website in websites:
            webbrowser.open(website)

        if show_message:
            self.show_temp_message(
                "#focus-message",
                f"[green]Opened {len(websites)} website(s) for {subject}.[/green]",
            )

        return True

    def get_focus_phase_text(self):
        if self.focus_mode == "pomodoro" and self.pomodoro_phase == "break":
            return "Break"

        return "Work"

    def get_focus_overlay_display(self):
        return format_focus_countdown_display(
            self.focus_seconds_left,
            self.get_focus_phase_text(),
        )

    def show_focus_overlay(self):
        if self.focus_overlay_screen is not None:
            self.update_focus_overlay()
            return

        self.focus_overlay_screen = FocusSessionScreen()
        self.push_screen(self.focus_overlay_screen)

    def update_focus_overlay(self):
        if self.focus_overlay_screen is None:
            return

        try:
            self.focus_overlay_screen.update_display()
        except Exception:
            self.focus_overlay_screen = None

    def close_focus_overlay(self):
        if self.focus_overlay_screen is None:
            return

        self.focus_overlay_screen = None

        try:
            self.pop_screen()
        except Exception:
            pass
 
    def start_focus_session(self, subject, minutes, pomodoro_mode=False, topic=""):
        focus_timer = self.query_one("#focus-timer", Static)
        focus_message = self.query_one("#focus-message", Static)
 
        self.focus_subject = subject
        self.focus_topic = str(topic).strip()
        self.focus_websites = self.get_focus_websites_for_subject(subject)
        self.focus_mode = "pomodoro" if pomodoro_mode else "manual"
        self.pomodoro_phase = "work"
        self.pomodoro_completed_work_blocks = 0
        self.pomodoro_logged_minutes = 0

        if pomodoro_mode:
            self.focus_minutes = POMODORO_WORK_MINUTES
            self.focus_seconds_left = POMODORO_WORK_MINUTES * 60
        else:
            self.focus_minutes = minutes
            self.focus_seconds_left = minutes * 60
 
        if self.focus_timer is not None:
            self.focus_timer.stop()
 
        if pomodoro_mode:
            focus_message.update(
                "[yellow]Pomodoro started. Completed 50 minute work blocks will auto-log until you cancel.[/yellow]"
            )
        else:
            self.show_temp_message(
                "#focus-message",
                "[yellow]Focus session started. Stay focused until the timer ends.[/yellow]",
            )
 
        self.update_focus_display()
        self.show_focus_overlay()
 
        self.focus_timer = self.set_interval(1, self.tick_focus_timer)
 
    def update_focus_display(self):
        focus_timer = self.query_one("#focus-timer", Static)
 
        minutes_left = self.focus_seconds_left // 60
        seconds_left = self.focus_seconds_left % 60
 
        focus_timer.display = True
        focus_timer.update(
            f"[bold orange1]Focus timer:[/bold orange1] "
            f"{minutes_left:02d}:{seconds_left:02d}"
        )

        focus_phase = self.query_one("#focus-phase", Static)
        focus_phase.display = True

        if self.focus_mode == "pomodoro":
            if self.pomodoro_phase == "break":
                focus_phase.update("[bold cyan]Break[/bold cyan]")
            else:
                focus_phase.update("[bold green]Work[/bold green]")
            self.update_focus_overlay()
            return

        focus_phase.update("[bold green]Work[/bold green]")
        self.update_focus_overlay()
 
    def tick_focus_timer(self):
        self.focus_seconds_left -= 1
 
        if self.focus_seconds_left <= 0:
            self.focus_seconds_left = 0
            self.update_focus_display()
            if self.focus_mode == "pomodoro":
                self.complete_pomodoro_phase()
                return
            self.complete_focus_session()
            return
 
        self.update_focus_display()

    def log_completed_focus_minutes(self, subject, minutes, topic=""):
        data = load_data()
        already_studied_today = has_studied_today(data)
        completed_at = get_utc_now_text()
        clean_topic = str(topic).strip()

        session = {
            "subject": str(subject).lower(),
            "minutes": minutes,
            "date": str(date.today()),
            "source": "focus",
            "completed_at": completed_at,
        }

        if clean_topic:
            session["topic"] = clean_topic

        data["sessions"].append(session)
        protect_streak_today(data)
        save_data(data)

        server_token = get_server_token()

        if server_token is not None:
            self.run_worker(
                partial(
                    self.upload_focus_session_in_background,
                    server_token,
                    str(subject).lower(),
                    minutes,
                    clean_topic,
                    completed_at,
                    None,
                    "focus_cli",
                ),
                thread=True,
                group="focus-upload",
            )

        self.update_dashboard()
        achievement_unlocked = self.unlock_earned_achievements()

        updated_data = load_data()
        streak_count = calculate_current_streak(updated_data)

        return already_studied_today, achievement_unlocked, streak_count, completed_at

    def complete_pomodoro_phase(self):
        focus_message = self.query_one("#focus-message", Static)

        if self.pomodoro_phase == "work":
            completed_subject = self.focus_subject
            completed_minutes = POMODORO_WORK_MINUTES

            already_studied_today, achievement_unlocked, streak_count, _ = (
                self.log_completed_focus_minutes(
                    completed_subject,
                    completed_minutes,
                    self.focus_topic,
                )
            )

            self.pomodoro_completed_work_blocks += 1
            self.pomodoro_logged_minutes += completed_minutes
            self.pomodoro_phase = "break"
            self.focus_minutes = POMODORO_BREAK_MINUTES
            self.focus_seconds_left = POMODORO_BREAK_MINUTES * 60

            focus_message.update(
                f"[green]Work block {self.pomodoro_completed_work_blocks} complete. "
                f"Logged {completed_minutes} minutes of {completed_subject}. Break started.[/green]"
            )

            if not already_studied_today and not achievement_unlocked:
                self.show_streak_effect(streak_count)
            elif not achievement_unlocked:
                self.play_focus_complete_sound()

            self.show_focus_notification(completed_subject, completed_minutes)
            self.update_focus_display()
            return

        self.pomodoro_phase = "work"
        self.focus_minutes = POMODORO_WORK_MINUTES
        self.focus_seconds_left = POMODORO_WORK_MINUTES * 60
        focus_message.update("[yellow]Break finished. Work started.[/yellow]")
        self.update_focus_display()
 
    def complete_focus_session(self):
        focus_timer = self.query_one("#focus-timer", Static)
        focus_message = self.query_one("#focus-message", Static)
 
        if self.focus_timer is not None:
            self.focus_timer.stop()
            self.focus_timer = None
 
        completed_subject = self.focus_subject
        completed_topic = self.focus_topic
        completed_minutes = self.focus_minutes
        self.close_focus_overlay()

        already_studied_today, achievement_unlocked, streak_count, completed_at = (
            self.log_completed_focus_minutes(
                completed_subject,
                completed_minutes,
                completed_topic,
            )
        )
 
        self.focus_seconds_left = 0
        self.focus_subject = None
        self.focus_topic = ""
        self.focus_websites = []
        self.focus_minutes = 0
        self.focus_mode = "manual"
        self.pomodoro_phase = "work"
 
        self.show_temp_message("#focus-timer", "[bold green]Focus finished.[/bold green]")
        focus_phase = self.query_one("#focus-phase", Static)
        focus_phase.update("")
        focus_phase.display = False
        self.show_temp_message(
            "#focus-message",
            f"[green]Completed focus session. Logged {completed_minutes} minutes of {completed_subject} study.[/green]",
        )

        
        if not already_studied_today and not achievement_unlocked:
            self.show_streak_effect(streak_count)
        elif not achievement_unlocked:
            self.play_focus_complete_sound()
        self.show_focus_notification(completed_subject, completed_minutes)
        self.push_screen(
            FocusSessionNoteScreen(
                completed_at,
                completed_subject,
                completed_topic,
                completed_minutes,
                get_topic_options(load_data(), completed_subject),
            )
        )

    def upload_focus_session_in_background(
        self,
        token,
        subject,
        minutes,
        topic="",
        completed_at=None,
        review_note=None,
        source="focus_cli",
    ):
        #avoid freezing the UI when the server is slow or offline
        try:
            upload_focus_session(
                token=token,
                subject=subject,
                minutes=minutes,
                website=None,
                topic=topic or None,
                completed_at=completed_at,
                review_note=review_note or None,
                source=source,
            )
        except ValueError:
            self.call_from_thread(
                self.show_temp_message,
                "#focus-message",
                "[yellow]Focus saved locally, but server upload failed.[/yellow]",
            )
            return

        self.call_from_thread(self.refresh_leaderboard)
 
    def cancel_focus_session(self):
        focus_timer = self.query_one("#focus-timer", Static)
        focus_message = self.query_one("#focus-message", Static)
 
        if self.focus_timer is not None:
            self.focus_timer.stop()
            self.focus_timer = None
 
        self.focus_seconds_left = 0
        self.focus_subject = None
        self.focus_topic = ""
        self.focus_websites = []
        self.focus_minutes = 0
        was_pomodoro = self.focus_mode == "pomodoro"
        logged_minutes = self.pomodoro_logged_minutes
        logged_blocks = self.pomodoro_completed_work_blocks
        self.focus_mode = "manual"
        self.pomodoro_phase = "work"
        self.pomodoro_completed_work_blocks = 0
        self.pomodoro_logged_minutes = 0
 
        focus_timer.update("")
        focus_timer.display = False
        focus_phase = self.query_one("#focus-phase", Static)
        focus_phase.update("")
        focus_phase.display = False
        self.close_focus_overlay()

        if was_pomodoro:
            focus_message.update(
                f"[yellow]Pomodoro stopped. Logged {logged_blocks} completed work block(s), "
                f"{logged_minutes} minutes total.[/yellow]"
            )
            return

        self.show_temp_message("#focus-message", "[yellow]Focus session cancelled. No study time was logged.[/yellow]")

    def save_focus_session_note(self, session_completed_at, note, topic=None):
        clean_note = str(note).strip()
        clean_topic = str(topic or "").strip()

        if clean_note == "" and clean_topic == "":
            self.show_temp_message("#focus-message", "[yellow]No review saved.[/yellow]")
            return

        data = load_data()

        for session in reversed(data.get("sessions", [])):
            if session.get("completed_at") == session_completed_at:
                if clean_note:
                    session["note"] = clean_note
                else:
                    session.pop("note", None)

                if clean_topic:
                    session["topic"] = clean_topic
                else:
                    session.pop("topic", None)

                save_data(data)
                self.update_dashboard()

                server_token = get_server_token()

                if server_token is not None:
                    upload_source = (
                        "chrome_extension"
                        if session.get("source") == "chrome_extension"
                        else "focus_cli"
                    )
                    self.run_worker(
                        partial(
                            self.upload_focus_session_in_background,
                            server_token,
                            session.get("subject", "unknown"),
                            int(session.get("minutes", 0) or 0),
                            session.get("topic", ""),
                            session.get("completed_at"),
                            session.get("note", ""),
                            upload_source,
                        ),
                        thread=True,
                        group="focus-upload",
                    )

                self.show_temp_message("#focus-message", "[green]Session review saved.[/green]")
                return

        self.show_temp_message("#focus-message", "[red]Could not find that session to save the note.[/red]")

    def show_sessions_panel(self, panel_name):
        log_panel = self.query_one("#log-session-panel")
        manage_panel = self.query_one("#manage-session-panel")

        log_panel.display = panel_name == "log"
        manage_panel.display = panel_name == "manage"

    def clear_session_edit_form(self):
        self.query_one("#session-details-preview", Static).update(
            "Choose a session to see its details."
        )
        self.query_one("#edit-session-minutes-input", Input).value = ""
        self.query_one("#edit-session-topic-input", Input).value = ""
        self.query_one("#edit-session-note-input", TextArea).load_text("")

    def populate_session_edit_form(self, selected_index):
        data = load_data()
        index = get_select_index(selected_index)

        if index is None or index < 0 or index >= len(data.get("sessions", [])):
            self.clear_session_edit_form()
            return

        session = data["sessions"][index]
        subject = str(session.get("subject", "")).lower()
        topic = str(session.get("topic", "")).strip()
        note = str(session.get("note", "")).strip()
        minutes = int(session.get("minutes", 0) or 0)
        session_date = session.get("date", "unknown date")
        source = session.get("source", "manual")

        subject_select = self.query_one("#edit-session-subject-select", Select)

        if subject:
            subject_select.value = subject

        self.query_one("#edit-session-minutes-input", Input).value = str(minutes)
        self.query_one("#edit-session-topic-input", Input).value = topic
        self.query_one("#edit-session-note-input", TextArea).load_text(note)

        preview_lines = [
            f"[bold]{session_date}[/bold]",
            f"Subject: {subject or 'unknown'}",
            f"Minutes: {minutes}",
            f"Topic: {topic or 'none'}",
            f"Note: {note or 'none'}",
            f"Source: {source}",
        ]

        self.query_one("#session-details-preview", Static).update("\n".join(preview_lines))

    def delete_focus_session_in_background(self, token, cloud_session_id):
        try:
            delete_focus_session(token, int(cloud_session_id))
        except (TypeError, ValueError):
            return

    def on_select_changed(self, event: Select.Changed) -> None:
        data = load_data()

        if event.select.has_focus:
            self.play_ui_sound()

        if event.select.id == "focus-subject-select":
            selected_subject = event.value
            website_input = self.query_one("#focus-website-input", TextArea)
            topic_select = self.query_one("#focus-topic-select", Select)
 
            if is_blank_select_value(selected_subject):
                website_input.load_text("")
                topic_select.set_options([])
                topic_select.clear()
                return
 
            saved_websites = get_subject_website_list(data, selected_subject)
            website_input.load_text(format_website_list_text(saved_websites))
            topic_select.set_options(get_topic_options(data, selected_subject))
            topic_select.clear()
            return
 
        if event.select.id == "edit-website-subject-select":
            selected_subject = event.value
            edit_website_input = self.query_one("#edit-website-input", TextArea)
            edit_topic_input = self.query_one("#edit-topic-input", TextArea)
 
            if is_blank_select_value(selected_subject):
                edit_website_input.load_text("")
                edit_topic_input.load_text("")
                return
 
            saved_websites = get_subject_website_list(data, selected_subject)
            saved_topics = get_subject_topic_list(data, selected_subject)
            edit_website_input.load_text(format_website_list_text(saved_websites))
            edit_topic_input.load_text(format_topic_list_text(saved_topics))
            return

        if event.select.id == "subject-select":
            selected_subject = event.value
            log_topic_select = self.query_one("#log-topic-select", Select)

            if is_blank_select_value(selected_subject):
                log_topic_select.set_options([])
                log_topic_select.clear()
                return

            log_topic_select.set_options(get_optional_topic_options(data, selected_subject))
            log_topic_select.clear()
            return

        if event.select.id == "session-select":
            self.populate_session_edit_form(event.value)
            return
    
    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if self.suppress_next_tab_sound:
            self.suppress_next_tab_sound = False
            return

        if self.logged_in:
            self.play_ui_sound()


    def try_remembered_login(self):
        #try auto login from remembered account
        username_input = self.query_one("#login-username-input", Input)

        remembered_username = get_remembered_username()

        if remembered_username is None:
            return
        
        username_input.value = remembered_username

        remembered_password = get_remembered_password(remembered_username)

        if remembered_password is None:
            self.show_temp_message("#login-message", "[yellow]Enter your password to continue[/yellow]")
            return

        try:
            private_data = login_account(remembered_username, remembered_password)
            set_session(remembered_username, remembered_password, private_data)
        except ValueError:
            clear_remembered_login()
            self.show_temp_message("#login-message", "[red]Saved login expired. Please log in again.[/red]")
            return

        try:
            server_token = login_to_server(remembered_username, remembered_password)
            set_server_token(server_token)

            cloud_data = self.sync_profile_from_server(
                remembered_username,
                remembered_password,
                server_token,
            )

            self.use_newest_profile_after_login(
                remembered_username,
                remembered_password,
                private_data,
                cloud_data,
            )
            self.sync_subject_websites_from_server(server_token)
            self.sync_subject_topics_from_server(server_token)
            self.sync_todo_items_from_server(server_token)
            self.sync_browser_focus_sessions_from_server(server_token)
            self.sync_focus_quality_from_server(server_token)

        except ValueError:
            self.show_temp_message(
                "#login-message",
                "[yellow]Saved local login worked, but server login failed.[/yellow]",
            )

        self.show_main_app()

    def update_server_status(self):
        #update server connection label
        server_status_label = self.query_one("#server-status-label", Static)
        server_status_label.update("[yellow]Server: Checking...[/yellow]")

        self.run_worker(
            self.check_server_status_in_background,
            thread=True,
            exclusive=True,
            group="server-status",
        )

    def check_server_status_in_background(self):
        #avoid freezing the UI while waiting for the network
        server_is_online = check_server_status()
        self.call_from_thread(self.show_server_status, server_is_online)

    def show_server_status(self, server_is_online):
        #update server connection label from the main thread
        server_status_label = self.query_one("#server-status-label", Static)
        self.server_is_online = server_is_online

        if server_is_online:
            server_status_label.update("[green]Server: Connected[/green]")
        else:
            server_status_label.update("[red]Server: Offline[/red]")

        if self.logged_in:
            self.update_setup_health_panel()
            self.query_one("#setup-checklist", Static).update(
                get_setup_checklist(
                    load_data(),
                    self.logged_in,
                    self.server_is_online,
                    get_server_token(),
                )
            )

    def sync_profile_from_server(self, username, password, token):
        #download encrypted profile from server
        try:
            encrypted_profile_data = get_profile_data(token)
        
        except ValueError:
            return None
        
        if encrypted_profile_data is None:
            return None
        
        try:
            cloud_data = decrypt_profile_data(
                encrypted_profile_data,
                username,
                password,
            )

        except Exception:
            self.show_temp_message(
                "#login-message",
                "[red]Could not decrypt cloud profile[/red]",
            )
            return None
        
        return cloud_data

    def sync_focus_quality_from_server(self, token=None):
        #download authenticated Chrome focus summaries and merge them locally
        token = token or get_server_token()

        if token is None:
            return {
                "updates": 0,
                "streak_protected": False,
            }

        server_sessions = get_focus_quality_sessions(token)
        data = load_data()
        already_studied_today = has_studied_today(data)
        added_count = merge_focus_quality_sessions(data, server_sessions)
        streak_protected = (
            not already_studied_today
            and has_studied_today(data)
        )

        if added_count > 0:
            save_data(data)

        if streak_protected:
            self.chrome_sync_protected_streak = True

        return {
            "updates": added_count,
            "streak_protected": streak_protected,
        }

    def sync_subject_websites_from_server(self, token=None):
        #download authenticated subject website lists saved by the extension
        token = token or get_server_token()

        if token is None:
            return {
                "updates": 0,
            }

        server_subject_websites = get_subject_websites(token)
        data = load_data()
        updated_count = merge_subject_websites(data, server_subject_websites)

        if updated_count > 0:
            save_data(data)

        return {
            "updates": updated_count,
        }

    def sync_subject_topics_from_server(self, token=None):
        token = token or get_server_token()

        if token is None:
            return {
                "updates": 0,
            }

        server_subject_topics = get_subject_topics(token)
        data = load_data()
        updated_count = merge_subject_topics(data, server_subject_topics)

        if updated_count > 0:
            save_data(data)

        return {
            "updates": updated_count,
        }

    def sync_browser_focus_sessions_from_server(self, token=None):
        token = token or get_server_token()

        if token is None:
            return {
                "updates": 0,
            }

        server_sessions = get_focus_sessions(token, source="chrome_extension")
        data = load_data()
        updated_count = merge_cloud_focus_sessions(data, server_sessions)

        if updated_count > 0:
            protect_streak_today(data)
            save_data(data)

        return {
            "updates": updated_count,
        }

    def sync_todo_items_from_server(self, token=None):
        #download authenticated browser todo items and merge them locally
        token = token or get_server_token()

        if token is None:
            return {
                "updates": 0,
            }

        server_todo_items = get_todo_items(token)
        data = load_data()
        updated_count = merge_todo_items(data, server_todo_items)

        if updated_count > 0:
            save_data(data)

        return {
            "updates": updated_count,
        }

    def use_newest_profile_after_login(
            self,
            username,
            password,
            local_data,
            cloud_data,
            prefer_cloud_when_equal=False,
    ):
        #keep whichever profile changed most recently
        local_data = repair_data(local_data)

        if cloud_data is None:
            set_session(username, password, local_data)
            save_data(local_data)
            return local_data

        cloud_data = repair_data(cloud_data)

        local_updated_at = local_data["sync"].get("last_local_update")
        cloud_updated_at = cloud_data["sync"].get("last_local_update")

        cloud_is_newer = (
            cloud_updated_at is not None
            and (
                local_updated_at is None
                or cloud_updated_at > local_updated_at
            )
        )

        if prefer_cloud_when_equal and cloud_updated_at == local_updated_at:
            cloud_is_newer = True

        if cloud_is_newer:

            cloud_data["sync"]["last_cloud_sync"] = cloud_updated_at
            cloud_data["sync"]["last_sync_error"] = None
            set_session(username, password, cloud_data)
            save_session_data(cloud_data)
            return cloud_data

        set_session(username, password, local_data)

        if local_updated_at != cloud_updated_at:
            save_data(local_data)

        return local_data

    def offer_setup_tour_if_needed(self, force=False):
        data = load_data()

        if not force and not should_offer_setup_tour(data):
            return

        self.set_timer(0.4, lambda: self.push_screen(SetupTourPromptScreen()))

    def get_current_tour_step(self):
        if self.tour_step_index < 0:
            self.tour_step_index = 0

        if self.tour_step_index >= len(SETUP_TOUR_STEPS):
            self.tour_step_index = len(SETUP_TOUR_STEPS) - 1

        return SETUP_TOUR_STEPS[self.tour_step_index]

    def set_main_tab(self, tab_id):
        main_tabs = self.query_one("#main-tabs", TabbedContent)

        if main_tabs.active == tab_id:
            return

        self.suppress_next_tab_sound = True
        main_tabs.active = tab_id

    def show_subject_subpanel(self, active_panel_id):
        panel_ids = [
            "#subject-add-panel",
            "#subject-edit-panel",
            "#subject-delete-panel",
        ]

        for panel_id in panel_ids:
            self.query_one(panel_id).display = panel_id == active_panel_id

    def focus_tour_widget(self, selector):
        try:
            self.query_one(selector).focus()
        except Exception:
            pass

    def set_first_subject_if_available(self, selector):
        data = load_data()
        subjects = data.get("subjects", [])

        if len(subjects) == 0:
            return

        try:
            self.query_one(selector, Select).value = subjects[0]
        except Exception:
            pass

    def navigate_to_current_tour_step(self):
        step = self.get_current_tour_step()
        step_id = step["id"]

        if step_id == "dashboard":
            self.set_main_tab("dashboard-tab")
            return

        if step_id == "subject":
            self.set_main_tab("settings-tab")
            self.show_settings_panel("#subjects-panel")
            self.show_subject_subpanel("#subject-add-panel")
            self.focus_tour_widget("#new-subject-input")
            return

        if step_id == "websites":
            self.set_main_tab("settings-tab")
            self.show_settings_panel("#subjects-panel")

            if len(load_data().get("subjects", [])) == 0:
                self.show_subject_subpanel("#subject-add-panel")
                self.focus_tour_widget("#new-subject-input")
                return

            self.show_subject_subpanel("#subject-edit-panel")
            self.set_first_subject_if_available("#edit-website-subject-select")
            self.focus_tour_widget("#edit-website-input")
            return

        if step_id == "timetable":
            self.set_main_tab("timetable-tab")
            self.editing_timetable_index = None
            self.query_one("#add-timetable-button", Button).label = "Save Session"
            self.query_one("#timetable-form-panel").display = True
            self.set_first_subject_if_available("#timetable-subject-select")
            self.focus_tour_widget("#timetable-day-select")
            return

        if step_id == "session":
            self.set_main_tab("log-tab")
            self.set_first_subject_if_available("#subject-select")
            self.focus_tour_widget("#minutes-input")
            return

        if step_id == "focus":
            self.set_main_tab("focus-tab")
            self.set_first_subject_if_available("#focus-subject-select")
            self.focus_tour_widget("#focus-minutes-input")
            return

        if step_id == "sync":
            self.set_main_tab("settings-tab")
            self.show_settings_panel("#sync-panel")
            self.focus_tour_widget("#sync-now-button")
            return

        if step_id == "finish":
            self.set_main_tab("settings-tab")
            self.show_settings_panel("#tour-panel")

    def tour_step_is_complete(self, step=None, data=None):
        step = step or self.get_current_tour_step()
        data = data or load_data()
        step_id = step["id"]

        if step_id == "subject":
            return len(data.get("subjects", [])) > 0

        if step_id == "websites":
            subject_websites = data.get("subject_websites", {})
            return any(
                len(clean_website_list(websites)) > 0
                for websites in subject_websites.values()
            )

        if step_id == "timetable":
            return len(data.get("timetable", [])) > 0

        if step_id == "session":
            return len(data.get("sessions", [])) > 0

        if step_id == "focus":
            return has_focus_session(data) or len(data.get("focus_quality_sessions", [])) > 0

        if step_id == "sync":
            return data.get("sync", {}).get("last_cloud_sync") is not None

        return False

    def skip_completed_tour_steps(self):
        skipped_steps = 0

        while self.tour_step_index < len(SETUP_TOUR_STEPS):
            step = self.get_current_tour_step()

            if step.get("manual"):
                break

            if not self.tour_step_is_complete(step):
                break

            self.tour_step_index += 1
            skipped_steps += 1

        return skipped_steps

    def update_tour_guide(self):
        guide = self.query_one("#tour-guide")

        if not self.tour_active:
            guide.display = False
            return

        guide.display = True
        step = self.get_current_tour_step()
        is_complete = self.tour_step_is_complete(step)

        if is_complete:
            status = "[green]Done. Press Done to continue.[/green]"
        elif step.get("optional"):
            status = "[yellow]Optional. Try it now, or continue when ready.[/yellow]"
        elif step.get("manual"):
            status = "[yellow]Read this step, then continue.[/yellow]"
        else:
            status = "[yellow]Waiting for this setup action.[/yellow]"

        self.query_one("#tour-guide-text", Static).update(
            "\n".join([
                f"[bold]Setup Tour {self.tour_step_index + 1}/{len(SETUP_TOUR_STEPS)}: {step['title']}[/bold]",
                step["body"],
                f"[bold]Goal:[/bold] {step['hint']}",
                status,
            ])
        )

        self.query_one("#tour-go-button", Button).label = step["target_label"]
        self.query_one("#tour-done-button", Button).label = "Finish" if step["id"] == "finish" else "Done"
        self.query_one("#tour-done-button", Button).disabled = False

    def advance_tour_step(self, auto=False):
        self.tour_step_index += 1
        self.skip_completed_tour_steps()

        if self.tour_step_index >= len(SETUP_TOUR_STEPS):
            self.complete_setup_tour()
            return

        self.navigate_to_current_tour_step()
        self.update_tour_guide()

        if auto:
            step = self.get_current_tour_step()
            self.show_temp_message(
                "#global-message",
                f"[green]Nice. Next: {step['title']}.[/green]",
            )

    def complete_current_tour_step(self):
        step = self.get_current_tour_step()

        if step["id"] == "finish":
            self.complete_setup_tour()
            return

        if (
            self.tour_step_is_complete(step)
            or step.get("manual")
            or step.get("optional")
        ):
            self.advance_tour_step()
            return

        self.update_tour_guide()
        self.show_temp_message(
            "#global-message",
            f"[yellow]Almost. {step['hint']}[/yellow]",
        )

    def check_tour_progress(self):
        if not self.tour_active or self.checking_tour_progress:
            return

        self.checking_tour_progress = True

        try:
            step = self.get_current_tour_step()

            if (
                not step.get("manual")
                and self.tour_step_is_complete(step)
            ):
                self.advance_tour_step(auto=True)
                return

            self.update_tour_guide()
        finally:
            self.checking_tour_progress = False

    def hide_tour_guide(self):
        self.tour_active = False
        self.query_one("#tour-guide").display = False

    def start_setup_tour(self):
        data = load_data()
        data.setdefault("onboarding", {})
        data["onboarding"]["tour_declined"] = False
        save_local_data_without_sync(data)
        self.tour_active = True
        self.tour_step_index = 0
        self.skip_completed_tour_steps()
        self.navigate_to_current_tour_step()
        self.update_tour_guide()
        self.update_tour_panel()
        self.show_temp_message("#global-message", "[green]Setup tour started.[/green]")

    def dismiss_setup_tour(self):
        data = load_data()
        data.setdefault("onboarding", {})
        data["onboarding"]["tour_declined"] = True
        save_local_data_without_sync(data)
        self.hide_tour_guide()
        self.update_tour_panel()

    def complete_setup_tour(self):
        data = load_data()
        data.setdefault("onboarding", {})
        data["onboarding"]["tour_completed"] = True
        data["onboarding"]["tour_declined"] = False
        save_local_data_without_sync(data)
        self.hide_tour_guide()
        self.update_tour_panel()
        self.show_temp_message("#global-message", "[green]Tour complete. You can replay it in Settings > Tour.[/green]")

    def check_for_updates_in_background(self):
        installed_version = get_installed_version()

        try:
            latest_version = get_latest_package_version()
            update_available = version_is_newer(latest_version, installed_version)
            result = {
                "last_checked": get_utc_now_text(),
                "installed_version": installed_version,
                "latest_version": latest_version,
                "update_available": update_available,
                "last_error": None,
            }
        except ValueError as error:
            result = {
                "last_checked": get_utc_now_text(),
                "installed_version": installed_version,
                "latest_version": None,
                "update_available": False,
                "last_error": str(error),
            }

        self.call_from_thread(self.show_update_check_result, result)

    def show_update_check_result(self, result):
        data = load_data()
        data["update_check"] = result
        save_local_data_without_sync(data)
        self.update_updates_panel()

        if result.get("last_error"):
            self.show_temp_message("#updates-message", f"[red]{result['last_error']}[/red]")
        elif result.get("update_available"):
            self.show_temp_message(
                "#updates-message",
                f"[yellow]Update available: {result['latest_version']}[/yellow]",
            )
        else:
            self.show_temp_message("#updates-message", "[green]StudyStreak is up to date.[/green]")

    def export_data_snapshot(self):
        data = load_data()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        export_path = get_app_data_dir() / f"studystreak-export-{timestamp}.json"

        with open(export_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        self.show_temp_message(
            "#privacy-message",
            f"[green]Exported data to {export_path}[/green]",
            seconds=8,
        )

    def run_data_privacy_action(self, action_id):
        data = load_data()

        if action_id == "clear-focus-quality":
            data["focus_quality_sessions"] = []
            data["sessions"] = [
                session for session in data.get("sessions", [])
                if session.get("source") != "chrome_extension"
            ]
            save_local_data_without_sync(data)
            self.update_dashboard()
            self.show_temp_message(
                "#privacy-message",
                "[yellow]Cleared local browser focus-quality data.[/yellow]",
            )
            return

        if action_id == "reset-local-data":
            fresh_data = get_default_data()
            fresh_data["appearance_settings"] = data.get("appearance_settings", {})
            fresh_data["sound_settings"] = data.get("sound_settings", {})
            fresh_data["notification-settings"] = data.get("notification-settings", {})
            fresh_data["onboarding"] = {
                "tour_completed": True,
                "tour_declined": False,
            }
            save_local_data_without_sync(fresh_data)
            self.update_dashboard()
            self.show_temp_message(
                "#privacy-message",
                "[yellow]Reset local study data for this profile.[/yellow]",
            )
            return


    def stop_session_timers(self):
        #stop background timer when leaving the logged in app
        if self.sync_status_timer is not None:
            self.sync_status_timer.stop()
            self.sync_status_timer = None

        if self.focus_timer is not None:
            self.focus_timer.stop()
            self.focus_timer = None

        self.focus_seconds_left = 0
        self.focus_subject = None
        self.focus_topic = ""
        self.focus_websites = []
        self.focus_minutes = 0
        self.focus_mode = "manual"
        self.pomodoro_phase = "work"
        self.pomodoro_completed_work_blocks = 0
        self.pomodoro_logged_minutes = 0
        self.last_notified_sync_error = None
        self.close_focus_overlay()

        focus_timer = self.query_one("#focus-timer", Static)
        focus_timer.update("")
        focus_timer.display = False

        focus_phase = self.query_one("#focus-phase", Static)
        focus_phase.update("")
        focus_phase.display = False



    def show_main_app(self, offer_tour=False):
        #show main app after login
        login_container = self.query_one("#login-container")
        main_container = self.query_one("#main-container")
        account_label = self.query_one("#account-label", Static)

        username = get_session_username()

        account_label.update(f"[bold]Logged in as:[/bold] [bold]{username}[/bold]")

        login_container.display = False
        main_container.display = True

        self.logged_in = True
        self.apply_theme()
        self.update_server_status()
        self.update_sync_status()
        if self.sync_status_timer is None:
            self.sync_status_timer = self.set_interval(2, self.update_sync_status)
        self.update_dashboard()
        self.refresh_leaderboard()
        if self.chrome_sync_protected_streak:
            self.chrome_sync_protected_streak = False
            achievement_unlocked = self.unlock_earned_achievements()
            data = load_data()
            streak_count = calculate_current_streak(data)
            self.show_temp_message(
                "#global-message",
                "[green]Chrome focus synced. Streak protected.[/green]",
            )
            if not achievement_unlocked:
                self.show_streak_effect(streak_count)

        if offer_tour:
            self.offer_setup_tour_if_needed(force=True)

    def refresh_leaderboard(self):
        #refresh server leaderboard
        leaderboard = self.query_one("#leaderboard", Static)
        leaderboard.update("[yellow]Loading leaderboard...[/yellow]")

        self.run_worker(
            self.load_leaderboard_in_background,
            thread=True,
            exclusive=True,
            group="leaderboard",
        )

    def load_leaderboard_in_background(self):
        #avoid freezing the UI while waiting for the network
        try:
            rows = get_leaderboard(self.leaderboard_period)
        except ValueError:
            self.call_from_thread(self.show_leaderboard_error)
            return

        self.call_from_thread(self.show_leaderboard_rows, rows, self.leaderboard_period)

    def show_leaderboard_error(self):
        leaderboard = self.query_one("#leaderboard", Static)
        leaderboard.update("[red]Could not load leaderboard.[/red]")

    def show_leaderboard_rows(self, rows, period):
        leaderboard = self.query_one("#leaderboard", Static)

        if len(rows) == 0:
            leaderboard.update("[yellow]No leaderboard data yet.[/yellow]")
            return
        
        period_titles = {
            "today": "Today",
            "week": "This week",
            "all": "All Time",
        }

        lines = [f"[bold]{period_titles[period]} Leaderboard[/bold]"]

        for index, row in enumerate(rows, start=1):
            current_streak = row.get("current_streak", 0)
            streak_word = "day" if current_streak == 1 else "days"

            lines.append(
                f"{index}. {row['display_name']} - {row['total_minutes']} minutes "
                f"- Streak {current_streak} {streak_word}"
            )
        leaderboard.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        
        self.play_ui_sound()

        if event.button.id == "home-prepare-focus-button":
            self.prepare_recommended_focus(play_sound_effect=False)
            return

        if event.button.id == "home-open-focus-button":
            self.set_main_tab("focus-tab")
            self.focus_tour_widget("#focus-minutes-input")
            return

        if event.button.id == "home-skip-action-button":
            self.skip_home_action(play_sound_effect=False)
            return

        if event.button.id == "tour-go-button":
            self.navigate_to_current_tour_step()
            self.update_tour_guide()
            return

        if event.button.id == "tour-done-button":
            self.complete_current_tour_step()
            return

        if event.button.id == "tour-skip-button":
            self.advance_tour_step()
            return

        if event.button.id == "tour-end-button":
            self.dismiss_setup_tour()
            self.show_temp_message("#global-message", "[yellow]Tour ended. You can replay it in Settings > Tour.[/yellow]")
            return

        if event.button.id == "logout-button":
            #logout from Textual UI
            login_container = self.query_one("#login-container")
            main_container = self.query_one("#main-container")
            username_input = self.query_one("#login-username-input", Input)
            password_input = self.query_one("#login-password-input", Input)


            self.stop_session_timers()
            logout_account()
            clear_session()
            clear_remembered_login()

            self.logged_in = False
            self.hide_tour_guide()

            username_input.value = ""
            password_input.value = ""

            main_container.display = False
            login_container.display = True

            self.show_temp_message("#login-message", "[yellow]Logged out.[/yellow]")
            return
        
        if event.button.id == "login-button":
            username_input = self.query_one("#login-username-input", Input)
            password_input = self.query_one("#login-password-input", Input)

            username = username_input.value.strip()
            password = password_input.value

            if username == "":
                self.show_temp_message("#login-message", "[red]Please enter your username.[/red]")
                return

            if password == "":
                self.show_temp_message("#login-message", "[red]Please enter your password.[/red]")
                return

            try:
                private_data = login_account(username, password)
                set_session(username, password, private_data)

                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)

                    cloud_data = self.sync_profile_from_server(username, password, server_token)

                    self.use_newest_profile_after_login(
                        username,
                        password,
                        private_data,
                        cloud_data,
                    )
                    self.sync_subject_websites_from_server(server_token)
                    self.sync_subject_topics_from_server(server_token)
                    self.sync_todo_items_from_server(server_token)
                    self.sync_browser_focus_sessions_from_server(server_token)
                    self.sync_focus_quality_from_server(server_token)

                except ValueError:
                    self.show_temp_message(
                        "#login-message",
                        "[yellow]Local login worked, but server login failed.[/yellow]",
                    )

            except ValueError:
                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)
                    cloud_data = self.sync_profile_from_server(username, password, server_token)

                except ValueError:
                    self.show_temp_message(
                        "#login-message",
                        "[red]Username or password is incorrect.[/red]",
                    )
                    return

                try:
                    create_account(username=username, password=password)
                except ValueError:
                    self.show_temp_message(
                        "#login-message",
                        "[red]Could not import server account locally.[/red]",
                    )
                    return

                private_data = login_account(username, password)

                self.use_newest_profile_after_login(
                    username,
                    password,
                    private_data,
                    cloud_data,
                    prefer_cloud_when_equal=True,
                )
                self.sync_subject_websites_from_server(server_token)
                self.sync_subject_topics_from_server(server_token)
                self.sync_todo_items_from_server(server_token)
                self.sync_browser_focus_sessions_from_server(server_token)
                self.sync_focus_quality_from_server(server_token)

                self.show_temp_message(
                    "#login-message",
                    "[yellow]Server account imported locally.[/yellow]",
                )

            remember_checkbox = self.query_one("#remember-me-checkbox", Checkbox)

            if remember_checkbox.value:
                save_remembered_login(username, password)
            else:
                clear_remembered_login()

            password_input.value = ""
            self.show_temp_message("#login-message", "[green]Login successful.[/green]")
            self.show_main_app()
            return

        if event.button.id == "create-account-button":
            username_input = self.query_one("#login-username-input", Input)
            password_input = self.query_one("#login-password-input", Input)

            username = username_input.value.strip()
            password = password_input.value

            if username == "":
                self.show_temp_message("#login-message", "[red]Please enter a username.[/red]")
                return

            if password == "":
                self.show_temp_message("#login-message", "[red]Please enter a password.[/red]")
                return

            try:
                username = normalise_username(username)
                validate_username(username)
                validate_password(password)

                if username in list_accounts():
                    self.show_temp_message("#login-message", "[red]That username already exists locally.[/red]")
                    return

                create_account(username=username, password=password)
                private_data = login_account(username, password)
                set_session(username, password, private_data)

            except ValueError as error:
                self.show_temp_message("#login-message", f"[red]{error}[/red]")
                return

            cloud_message = "[green]Account created and logged in.[/green]"

            try:
                signup_to_server(username, password)
                server_token = login_to_server(username, password)
                set_server_token(server_token)
                save_data(private_data)
                self.sync_subject_websites_from_server(server_token)
                self.sync_subject_topics_from_server(server_token)
                self.sync_todo_items_from_server(server_token)
                self.sync_browser_focus_sessions_from_server(server_token)
                self.sync_focus_quality_from_server(server_token)

            except ValueError as signup_error:
                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)
                    save_data(private_data)
                    self.sync_subject_websites_from_server(server_token)
                    self.sync_subject_topics_from_server(server_token)
                    self.sync_todo_items_from_server(server_token)
                    self.sync_browser_focus_sessions_from_server(server_token)
                    self.sync_focus_quality_from_server(server_token)
                    cloud_message = "[green]Account created and linked to existing cloud login.[/green]"

                except ValueError:
                    cloud_message = (
                        "[yellow]Account created on this device. "
                        f"Cloud signup failed: {signup_error}[/yellow]"
                    )

            remember_checkbox = self.query_one("#remember-me-checkbox", Checkbox)

            if remember_checkbox.value:
                save_remembered_login(username, password)
            else:
                clear_remembered_login()

            password_input.value = ""
            self.show_temp_message("#login-message", cloud_message)
            self.show_main_app(offer_tour=True)
            return

        settings_panel_by_button = {
            "settings-weekly-button": "#weekly-goal-panel",
            "settings-health-button": "#setup-health-panel",
            "settings-sync-button": "#sync-panel",
            "settings-tour-button": "#tour-panel",
            "settings-updates-button": "#updates-panel",
            "settings-extension-button": "#extension-panel",
            "settings-appearance-button": "#appearance-panel",
            "settings-sounds-button": "#sounds-panel",
            "settings-subjects-button": "#subjects-panel",
            "settings-privacy-button": "#privacy-panel",
            "settings-focus-import-button": "#focus-import-panel",
        }

        if event.button.id in settings_panel_by_button:
            self.show_settings_panel(settings_panel_by_button[event.button.id])
            return

        if event.button.id == "start-tour-button":
            self.start_setup_tour()
            return

        if event.button.id == "mark-tour-complete-button":
            self.complete_setup_tour()
            self.show_temp_message("#tour-message", "[green]Tour marked complete.[/green]")
            return

        if event.button.id == "check-update-button":
            self.query_one("#updates-message", Static).display = True
            self.query_one("#updates-message", Static).update("[yellow]Checking PyPI...[/yellow]")
            self.run_worker(
                self.check_for_updates_in_background,
                thread=True,
                exclusive=True,
                group="update-check",
            )
            return

        if event.button.id == "open-extension-guide-button":
            webbrowser.open("https://github.com/Chi-ChunL/StudyStreak#browser-extension")
            self.show_temp_message("#extension-message", "[green]Opened extension guide.[/green]")
            return

        if event.button.id == "export-data-button":
            self.export_data_snapshot()
            return

        if event.button.id == "clear-focus-quality-data-button":
            self.push_screen(
                DataActionConfirmScreen(
                    "clear-focus-quality",
                    "Clear browser focus data?",
                    "This removes local Chrome/Firefox focus-quality summaries and synced browser focus sessions from this profile.",
                    "Clear Data",
                )
            )
            return

        if event.button.id == "reset-local-data-button":
            self.push_screen(
                DataActionConfirmScreen(
                    "reset-local-data",
                    "Reset local study data?",
                    "This clears study sessions, subjects, timetable, focus summaries, and achievements for this local profile. It does not directly delete cloud data.",
                    "Reset Local Data",
                )
            )
            return

        if event.button.id == "sync-now-button":
            try:
                subject_sync_result = self.sync_subject_websites_from_server()
                subject_topic_sync_result = self.sync_subject_topics_from_server()
                todo_sync_result = self.sync_todo_items_from_server()
                browser_session_sync_result = self.sync_browser_focus_sessions_from_server()
                data = load_data()
                save_data(data)
                sync_result = self.sync_focus_quality_from_server()
            except ValueError as error:
                self.update_sync_status()
                self.show_temp_message("#sync-message", f"[red]{error}[/red]")
                return

            subject_website_updates = subject_sync_result["updates"]
            subject_topic_updates = subject_topic_sync_result["updates"]
            todo_updates = todo_sync_result["updates"]
            browser_session_updates = browser_session_sync_result["updates"]
            added_count = sync_result["updates"]
            streak_protected = sync_result["streak_protected"]
            self.update_sync_status()
            if (
                added_count > 0
                or subject_website_updates > 0
                or subject_topic_updates > 0
                or todo_updates > 0
                or browser_session_updates > 0
            ):
                self.update_dashboard()
                achievement_unlocked = self.unlock_earned_achievements()
                if streak_protected:
                    self.chrome_sync_protected_streak = False
                    data = load_data()
                    streak_count = calculate_current_streak(data)
                    self.show_temp_message(
                        "#sync-message",
                        "[green]Chrome focus synced. Streak protected.[/green]",
                    )
                    if not achievement_unlocked:
                        self.show_streak_effect(streak_count)
                    return

                message_parts = []

                if added_count > 0:
                    message_parts.append(f"{added_count} Chrome focus update(s)")

                if subject_website_updates > 0:
                    message_parts.append(f"{subject_website_updates} subject website set(s)")

                if subject_topic_updates > 0:
                    message_parts.append(f"{subject_topic_updates} subject topic set(s)")

                if browser_session_updates > 0:
                    message_parts.append(f"{browser_session_updates} browser session log(s)")

                if todo_updates > 0:
                    message_parts.append(f"{todo_updates} todo update(s)")

                self.show_temp_message(
                    "#sync-message",
                    f"[green]Sync started. Updated {', '.join(message_parts)}.[/green]",
                )
            else:
                self.show_temp_message(
                    "#sync-message",
                    "[yellow]Sync started. No new browser updates.[/yellow]",
                )
            self.set_timer(2, self.update_sync_status)
            return
 
        if event.button.id == "subject-add-tab":
            subject_add_panel = self.query_one("#subject-add-panel")
            subject_edit_panel = self.query_one("#subject-edit-panel")
            subject_delete_panel = self.query_one("#subject-delete-panel")
 
            subject_add_panel.display = True
            subject_edit_panel.display = False
            subject_delete_panel.display = False
            return
 
        if event.button.id == "subject-edit-tab":
            subject_add_panel = self.query_one("#subject-add-panel")
            subject_edit_panel = self.query_one("#subject-edit-panel")
            subject_delete_panel = self.query_one("#subject-delete-panel")
 
            subject_add_panel.display = False
            subject_edit_panel.display = True
            subject_delete_panel.display = False
            return
 
        if event.button.id == "subject-delete-tab":
            subject_add_panel = self.query_one("#subject-add-panel")
            subject_edit_panel = self.query_one("#subject-edit-panel")
            subject_delete_panel = self.query_one("#subject-delete-panel")
 
            subject_add_panel.display = False
            subject_edit_panel.display = False
            subject_delete_panel.display = True
            return

        if event.button.id == "sessions-log-tab-button":
            self.show_sessions_panel("log")
            return

        if event.button.id == "sessions-manage-tab-button":
            self.show_sessions_panel("manage")
            return
 
        if event.button.id == "clear-button":
            subject_select = self.query_one("#subject-select", Select)
            log_topic_select = self.query_one("#log-topic-select", Select)
            minutes_input = self.query_one("#minutes-input", Input)
            note_input = self.query_one("#manual-session-note-input", TextArea)
            message = self.query_one("#message", Static)
 
            subject_select.clear()
            log_topic_select.set_options([])
            log_topic_select.clear()
            minutes_input.value = ""
            note_input.load_text("")
            message.update("")
            message.display = False
            return
 
        if event.button.id == "delete-selected-button":
            session_select = self.query_one("#session-select", Select)
 
            selected_index = session_select.value
            data = load_data()
 
            if len(data["sessions"]) == 0:
                self.show_temp_message("#manage-message", "[yellow]There are no sessions to delete.[/yellow]")
                self.update_dashboard()
                return
 
            selected_index = get_select_index(selected_index)

            if selected_index is None:
                self.show_temp_message("#manage-message", "[yellow]Please select a session to delete.[/yellow]")
                return
 
            if selected_index < 0 or selected_index >= len(data["sessions"]):
                self.show_temp_message("#manage-message", "[red]Selected session could not be found.[/red]")
                self.update_dashboard()
                return
 
            deleted_session = data["sessions"].pop(selected_index)
            save_data(data)

            server_token = get_server_token()
            cloud_session_id = deleted_session.get("cloud_focus_session_id")

            if server_token is not None and cloud_session_id is not None:
                self.run_worker(
                    partial(
                        self.delete_focus_session_in_background,
                        server_token,
                        cloud_session_id,
                    ),
                    thread=True,
                    group="focus-delete",
                )
 
            subject = deleted_session["subject"]
            minutes = deleted_session["minutes"]
            session_date = deleted_session["date"]
 
            self.update_dashboard()
 
            self.show_temp_message(
                "#manage-message",
                f"[yellow]Deleted: {session_date} - {subject} - {minutes} minutes.[/yellow]",
            )
            return

        if event.button.id == "save-session-edit-button":
            session_select = self.query_one("#session-select", Select)
            subject_select = self.query_one("#edit-session-subject-select", Select)
            minutes_input = self.query_one("#edit-session-minutes-input", Input)
            topic_input = self.query_one("#edit-session-topic-input", Input)
            note_input = self.query_one("#edit-session-note-input", TextArea)

            selected_index = get_select_index(session_select.value)

            if selected_index is None:
                self.show_temp_message("#manage-message", "[yellow]Please select a session to edit.[/yellow]")
                return

            data = load_data()

            if selected_index < 0 or selected_index >= len(data["sessions"]):
                self.show_temp_message("#manage-message", "[red]Selected session could not be found.[/red]")
                self.update_dashboard()
                return

            subject = subject_select.value
            minutes_text = minutes_input.value.strip()
            topic = topic_input.value.strip()
            note = note_input.text.strip()

            if is_blank_select_value(subject):
                self.show_temp_message("#manage-message", "[red]Please choose a subject.[/red]")
                return

            if not minutes_text.isdigit():
                self.show_temp_message("#manage-message", "[red]Minutes must be a whole number.[/red]")
                return

            minutes = int(minutes_text)

            if minutes <= 0:
                self.show_temp_message("#manage-message", "[red]Minutes must be more than 0.[/red]")
                return

            session = data["sessions"][selected_index]
            session["subject"] = str(subject).lower()
            session["minutes"] = minutes

            if topic:
                session["topic"] = topic
            else:
                session.pop("topic", None)

            if note:
                session["note"] = note
            else:
                session.pop("note", None)

            save_data(data)

            server_token = get_server_token()

            if server_token is not None and session.get("completed_at"):
                upload_source = (
                    "chrome_extension"
                    if session.get("source") == "chrome_extension"
                    else "focus_cli"
                )
                self.run_worker(
                    partial(
                        self.upload_focus_session_in_background,
                        server_token,
                        session["subject"],
                        minutes,
                        session.get("topic", ""),
                        session.get("completed_at"),
                        session.get("note", ""),
                        upload_source,
                    ),
                    thread=True,
                    group="focus-upload",
                )

            self.update_dashboard()
            self.show_sessions_panel("manage")
            self.show_temp_message("#manage-message", "[green]Session updated.[/green]")
            return
 
        if event.button.id == "save-goal-button":
            goal_input = self.query_one("#weekly-goal-input", Input)
 
            goal_text = goal_input.value.strip()
 
            if goal_text == "":
                self.show_temp_message("#settings-message", "[red]Please enter a weekly goal.[/red]")
                return
 
            if not goal_text.isdigit():
                self.show_temp_message("#settings-message", "[red]Weekly goal must be a whole number.[/red]")
                return
 
            weekly_goal = int(goal_text)
 
            if weekly_goal <= 0:
                self.show_temp_message("#settings-message", "[red]Weekly goal must be more than 0.[/red]")
                return

            data = load_data()
            data["weekly_goal"] = weekly_goal
            save_data(data)
 
            self.update_dashboard()
 
            self.show_temp_message(
                "#settings-message",
                f"[green]Weekly goal updated to {weekly_goal} minutes.[/green]",
            )
 
            goal_input.value = ""
            return
 
        if event.button.id == "add-subject-button":
            new_subject_input = self.query_one("#new-subject-input", Input)
            new_subject_website_input = self.query_one("#new-subject-website-input", TextArea)
            new_subject_topic_input = self.query_one("#new-subject-topic-input", TextArea)
 
            new_subject = new_subject_input.value.strip().lower()
            websites = clean_website_list(new_subject_website_input.text)
            topics = clean_topic_list(new_subject_topic_input.text)
 
            if new_subject == "":
                self.show_temp_message("#subject-message", "[red]Please enter a subject name.[/red]")
                return
 
            data = load_data()
 
            if new_subject in data["subjects"]:
                self.show_temp_message("#subject-message", "[yellow]That subject already exists.[/yellow]")
                return
 
            data["subjects"].append(new_subject)
            data["subjects"].sort()
 
            data["subject_websites"][new_subject] = websites
            data["subject_topics"][new_subject] = topics
 
            save_data(data)
 
            self.update_dashboard()
            self.unlock_earned_achievements()
 
            if len(websites) == 0 and len(topics) == 0:
                self.show_temp_message("#subject-message", f"[green]Added subject: {new_subject}[/green]")
            else:
                self.show_temp_message(
                    "#subject-message",
                    (
                        f"[green]Added subject: {new_subject} with "
                        f"{len(websites)} website(s) and {len(topics)} topic(s).[/green]"
                    ),
                )
 
            new_subject_input.value = ""
            new_subject_website_input.load_text("")
            new_subject_topic_input.load_text("")
            return
 
        if event.button.id == "update-website-button":
            edit_website_subject_select = self.query_one("#edit-website-subject-select", Select)
            edit_website_input = self.query_one("#edit-website-input", TextArea)
            edit_topic_input = self.query_one("#edit-topic-input", TextArea)
 
            selected_subject = edit_website_subject_select.value
            websites = clean_website_list(edit_website_input.text)
            topics = clean_topic_list(edit_topic_input.text)
 
            if is_blank_select_value(selected_subject):
                self.show_temp_message("#edit-website-message", "[yellow]Please choose a subject first.[/yellow]")
                return
 
            data = load_data()
 
            if str(selected_subject) not in data["subjects"]:
                self.show_temp_message("#edit-website-message", "[red]That subject could not be found.[/red]")
                self.update_dashboard()
                return
 
            data["subject_websites"][str(selected_subject)] = websites
            data["subject_topics"][str(selected_subject)] = topics
            save_data(data)
 
            self.update_dashboard()
 
            if len(websites) == 0 and len(topics) == 0:
                self.show_temp_message(
                    "#edit-website-message",
                    f"[yellow]Cleared websites and topics for {selected_subject}.[/yellow]",
                )
            else:
                self.show_temp_message(
                    "#edit-website-message",
                    (
                        f"[green]Updated {selected_subject} with "
                        f"{len(websites)} website(s) and {len(topics)} topic(s).[/green]"
                    ),
                )
 
            return
 
        if event.button.id == "delete-subject-button":
            delete_subject_select = self.query_one("#delete-subject-select", Select)
 
            selected_subject = delete_subject_select.value
 
            if is_blank_select_value(selected_subject):
                self.show_temp_message("#delete-subject-message", "[yellow]Please choose a subject to delete.[/yellow]")
                return
 
            self.push_screen(DeleteSubjectConfirmScreen(str(selected_subject)))
            return
 
        if event.button.id == "open-website-button":
            self.open_focus_websites()
            return
        
        if event.button.id == "show-timetable-form-button":
            #show timetable form
            self.editing_timetable_index = None
            self.query_one("#add-timetable-button", Button).label = "Save Session"
            self.query_one("#timetable-subject-select", Select).clear()
            self.query_one("#timetable-day-select", Select).clear()
            self.query_one("#timetable-start-input", Input).value = ""
            self.query_one("#timetable-minutes-input", Input).value = ""
            timetable_form_panel = self.query_one("#timetable-form-panel")
            timetable_form_panel.display = True
            return
        
        if event.button.id == "hide-timetable-form-button":
            #hide timetable form
            timetable_form_panel = self.query_one("#timetable-form-panel")
            timetable_form_panel.display = False
            self.editing_timetable_index = None
            self.query_one("#add-timetable-button", Button).label = "Save Session"
            return

        if event.button.id == "edit-timetable-button":
            select = self.query_one("#manage-timetable-select", Select)
            selected_index = select.value

            selected_index = get_select_index(selected_index)

            if selected_index is None:
                self.show_temp_message(
                    "#timetable-message",
                    "[yellow]Please choose a planned session to edit.[/yellow]",
                )
                return

            self.editing_timetable_index = selected_index
            data = load_data()

            if (
                self.editing_timetable_index < 0
                or self.editing_timetable_index >= len(data["timetable"])
            ):
                self.show_temp_message(
                    "#timetable-message",
                    "[red]That planned session could not be found.[/red]",
                )
                self.editing_timetable_index = None
                self.update_dashboard()
                return

            item = data["timetable"][self.editing_timetable_index]

            self.query_one("#timetable-subject-select", Select).value = item["subject"]
            self.query_one("#timetable-day-select", Select).value = item["day"]
            self.query_one("#timetable-start-input", Input).value = item["start_time"]
            self.query_one("#timetable-minutes-input", Input).value = str(item["minutes"])
            self.query_one("#add-timetable-button", Button).label = "Save Changes"
            self.query_one("#timetable-form-panel").display = True
            return

        if event.button.id == "delete-timetable-button":
            manage_timetable_select = self.query_one("#manage-timetable-select", Select)
            selected_index = manage_timetable_select.value

            selected_index = get_select_index(selected_index)

            if selected_index is None:
                self.show_temp_message(
                    "#timetable-message",
                    "[yellow]Please choose a planned session to delete.[/yellow]",
                )
                return

            data = load_data()

            if selected_index < 0 or selected_index >= len(data["timetable"]):
                self.show_temp_message(
                    "#timetable-message",
                    "[red]That planned session could not be found.[/red]",
                )
                self.update_dashboard()
                return

            deleted_item = data["timetable"].pop(selected_index)
            save_data(data)
            self.editing_timetable_index = None
            self.query_one("#add-timetable-button", Button).label = "Save Session"
            self.query_one("#timetable-form-panel").display = False
            self.update_dashboard()

            self.show_temp_message(
                "#timetable-message",
                f"[yellow]Deleted {deleted_item['subject'].title()} "
                f"on {deleted_item['day']} at {deleted_item['start_time']}.[/yellow]",
            )
            return

        if event.button.id == "add-timetable-button":
            #add timetable session
            subject_select = self.query_one("#timetable-subject-select", Select)
            day_select = self.query_one("#timetable-day-select", Select)
            start_input = self.query_one("#timetable-start-input", Input)
            minutes_input = self.query_one("#timetable-minutes-input", Input)

            subject = subject_select.value
            day = day_select.value
            start_time = start_input.value.strip()
            minutes_text = minutes_input.value.strip()

            if is_blank_select_value(subject):
                self.show_temp_message("#timetable-message", "[red]Please choose a subject.[/red]")
                return

            if is_blank_select_value(day):
                self.show_temp_message("#timetable-message", "[red]Please choose a day.[/red]")
                return

            if start_time == "":
                self.show_temp_message("#timetable-message", "[red]Please enter a start time.[/red]")
                return

            if len(start_time) != 5 or start_time[2] != ":":
                self.show_temp_message("#timetable-message", "[red]Use time format HH:MM.[/red]")
                return
            
            hour_text = start_time[:2]
            minute_text = start_time[3:]

            if not hour_text.isdigit() or not minute_text.isdigit():
                self.show_temp_message("#timetable-message", "[red]Start time must be numbers, e.g. 17:00.[/red]")
                return
            hour = int(hour_text)
            minute = int(minute_text)

            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                self.show_temp_message("#timetable-message", "[red]Please enter a valid time.[/red]")
                return

            if minutes_text == "":
                self.show_temp_message("#timetable-message", "[red]Please enter a duration.[/red]")
                return

            if not minutes_text.isdigit():
                self.show_temp_message("#timetable-message", "[red]Duration must be a whole number.[/red]")
                return

            minutes = int(minutes_text)

            if minutes <= 0:
                self.show_temp_message("#timetable-message", "[red]Duration must be more than 0.[/red]")
                return
            
            data = load_data()

            new_day = normalise_timetable_day(str(day))
            new_start_minutes = hour * 60 + minute
            new_end_minutes = new_start_minutes + minutes

            if new_end_minutes > 24 * 60:
                self.show_temp_message(
                    "#timetable-message",
                    "[red]Timetable sessions cannot continue past midnight.[/red]",
                )
                return
            
            for existing_index, existing_item in enumerate(data.get("timetable", [])):
                if existing_index == self.editing_timetable_index:
                    continue

                existing_day = normalise_timetable_day(existing_item["day"])

                if existing_day != new_day:
                    continue

                existing_start_time = existing_item["start_time"]
                existing_hour = int(existing_start_time[:2])
                existing_minute = int(existing_start_time[3:])

                existing_start_minutes = existing_hour * 60 + existing_minute
                existing_end_minutes = existing_start_minutes + existing_item["minutes"]

                sessions_overlap = (
                    new_start_minutes < existing_end_minutes
                    and existing_start_minutes < new_end_minutes
                )

                if sessions_overlap:
                    existing_subject = existing_item["subject"].title()
                    existing_end_time = get_timetable_end_time(
                        existing_start_time,
                        existing_item["minutes"],
                    )

                    self.show_temp_message(
                        "#timetable-message",
                        f"[red]That overlaps with {existing_subject}: "
                        f"{existing_start_time} - {existing_end_time}.[/red]",
                    )
                    return

            timetable_item = {
                "subject": str(subject).lower(),
                "day": new_day,
                "start_time": start_time,
                "minutes": minutes,
            }

            was_editing = self.editing_timetable_index is not None

            if was_editing:
                if (
                    self.editing_timetable_index < 0
                    or self.editing_timetable_index >= len(data["timetable"])
                ):
                    self.show_temp_message(
                        "#timetable-message",
                        "[red]That planned session could not be found.[/red]",
                    )
                    self.editing_timetable_index = None
                    self.query_one("#add-timetable-button", Button).label = "Save Session"
                    self.update_dashboard()
                    return

                data["timetable"][self.editing_timetable_index] = timetable_item
            else:
                data["timetable"].append(timetable_item)

            save_data(data)

            self.update_dashboard()
            self.unlock_earned_achievements()

            subject_select.clear()
            day_select.clear()
            start_input.value = ""
            minutes_input.value = ""

            action = "Updated" if was_editing else "Added"
            self.editing_timetable_index = None
            self.query_one("#add-timetable-button", Button).label = "Save Session"

            self.show_temp_message(
                "#timetable-message",
                f"[green]{action} {subject} on {day} at {start_time}.[/green]",
            )

            timetable_form_panel = self.query_one("#timetable-form-panel")
            timetable_form_panel.display = False
            return
        

        if event.button.id == "start-focus-button":
            focus_subject_select = self.query_one("#focus-subject-select", Select)
            focus_topic_select = self.query_one("#focus-topic-select", Select)
            focus_minutes_input = self.query_one("#focus-minutes-input", Input)
            pomodoro_checkbox = self.query_one("#pomodoro-mode-checkbox", Checkbox)
 
            subject = focus_subject_select.value
            topic = "" if is_blank_select_value(focus_topic_select.value) else str(focus_topic_select.value)
            minutes_text = focus_minutes_input.value.strip()
            pomodoro_mode = pomodoro_checkbox.value
 
            if is_blank_select_value(subject):
                self.show_temp_message("#focus-message", "[red]Please choose a subject.[/red]")
                return

            if pomodoro_mode:
                self.start_focus_session(
                    str(subject),
                    POMODORO_WORK_MINUTES,
                    pomodoro_mode=True,
                    topic=topic,
                )
                return
 
            if minutes_text == "":
                self.show_temp_message("#focus-message", "[red]Please enter a focus duration.[/red]")
                return
 
            if not minutes_text.isdigit():
                self.show_temp_message("#focus-message", "[red]Focus duration must be a whole number.[/red]")
                return
 
            minutes = int(minutes_text)
 
            if minutes <= 0:
                self.show_temp_message("#focus-message", "[red]Focus duration must be more than 0.[/red]")
                return
 
            self.start_focus_session(str(subject), minutes, topic=topic)
            return

        if event.button.id == "save-focus-import-secret-button":
            secret_input = self.query_one("#focus-import-secret-input", Input)
            secret = secret_input.value.strip()

            if secret == "":
                self.show_temp_message("#focus-quality-message", "[red]Import key cannot be empty.[/red]")
                return
            
            data = load_data()
            data["focus_import_settings"]["secret"] = secret
            save_data(data)

            secret_input.value = ""
            self.update_dashboard()
            self.show_temp_message("#focus-quality-message", "[green]Focus import key saved.[/green]")
            return

        if event.button.id == "import-focus-json-button":
            focus_json_input = self.query_one("#focus-quality-json-input", TextArea)
            raw_summary = focus_json_input.text.strip()

            try:
                session = save_focus_quality_json(raw_summary)
            except ValueError as error:
                self.show_temp_message("#focus-quality-message", f"[red]{error}[/red]")
                return

            focus_json_input.load_text("")
            self.update_dashboard()
            self.show_temp_message(
                "#focus-quality-message",
                f"[green]Imported Chrome focus summary with {session['score']}% quality.[/green]",
            )
            return

        if event.button.id == "clear-focus-json-button":
            focus_json_input = self.query_one("#focus-quality-json-input", TextArea)
            focus_json_input.load_text("")
            self.show_temp_message("#focus-quality-message", "[yellow]Focus JSON cleared.[/yellow]")
            return

        if event.button.id == "settings-focus-import-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            appearance_panel = self.query_one("#appearance-panel")
            focus_import_panel = self.query_one("#focus-import-panel")

            weekly_goal_panel.display = False
            subjects_panel.display = False
            sync_panel.display = False
            sounds_panel.display = False
            appearance_panel.display = False
            focus_import_panel.display = True
            self.update_dashboard()
            return

        if event.button.id == "leaderboard-today-button":
            #show today's leaderboard
            self.leaderboard_period = "today"
            self.refresh_leaderboard()
            return
        
        if event.button.id == "leaderboard-week-button":
            #show weekly leaderboard 
            self.leaderboard_period = "week"
            self.refresh_leaderboard()
            return
        
        if event.button.id == "leaderboard-all-button":
            #show all-time leaderboard
            self.leaderboard_period = "all"
            self.refresh_leaderboard()
            return

        if event.button.id == "refresh-leaderboard-button":
            #refresh leaderboard button
            self.refresh_leaderboard()
            return

        if event.button.id == "cancel-focus-button":
            self.cancel_focus_session()
            return

        if event.button.id == "log-button":
            subject_select = self.query_one("#subject-select", Select)
            topic_select = self.query_one("#log-topic-select", Select)
            minutes_input = self.query_one("#minutes-input", Input)
            note_input = self.query_one("#manual-session-note-input", TextArea)
            message = self.query_one("#message", Static)
 
            subject = subject_select.value
            topic_value = topic_select.value
            topic = "" if is_blank_select_value(topic_value) else str(topic_value)
            minutes_text = minutes_input.value.strip()
            note = note_input.text.strip()
 

            if is_blank_select_value(subject):
                self.show_temp_message("#message", "[red]Please choose a subject.[/red]")
                return
 
            if minutes_text == "":
                self.show_temp_message("#message", "[red]Please enter the number of minutes.[/red]")
                return
 
            if not minutes_text.isdigit():
                self.show_temp_message("#message", "[red]Minutes must be a whole number.[/red]")
                return
 
            minutes = int(minutes_text)
 
            if minutes <= 0:
                self.show_temp_message("#message", "[red]Minutes must be more than 0.[/red]")
                return
 
            data = load_data()
            already_studied_today = has_studied_today(data)
 
            session = {
                "subject": str(subject).lower(),
                "minutes": minutes,
                "date": str(date.today()),
                "source": "manual",
                "completed_at": get_utc_now_text(),
            }

            if topic:
                session["topic"] = topic

            if note:
                session["note"] = note
 
            data["sessions"].append(session)
            protect_streak_today(data)
            save_data(data)
 
            self.update_dashboard()
            achievement_unlocked = self.unlock_earned_achievements()

            updated_data = load_data()
            streak_count = calculate_current_streak(updated_data)

            if not already_studied_today and not achievement_unlocked:
                self.show_streak_effect(streak_count)
 
            self.show_temp_message("#message", f"[green]Logged {minutes} minutes of {subject} study.[/green]")
 
            subject_select.clear()
            topic_select.set_options([])
            topic_select.clear()
            minutes_input.value = ""
            note_input.load_text("")
            return
