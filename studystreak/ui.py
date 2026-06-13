import webbrowser
from datetime import date, timedelta, datetime
from functools import partial

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
    clean_website_list,
    load_data,
    merge_focus_quality_sessions,
    protect_streak_today,
    repair_data,
    save_data,
    save_focus_quality_json,
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
    upload_focus_session, 
    get_leaderboard,
    check_server_status,
    get_profile_data,
    get_focus_quality_sessions,
)
from studystreak.profile_sync import decrypt_profile_data
from studystreak.notification import (
    play_sound,
    show_focus_complete_notification,
    show_sync_failed_notification,
    show_achievement_notification,
)
from studystreak.paths import get_app_data_dir



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
 
    return "[yellow]Keep going[/yellow]"
 
 
def has_studied_today(data):
    today_date = str(date.today())
    return today_date in data.get("streak_days", [])
 
 
def get_recent_sessions(data, limit=5):
    sessions = data["sessions"]
 
    if len(sessions) == 0:
        return (
            "[bold]Recent study sessions[/bold]\n"
            "No sessions yet.\n"
            "Next: open Log Session or Focus Mode to record your first study block."
        )
 
    recent_sessions = sessions[-limit:]
    recent_sessions.reverse()
 
    lines = ["[bold]Recent study sessions[/bold]"]
 
    for session in recent_sessions:
        subject = session["subject"]
        minutes = session["minutes"]
        session_date = session["date"]
 
        lines.append(f"{subject} - {minutes} minutes - {session_date}")
 
    return "\n".join(lines)
 
 
def get_session_options(data):
    sessions = data["sessions"]
 
    options = []
 
    for index, session in enumerate(sessions):
        subject = session["subject"]
        minutes = session["minutes"]
        session_date = session["date"]
 
        label = f"{session_date} - {subject} - {minutes} minutes"
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

    for session in sessions:
        subject = session["subject"]
        minutes = session["minutes"]

        if subject not in subject_total:
            subject_total[subject] = 0

        subject_total[subject] += minutes

    focus_by_subject = {}

    for session in focus_sessions:
        subject = session.get("subject", "unknown")
        focused_seconds = session.get("focused_seconds", 0)
        score = session.get("score", 0)

        if subject not in focus_by_subject:
            focus_by_subject[subject] = {
                "sessions": 0,
                "focused_seconds": 0,
                "total_score": 0,
            }

        focus_by_subject[subject]["sessions"] += 1
        focus_by_subject[subject]["focused_seconds"] += focused_seconds
        focus_by_subject[subject]["total_score"] += score

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

        lines.append(f"{subject} - {time_text}")

        focus_stats = focus_by_subject.get(subject)

        if focus_stats:
            focus_minutes = focus_stats["focused_seconds"] // 60
            average_score = focus_stats["total_score"] // focus_stats["sessions"]

            lines.append(
                f"  Chrome focus - {focus_minutes}m focused, "
                f"{average_score}% average quality"
            )

    return "\n".join(lines)
 
def is_blank_select_value(value):
    return (
        value is None
        or value is False
        or str(value).lower() in ["", "none", "null", "select.null", "select.blank"]
    )

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
    status = "[green]Done[/green]" if done else "[yellow]Next[/yellow]"
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
    focus_minutes = 0
    logged_in = False
    temp_message_versions = {}
    leaderboard_period = "all"
    last_notified_sync_error = None
    editing_timetable_index = None
    chrome_sync_protected_streak = False
    server_is_online = None
 
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
            

            with TabbedContent(initial="dashboard-tab"):
                with TabPane("Dashboard", id="dashboard-tab"):
                    yield Static("", id="setup-checklist")
                    yield Static("", id="dashboard")
                    yield Static("", id="recent-sessions")
 
                with TabPane("Subject Stats", id="subject-stats-tab"):
                    yield Static("", id="subject-stats")
 
                with TabPane("Log Session", id="log-tab"):
                    yield Static("Log your study session below.", id="log-title")
 
                    yield Select(
                        options=[],
                        id="subject-select",
                        prompt="Choose a subject",
                    )
 
                    yield Input(placeholder="Minutes, e.g. 30", id="minutes-input")
 
                    with Horizontal(id="button-row"):
                        yield Button("Log Session", id="log-button")
                        yield Button("Clear", id="clear-button")
 
                    yield Static("", id="message")
 
                with TabPane("Manage Session", id="manage-tab"):
                    yield Static("Select a study session to delete.", id="manage-title")
 
                    yield Select(
                        options=[],
                        id="session-select",
                        prompt="Choose a session",
                    )
 
                    with Horizontal(id="manage-button-row"):
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

                with TabPane("Focus Mode", id="focus-tab"):
                    yield Static("Start a focused study session.", id="focus-title")
 
                    yield Select(
                        options=[],
                        id="focus-subject-select",
                        prompt="Choose a subject",
                    )
 
                    yield TextArea(
                        "",
                        id="focus-website-input",
                    )
 
                    yield Input(
                        placeholder="Focus duration in minutes, e.g. 25",
                        id="focus-minutes-input",
                    )
 
                    with Horizontal(id="focus-button-row"):
                        yield Button("Open Website", id="open-website-button")
                        yield Button("Start Focus", id="start-focus-button")
                        yield Button("Cancel Focus", id="cancel-focus-button")
 
                    yield Static("", id="focus-timer")
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
                            yield Button("Appearance", id="settings-appearance-button")
                            yield Button("Sounds", id="settings-sounds-button")
                            yield Button("Subjects", id="settings-subjects-button")
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

                            with Vertical(id="appearance-panel"):
                                yield Static("Appearance", id="appearance-panel-title")
                                yield Checkbox("Light mode", id="light-mode-checkbox")
                                yield Static("", id="appearance-message")

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
 
                                    yield TextArea(
                                        "",
                                        id="new-subject-website-input",
                                    )
 
                                    with Horizontal(id="subject-button-row"):
                                        yield Button("Add Subject", id="add-subject-button")
 
                                    yield Static("", id="subject-message")
 
                                with Vertical(id="subject-edit-panel"):
 
                                    yield Static("Edit subject website.", id="edit-website-title")
 
                                    yield Select(
                                        options=[],
                                        id="edit-website-subject-select",
                                        prompt="Choose a subject",
                                    )
 
                                    yield TextArea(
                                        "",
                                        id="edit-website-input",
                                    )
 
                                    with Horizontal(id="edit-website-button-row"):
                                        yield Button("Update Website", id="update-website-button")
 
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

        login_container.display = True
        main_container.display = False

        subjects_panel = self.query_one("#subjects-panel")
        setup_health_panel = self.query_one("#setup-health-panel")
        sync_panel = self.query_one("#sync-panel")
        appearance_panel = self.query_one("#appearance-panel")

        subjects_panel.display = False
        setup_health_panel.display = False
        sync_panel.display = False
        appearance_panel.display = False

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

        self.apply_theme()
        self.hide_all_temp_messages()
        self.try_remembered_login()
 
    def update_dashboard(self):
        data = load_data()
 
        streak_count = calculate_current_streak(data)
        streak_protected_today = "Yes" if has_studied_today(data) else "No"
        today_minutes = calculate_today_minutes(data)
        today_sessions = calculate_today_sessions(data)
        weekly_minutes = calculate_weekly_minutes(data)
        weekly_goal = data["weekly_goal"]
        weekly_progress_bar = create_progress_bar(weekly_minutes, weekly_goal)
        weekly_goal_status = get_weekly_goal_status(weekly_minutes, weekly_goal)


        dashboard = self.query_one("#dashboard", Static)
        setup_checklist = self.query_one("#setup-checklist", Static)
        recent_sessions = self.query_one("#recent-sessions", Static)
        subject_stats = self.query_one("#subject-stats", Static)
        session_select = self.query_one("#session-select", Select)
        subject_select = self.query_one("#subject-select", Select)
        focus_subject_select = self.query_one("#focus-subject-select", Select)
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
 
        setup_checklist.update(
            get_setup_checklist(
                data,
                self.logged_in,
                self.server_is_online,
                get_server_token(),
            )
        )

        dashboard.update(
            f"[bold]Current streak:[/bold] {streak_count} days\n"
            f"[bold]Streak protected today:[/bold] {streak_protected_today}\n"
            f"[bold]Studied today:[/bold] {today_minutes} minutes\n"
            f"[bold]Sessions today:[/bold] {today_sessions}\n"
            f"[bold]Weekly goal:[/bold] {weekly_minutes} / {weekly_goal} minutes\n"
            f"[bold]Progress:[/bold] {weekly_progress_bar}\n"
            f"[bold]Weekly goal status:[/bold] {weekly_goal_status}"
        )
 
        recent_sessions.update(get_recent_sessions(data))
        subject_stats.update(get_subject_stats(data))
        focus_quality_summary.update(get_focus_quality_summary(data))
 
        session_select.set_options(get_session_options(data))
        session_select.clear()
 
        subject_select.set_options(get_subject_options(data))
        subject_select.clear()
 
        focus_subject_select.set_options(get_subject_options(data))
        focus_subject_select.clear()
 
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
            "#appearance-panel",
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

        if active_panel_id == "#appearance-panel":
            self.update_appearance_settings_panel()

        if active_panel_id == "#sounds-panel":
            self.update_sound_settings_panel()

        if active_panel_id == "#subjects-panel":
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
            "#appearance-message",
            "#subject-message",
            "#edit-website-message",
            "#delete-subject-message",
            "#focus-message",
            "#focus-quality-message",
            "#focus-timer",
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

    def play_ui_sound(self):
        self.play_app_sound("ui")

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

        self.play_app_sound("achievement")
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
        global_message = self.query_one("#global-message", Static)
 
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
 
    def show_streak_effect(self, streak_count):
        if streak_count > 0:
            self.play_streak_protected()
            self.push_screen(StreakEffectScreen(streak_count))
        else:
            global_message = self.query_one("#global-message", Static)
            self.show_temp_message("#global-message", "[green]Your study session has been logged.[/green]")
 
    def delete_subject_and_sessions(self, subject):
        data = load_data()
 
        if subject not in data["subjects"]:
            delete_subject_message = self.query_one("#delete-subject-message", Static)
            self.show_temp_message("#delete-subject-message", "[red]That subject could not be found.[/red]")
            self.update_dashboard()
            return
 
        original_session_count = len(data["sessions"])
        original_timetable_count = len(data.get("timetable", []))

        data["subjects"].remove(subject)
 
        if subject in data["subject_websites"]:
            del data["subject_websites"][subject]
 
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
 
        delete_subject_message = self.query_one("#delete-subject-message", Static)
 
        self.show_temp_message(
            "#delete-subject-message",
            f"[yellow]Deleted subject: {subject}. "
            f"Removed {deleted_session_count} linked session(s) "
            f"and {deleted_timetable_count} timetable item(s).[/yellow]",
        )
 
    def start_focus_session(self, subject, minutes):
        focus_timer = self.query_one("#focus-timer", Static)
        focus_message = self.query_one("#focus-message", Static)
 
        self.focus_subject = subject
        self.focus_minutes = minutes
        self.focus_seconds_left = minutes * 60
 
        if self.focus_timer is not None:
            self.focus_timer.stop()
 
        self.show_temp_message(
            "#focus-message",
            "[yellow]Focus session started. Stay focused until the timer ends.[/yellow]",
        )
 
        self.update_focus_display()
 
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
 
    def tick_focus_timer(self):
        self.focus_seconds_left -= 1
 
        if self.focus_seconds_left <= 0:
            self.focus_seconds_left = 0
            self.update_focus_display()
            self.complete_focus_session()
            return
 
        self.update_focus_display()
 
    def complete_focus_session(self):
        focus_timer = self.query_one("#focus-timer", Static)
        focus_message = self.query_one("#focus-message", Static)
 
        if self.focus_timer is not None:
            self.focus_timer.stop()
            self.focus_timer = None
 
        data = load_data()
        already_studied_today = has_studied_today(data)
 
        session = {
            "subject": str(self.focus_subject).lower(),
            "minutes": self.focus_minutes,
            "date": str(date.today()),
            "source": "focus",
        }
 
        data["sessions"].append(session)
        protect_streak_today(data)
        save_data(data)
        
        server_token = get_server_token()

        if server_token is not None:
            self.run_worker(
                partial(
                    self.upload_focus_session_in_background,
                    server_token,
                    str(self.focus_subject).lower(),
                    self.focus_minutes,
                ),
                thread=True,
                group="focus-upload",
            )

        self.update_dashboard()
        achievement_unlocked = self.unlock_earned_achievements()
 
        updated_data = load_data()
        streak_count = calculate_current_streak(updated_data)
 
        completed_subject = self.focus_subject
        completed_minutes = self.focus_minutes
 
        self.focus_seconds_left = 0
        self.focus_subject = None
        self.focus_minutes = 0
 
        self.show_temp_message("#focus-timer", "[bold green]Focus finished.[/bold green]")
        self.show_temp_message(
            "#focus-message",
            f"[green]Completed focus session. Logged {completed_minutes} minutes of {completed_subject} study.[/green]",
        )

        
        if not already_studied_today and not achievement_unlocked:
            self.show_streak_effect(streak_count)
        elif not achievement_unlocked:
            self.play_focus_complete_sound()
        self.show_focus_notification(completed_subject, completed_minutes)

    def upload_focus_session_in_background(self, token, subject, minutes):
        #avoid freezing the UI when the server is slow or offline
        try:
            upload_focus_session(
                token=token,
                subject=subject,
                minutes=minutes,
                website=None,
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
        self.focus_minutes = 0
 
        focus_timer.update("")
        focus_timer.display = False
        self.show_temp_message("#focus-message", "[yellow]Focus session cancelled. No study time was logged.[/yellow]")

    def on_select_changed(self, event: Select.Changed) -> None:
        data = load_data()

        if event.select.has_focus:
            self.play_ui_sound()

        if event.select.id == "focus-subject-select":
            selected_subject = event.value
            website_input = self.query_one("#focus-website-input", TextArea)
 
            if is_blank_select_value(selected_subject):
                website_input.load_text("")
                return
 
            saved_websites = get_subject_website_list(data, selected_subject)
            website_input.load_text(format_website_list_text(saved_websites))
            return
 
        if event.select.id == "edit-website-subject-select":
            selected_subject = event.value
            edit_website_input = self.query_one("#edit-website-input", TextArea)
 
            if is_blank_select_value(selected_subject):
                edit_website_input.load_text("")
                return
 
            saved_websites = get_subject_website_list(data, selected_subject)
            edit_website_input.load_text(format_website_list_text(saved_websites))
    
    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if self.logged_in:
            self.play_ui_sound()


    def try_remembered_login(self):
        #try auto login from remembered account
        username_input = self.query_one("#login-username-input", Input)
        login_message = self.query_one("#login-message", Static)

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
        self.focus_minutes = 0
        self.last_notified_sync_error = None

        focus_timer = self.query_one("#focus-timer", Static)
        focus_timer.update("")
        focus_timer.display = False



    def show_main_app(self):
        #show main app after login
        login_container = self.query_one("#login-container")
        main_container = self.query_one("#main-container")
        account_label = self.query_one("#account-label", Static)

        username = get_session_username()

        account_label.update(f"[cyan]Logged in as:[/cyan] {username}")

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

        if event.button.id == "logout-button":
            #logout from Textual UI
            login_container = self.query_one("#login-container")
            main_container = self.query_one("#main-container")
            username_input = self.query_one("#login-username-input", Input)
            password_input = self.query_one("#login-password-input", Input)
            login_message = self.query_one("#login-message", Static)


            self.stop_session_timers()
            logout_account()
            clear_session()
            clear_remembered_login()

            self.logged_in = False

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
            login_message = self.query_one("#login-message", Static)

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
                self.sync_focus_quality_from_server(server_token)

            except ValueError as signup_error:
                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)
                    save_data(private_data)
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
            self.show_main_app()
            return

        settings_panel_by_button = {
            "settings-weekly-button": "#weekly-goal-panel",
            "settings-health-button": "#setup-health-panel",
            "settings-sync-button": "#sync-panel",
            "settings-appearance-button": "#appearance-panel",
            "settings-sounds-button": "#sounds-panel",
            "settings-subjects-button": "#subjects-panel",
            "settings-focus-import-button": "#focus-import-panel",
        }

        if event.button.id in settings_panel_by_button:
            self.show_settings_panel(settings_panel_by_button[event.button.id])
            return

        if event.button.id == "settings-weekly-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            appearance_panel = self.query_one("#appearance-panel")
            focus_import_panel = self.query_one("#focus-import-panel")

            appearance_panel.display = False
            sounds_panel.display = False
            weekly_goal_panel.display = True
            subjects_panel.display = False
            sync_panel.display = False
            focus_import_panel.display = False
            return

        if event.button.id == "settings-sync-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            appearance_panel = self.query_one("#appearance-panel")
            focus_import_panel = self.query_one("#focus-import-panel")

            appearance_panel.display = False
            sounds_panel.display = False
            weekly_goal_panel.display = False
            subjects_panel.display = False
            sync_panel.display = True
            focus_import_panel.display = False
            self.update_sync_status()
            return 

        if event.button.id == "settings-appearance-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            subjects_panel = self.query_one("#subjects-panel")
            appearance_panel = self.query_one("#appearance-panel")
            focus_import_panel = self.query_one("#focus-import-panel")

            weekly_goal_panel.display = False
            sync_panel.display = False
            sounds_panel.display = False
            subjects_panel.display = False
            appearance_panel.display = True
            focus_import_panel.display = False

            self.update_appearance_settings_panel()
            return
        
        if event.button.id == "settings-sounds-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            subjects_panel = self.query_one("#subjects-panel")
            appearance_panel = self.query_one("#appearance-panel")
            focus_import_panel = self.query_one("#focus-import-panel")

            weekly_goal_panel.display = False
            sync_panel.display = False
            sounds_panel.display = True
            subjects_panel.display = False
            appearance_panel.display = False
            focus_import_panel.display = False

            self.update_sound_settings_panel()
            return


        if event.button.id == "settings-subjects-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            appearance_panel = self.query_one("#appearance-panel")
            focus_import_panel = self.query_one("#focus-import-panel")


            subject_add_panel = self.query_one("#subject-add-panel")
            subject_edit_panel = self.query_one("#subject-edit-panel")
            subject_delete_panel = self.query_one("#subject-delete-panel")
 
            weekly_goal_panel.display = False
            subjects_panel.display = True
            sync_panel.display = False
            sounds_panel.display = False
            appearance_panel.display = False
            focus_import_panel.display = False

            subject_add_panel.display = True
            subject_edit_panel.display = False
            subject_delete_panel.display = False
            return

        if event.button.id == "sync-now-button":
            data = load_data()
            save_data(data)
            try:
                sync_result = self.sync_focus_quality_from_server()
            except ValueError as error:
                self.update_sync_status()
                self.show_temp_message("#sync-message", f"[red]{error}[/red]")
                return

            added_count = sync_result["updates"]
            streak_protected = sync_result["streak_protected"]
            self.update_sync_status()
            if added_count > 0:
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

                self.show_temp_message(
                    "#sync-message",
                    f"[green]Sync started. Added {added_count} Chrome focus updates.[/green]",
                )
            else:
                self.show_temp_message(
                    "#sync-message",
                    "[yellow]Sync started. No new Chrome focus updates.[/yellow]",
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
 
        if event.button.id == "clear-button":
            subject_select = self.query_one("#subject-select", Select)
            minutes_input = self.query_one("#minutes-input", Input)
            message = self.query_one("#message", Static)
 
            subject_select.clear()
            minutes_input.value = ""
            message.update("")
            message.display = False
            return
 
        if event.button.id == "delete-selected-button":
            session_select = self.query_one("#session-select", Select)
            manage_message = self.query_one("#manage-message", Static)
 
            selected_index = session_select.value
            data = load_data()
 
            if len(data["sessions"]) == 0:
                self.show_temp_message("#manage-message", "[yellow]There are no sessions to delete.[/yellow]")
                self.update_dashboard()
                return
 
            if selected_index is None or selected_index is False:
                self.show_temp_message("#manage-message", "[yellow]Please select a session to delete.[/yellow]")
                return
 
            selected_index = int(selected_index)
 
            if selected_index < 0 or selected_index >= len(data["sessions"]):
                self.show_temp_message("#manage-message", "[red]Selected session could not be found.[/red]")
                self.update_dashboard()
                return
 
            deleted_session = data["sessions"].pop(selected_index)
            save_data(data)
 
            subject = deleted_session["subject"]
            minutes = deleted_session["minutes"]
            session_date = deleted_session["date"]
 
            self.update_dashboard()
 
            self.show_temp_message(
                "#manage-message",
                f"[yellow]Deleted: {session_date} - {subject} - {minutes} minutes.[/yellow]",
            )
            return
 
        if event.button.id == "save-goal-button":
            goal_input = self.query_one("#weekly-goal-input", Input)
            settings_message = self.query_one("#settings-message", Static)
 
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
            subject_message = self.query_one("#subject-message", Static)
 
            new_subject = new_subject_input.value.strip().lower()
            websites = clean_website_list(new_subject_website_input.text)
 
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
 
            save_data(data)
 
            self.update_dashboard()
            self.unlock_earned_achievements()
 
            if len(websites) == 0:
                self.show_temp_message("#subject-message", f"[green]Added subject: {new_subject}[/green]")
            else:
                self.show_temp_message(
                    "#subject-message",
                    f"[green]Added subject: {new_subject} with {len(websites)} website(s).[/green]",
                )
 
            new_subject_input.value = ""
            new_subject_website_input.load_text("")
            return
 
        if event.button.id == "update-website-button":
            edit_website_subject_select = self.query_one("#edit-website-subject-select", Select)
            edit_website_input = self.query_one("#edit-website-input", TextArea)
            edit_website_message = self.query_one("#edit-website-message", Static)
 
            selected_subject = edit_website_subject_select.value
            websites = clean_website_list(edit_website_input.text)
 
            if is_blank_select_value(selected_subject):
                self.show_temp_message("#edit-website-message", "[yellow]Please choose a subject first.[/yellow]")
                return
 
            data = load_data()
 
            if str(selected_subject) not in data["subjects"]:
                self.show_temp_message("#edit-website-message", "[red]That subject could not be found.[/red]")
                self.update_dashboard()
                return
 
            data["subject_websites"][str(selected_subject)] = websites
            save_data(data)
 
            self.update_dashboard()
 
            if len(websites) == 0:
                self.show_temp_message(
                    "#edit-website-message",
                    f"[yellow]Cleared websites for {selected_subject}.[/yellow]",
                )
            else:
                self.show_temp_message(
                    "#edit-website-message",
                    f"[green]Updated {selected_subject} with {len(websites)} website(s).[/green]",
                )
 
            return
 
        if event.button.id == "delete-subject-button":
            delete_subject_select = self.query_one("#delete-subject-select", Select)
            delete_subject_message = self.query_one("#delete-subject-message", Static)
 
            selected_subject = delete_subject_select.value
 
            if is_blank_select_value(selected_subject):
                self.show_temp_message("#delete-subject-message", "[yellow]Please choose a subject to delete.[/yellow]")
                return
 
            self.push_screen(DeleteSubjectConfirmScreen(str(selected_subject)))
            return
 
        if event.button.id == "open-website-button":
            focus_subject_select = self.query_one("#focus-subject-select", Select)
            website_input = self.query_one("#focus-website-input", TextArea)

            subject = focus_subject_select.value
            websites = clean_website_list(website_input.text)
            data = load_data()

            if is_blank_select_value(subject):
                self.show_temp_message("#focus-message", "[red]Please choose a subject first.[/red]")
                return

            if len(websites) == 0:
                websites = get_subject_website_list(data, subject)

            if len(websites) == 0:
                self.show_temp_message(
                    "#focus-message",
                    "[red]No websites saved for this subject. Please enter one manually.[/red]",
                )
                return

            for website in websites:
                webbrowser.open(website)

            self.show_temp_message(
                "#focus-message",
                f"[green]Opened {len(websites)} website(s) for {subject}.[/green]",
            )
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

            if is_blank_select_value(selected_index):
                self.show_temp_message(
                    "#timetable-message",
                    "[yellow]Please choose a planned session to edit.[/yellow]",
                )
                return

            self.editing_timetable_index = int(selected_index)
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

            if is_blank_select_value(selected_index):
                self.show_temp_message(
                    "#timetable-message",
                    "[yellow]Please choose a planned session to delete.[/yellow]",
                )
                return

            data = load_data()
            selected_index = int(selected_index)

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
            focus_minutes_input = self.query_one("#focus-minutes-input", Input)
            focus_message = self.query_one("#focus-message", Static)
 
            subject = focus_subject_select.value
            minutes_text = focus_minutes_input.value.strip()
 
            if is_blank_select_value(subject):
                self.show_temp_message("#focus-message", "[red]Please choose a subject.[/red]")
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
 
            self.start_focus_session(str(subject), minutes)
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
            minutes_input = self.query_one("#minutes-input", Input)
            message = self.query_one("#message", Static)
 
            subject = subject_select.value
            minutes_text = minutes_input.value.strip()
 

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
            }
 
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
            minutes_input.value = ""
            return
