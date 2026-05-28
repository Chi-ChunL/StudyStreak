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
    Button,
    TabbedContent,
    TabPane,
    Select,
    Checkbox,
)
 
from studystreak.storage import load_data, save_data
from studystreak.accounts import create_account, list_accounts, login_account, logout_account
from studystreak.accounts import normalise_username, validate_password, validate_username
from studystreak.session import set_session, clear_session, get_session_username, set_server_token, get_server_token
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
)
from studystreak.profile_sync import decrypt_profile_data
from studystreak.notification import play_sound, show_focus_complete_notification, show_sync_failed_notification



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
 
def calculate_current_streak(data):
    study_dates = set()
 
    for session in data["sessions"]:
        study_dates.add(session["date"])
 
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
 
    for session in data["sessions"]:
        if session["date"] == today_date:
            return True
 
    return False
 
 
def get_recent_sessions(data, limit=5):
    sessions = data["sessions"]
 
    if len(sessions) == 0:
        return "No study sessions logged yet."
 
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


def get_timetable_grid(data):
    #show timetable as weekly grid
    timetable = data.get("timetable", [])

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    start_hour = 8
    end_hour = 22

    cell_width = 12
    time_width = 7

    timetable_slots = {}

    for item in timetable:
        day = normalise_timetable_day(item["day"])
        start_time = item["start_time"]
        subject = item["subject"]

        hour = int(start_time[:2])
        key = (day, hour)

        if key not in timetable_slots:
            timetable_slots[key] = []

        timetable_slots[key].append(subject)

    lines = ["[bold]Weekly Timetable[/bold]", ""]

    header = "Time".ljust(time_width)

    for day in days:
        header += day.center(cell_width)

    lines.append(header)
    lines.append("-" * (time_width + cell_width * len(days)))

    for hour in range(start_hour, end_hour + 1):
        row = f"{hour:02}:00".ljust(time_width)

        for day in days:
            sessions = timetable_slots.get((day, hour), [])

            if len(sessions) == 0:
                cell_text = ""
            else:
                cell_text = ", ".join(sessions)
                cell_text = cell_text[:cell_width - 1]

            row += cell_text.center(cell_width)

        lines.append(row)

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
        return f"No timetable sessions planned for {today_name}."

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
 
    if len(sessions) == 0:
        return "No study sessions logged yet."
 
    subject_total = {}
 
    for session in sessions:
        subject = session["subject"]
        minutes = session["minutes"]
 
        if subject not in subject_total:
            subject_total[subject] = 0
 
        subject_total[subject] += minutes
 
    lines = ["[bold]Subject Stats[/bold]"]
 
    for subject, total_minutes in sorted(subject_total.items()):
        hours = total_minutes // 60
        remaining_minutes = total_minutes % 60
 
        if hours > 0:
            time_text = f"{hours}h {remaining_minutes}m"
        else:
            time_text = f"{remaining_minutes}m"
 
        lines.append(f"{subject} - {time_text}")
 
    return "\n".join(lines)
 
def is_blank_select_value(value):
    return (
        value is None
        or value is False
        or str(value).lower() in ["", "none", "null", "select.null", "select.blank"]
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
    focus_seconds_left = 0
    focus_subject = None
    focus_minutes = 0
    logged_in = False
    temp_message_versions = {}
    leaderboard_period = "all"
    last_notified_sync_error = None
 
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="login-container"):
            yield Static("StudyStreak Login", id="login-title")
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
            yield Static("StudyStreak CLI", id="title")
            yield Static("Track your study streak and log your progress.", id="subtitle")

            with Horizontal(id="account-row"):
                yield Static("", id="account-label")
                yield Button("Logout", id="logout-button")
            

            with TabbedContent(initial="dashboard-tab"):
                with TabPane("Dashboard", id="dashboard-tab"):
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

                with TabPane("Focus Mode", id="focus-tab"):
                    yield Static("Start a focused study session.", id="focus-title")
 
                    yield Select(
                        options=[],
                        id="focus-subject-select",
                        prompt="Choose a subject",
                    )
 
                    yield Input(
                        placeholder="Study website, e.g. https://senecalearning.com",
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

                with TabPane("Settings", id="settings-tab"):
                    yield Static("Settings", id="settings-title")
 
                    with Horizontal(id="settings-layout"):
                        with Vertical(id="settings-sidebar"):
                            yield Button("Weekly Goal", id="settings-weekly-button")
                            yield Button("Sync", id="settings-sync-button")
                            yield Button("Sounds", id="settings-sounds-button")
                            yield Button("Subjects", id="settings-subjects-button")
 
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

                            with Vertical(id="sync-panel"):
                                yield Static("Cloud sync", id="sync-panel-title")
                                yield Static("", id="sync-details")

                                with Horizontal(id="sync-button-row"):
                                    yield Button("Sync Now", id="sync-now-button")

                                yield Static("", id="sync-message")

                            with Vertical(id="sounds-panel"):
                                yield Static("Sound settings", id="sound-panel-title")

                                yield Checkbox("UI sounds", id="ui-sounds-checkbox")
                                yield Checkbox("Focus complete sound", id="focus-sound-checkbox")
                                yield Checkbox("Streak protected sound", id="streak-sound-checkbox")
                                yield Checkbox("Focus complete notification", id="focus-notification-checkbox")
                                yield Checkbox("Sync failed notification", id="sync-failed-notification-checkbox")

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
 
                                    yield Input(
                                        placeholder="Study website for this subject, e.g. https://senecalearning.com",
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
 
                                    yield Input(
                                        placeholder="New website, e.g. https://senecalearning.com",
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
        sync_panel = self.query_one("#sync-panel")

        subjects_panel.display = False
        sync_panel.display = False

        subject_edit_panel = self.query_one("#subject-edit-panel")
        subject_delete_panel = self.query_one("#subject-delete-panel")

        subject_edit_panel.display = False
        subject_delete_panel.display = False

        sound_panel = self.query_one("#sounds-panel")
        sound_panel.display = False

        timetable_form_panel = self.query_one("#timetable-form-panel")
        timetable_form_panel.display = False

        self.hide_all_temp_messages()
        self.try_remembered_login()
 
    def update_dashboard(self):
        data = load_data()
 
        streak_count = calculate_current_streak(data)
        today_minutes = calculate_today_minutes(data)
        today_sessions = calculate_today_sessions(data)
        weekly_minutes = calculate_weekly_minutes(data)
        weekly_goal = data["weekly_goal"]
        weekly_progress_bar = create_progress_bar(weekly_minutes, weekly_goal)
        weekly_goal_status = get_weekly_goal_status(weekly_minutes, weekly_goal)


        dashboard = self.query_one("#dashboard", Static)
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

        weekly_goal_input.placeholder = f"Current goal: {weekly_goal} minutes"
 
        dashboard.update(
            f"[bold]Current streak:[/bold] {streak_count} days\n"
            f"[bold]Studied today:[/bold] {today_minutes} minutes\n"
            f"[bold]Sessions today:[/bold] {today_sessions}\n"
            f"[bold]Weekly goal:[/bold] {weekly_minutes} / {weekly_goal} minutes\n"
            f"[bold]Progress:[/bold] {weekly_progress_bar}\n"
            f"[bold]Weekly goal status:[/bold] {weekly_goal_status}"
        )
 
        recent_sessions.update(get_recent_sessions(data))
        subject_stats.update(get_subject_stats(data))
 
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

        today_timetable.update(get_today_timetable_display(data))
        timetable_grid.update(get_timetable_grid(data))

        self.update_sync_status()

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
            
            if self.last_notified_sync_error != last_sync_error:
                self.last_notified_sync_error = last_sync_error
                self.notify_sync_failed(last_sync_error)
            
            return

        if last_cloud_sync is None:
            sync_status_label.update("[yellow]Sync: Not synced yet[/yellow]")
            sync_details.update("[yellow]This device has not uploaded cloud data yet.[/yellow]")
            return
        
        if last_local_update is None:
            sync_status_label.update("[green]Sync: Synced[/green]")
            sync_details.update("[green]Cloud sync is up to date.[/green]")
            return
        
        if last_cloud_sync >= last_local_update:
            sync_status_label.update("[green]Sync: Synced[/green]")
            sync_details.update("[green]Cloud sync is up to date.[/green]")
            self.last_notified_sync_error = None
        else:
            sync_status_label.update("[yellow]Sync: Pending upload[/yellow]")
            sync_details.update("[yellow]A recent local change is waiting to upload.[/yellow]")
    
    def update_sound_settings_panel(self):
        data = load_data()
        sound_settings = data.get("sound_settings", {})
        notification_settings = data.get("notification-settings", {})

        self.query_one("#ui-sounds-checkbox", Checkbox).value = sound_settings.get("ui", True)
        self.query_one("#focus-sound-checkbox", Checkbox).value = sound_settings.get("focus_complete", True)
        self.query_one("#streak-sound-checkbox", Checkbox).value = sound_settings.get("streak_protected", True)
        self.query_one("#focus-notification-checkbox", Checkbox).value = (
            notification_settings.get("focus_complete", True)
        )
        self.query_one("#sync-failed-notification-checkbox", Checkbox).value = (
            notification_settings.get("sync_failed", True)
        )

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox_sound_map = {
            "ui-sounds-checkbox": "ui",
            "focus-sound-checkbox": "focus_complete",
            "streak-sound-checkbox": "streak_protected",
        }

        notification_checkbox_map = {
            "focus-notification-checkbox": "focus_complete",
            "sync-failed-notification-checkbox": "sync_failed",
        }

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
            "#subject-message",
            "#edit-website-message",
            "#delete-subject-message",
            "#focus-message",
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
 
        data["subjects"].remove(subject)
 
        if subject in data["subject_websites"]:
            del data["subject_websites"][subject]
 
        data["sessions"] = [
            session for session in data["sessions"]
            if session["subject"] != subject
        ]
 
        deleted_session_count = original_session_count - len(data["sessions"])
 
        save_data(data)
        self.update_dashboard()
 
        delete_subject_message = self.query_one("#delete-subject-message", Static)
 
        self.show_temp_message(
            "#delete-subject-message",
            f"[yellow]Deleted subject: {subject}. "
            f"Removed {deleted_session_count} linked session(s).[/yellow]",
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
        }
 
        data["sessions"].append(session)
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

        
        if not already_studied_today:
            self.show_streak_effect(streak_count)
        else:
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
            website_input = self.query_one("#focus-website-input", Input)
 
            if is_blank_select_value(selected_subject):
                website_input.value = ""
                return
 
            saved_website = data["subject_websites"].get(str(selected_subject), "")
            website_input.value = saved_website
            return
 
        if event.select.id == "edit-website-subject-select":
            selected_subject = event.value
            edit_website_input = self.query_one("#edit-website-input", Input)
 
            if is_blank_select_value(selected_subject):
                edit_website_input.value = ""
                return
 
            saved_website = data["subject_websites"].get(str(selected_subject), "")
            edit_website_input.value = saved_website
    
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

            if cloud_data is not None:
                set_session(remembered_username, remembered_password, cloud_data)
                save_data(cloud_data)

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

        if server_is_online:
            server_status_label.update("[green]Server: Connected[/green]")
        else:
            server_status_label.update("[red]Server: Offline[/red]")

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
        self.update_server_status()
        self.update_sync_status()
        self.set_interval(2, self.update_sync_status)
        self.update_dashboard()
        self.refresh_leaderboard()

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
            lines.append(
                f"{index}. {row['display_name']} - {row['total_minutes']} minutes"
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

                    if cloud_data is not None:
                        set_session(username, password, cloud_data)
                        save_data(cloud_data)

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

                if cloud_data is not None:
                    private_data = cloud_data

                set_session(username, password, private_data)
                save_data(private_data)
                set_server_token(server_token)

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

                signup_to_server(username, password)
                create_account(username=username, password=password)

                private_data = login_account(username, password)
                set_session(username, password, private_data)

                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)
                    save_data(private_data)
                except ValueError as error:
                    self.show_temp_message(
                        "#login-message",
                        f"[yellow]Account created locally, but server login failed.[/yellow]",
                    )

                remember_checkbox = self.query_one("#remember-me-checkbox", Checkbox)

                if remember_checkbox.value:
                    save_remembered_login(username, password)
                else:
                    clear_remembered_login()
            except ValueError as error:
                self.show_temp_message("#login-message", f"[red]Username or Password Incorrect.[/red]")
                return

            password_input.value = ""
            self.show_temp_message("#login-message", "[green]Account created and logged in.[/green]")
            self.show_main_app()
            return

        if event.button.id == "settings-weekly-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")

            sounds_panel.display = False
            weekly_goal_panel.display = True
            subjects_panel.display = False
            sync_panel.display = False
            return

        if event.button.id == "settings-sync-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")

            sounds_panel.display = False
            weekly_goal_panel.display = False
            subjects_panel.display = False
            sync_panel.display = True
            self.update_sync_status()
            return 
        
        if event.button.id == "settings-sounds-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")
            subjects_panel = self.query_one("#subjects-panel")

            weekly_goal_panel.display = False
            sync_panel.display = False
            sounds_panel.display = True
            subjects_panel.display = False

            self.update_sound_settings_panel()
            return


        if event.button.id == "settings-subjects-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
            sync_panel = self.query_one("#sync-panel")
            sounds_panel = self.query_one("#sounds-panel")


            subject_add_panel = self.query_one("#subject-add-panel")
            subject_edit_panel = self.query_one("#subject-edit-panel")
            subject_delete_panel = self.query_one("#subject-delete-panel")
 
            weekly_goal_panel.display = False
            subjects_panel.display = True
            sync_panel.display = False
            sounds_panel.display = False

            subject_add_panel.display = True
            subject_edit_panel.display = False
            subject_delete_panel.display = False
            return

        if event.button.id == "sync-now-button":
            data = load_data()
            save_data(data)
            self.update_sync_status()
            self.show_temp_message("#sync-message", "[yellow]Sync started.[/yellow]")
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
            new_subject_website_input = self.query_one("#new-subject-website-input", Input)
            subject_message = self.query_one("#subject-message", Static)
 
            new_subject = new_subject_input.value.strip().lower()
            website = new_subject_website_input.value.strip()
 
            if new_subject == "":
                self.show_temp_message("#subject-message", "[red]Please enter a subject name.[/red]")
                return
 
            website = format_website_url(website)
 
            data = load_data()
 
            if new_subject in data["subjects"]:
                self.show_temp_message("#subject-message", "[yellow]That subject already exists.[/yellow]")
                return
 
            data["subjects"].append(new_subject)
            data["subjects"].sort()
 
            data["subject_websites"][new_subject] = website
 
            save_data(data)
 
            self.update_dashboard()
 
            if website == "":
                self.show_temp_message("#subject-message", f"[green]Added subject: {new_subject}[/green]")
            else:
                self.show_temp_message(
                    "#subject-message",
                    f"[green]Added subject: {new_subject} with website: {website}[/green]",
                )
 
            new_subject_input.value = ""
            new_subject_website_input.value = ""
            return
 
        if event.button.id == "update-website-button":
            edit_website_subject_select = self.query_one("#edit-website-subject-select", Select)
            edit_website_input = self.query_one("#edit-website-input", Input)
            edit_website_message = self.query_one("#edit-website-message", Static)
 
            selected_subject = edit_website_subject_select.value
            website = edit_website_input.value.strip()
 
            if is_blank_select_value(selected_subject):
                self.show_temp_message("#edit-website-message", "[yellow]Please choose a subject first.[/yellow]")
                return
 
            data = load_data()
 
            if str(selected_subject) not in data["subjects"]:
                self.show_temp_message("#edit-website-message", "[red]That subject could not be found.[/red]")
                self.update_dashboard()
                return
 
            website = format_website_url(website)
 
            data["subject_websites"][str(selected_subject)] = website
            save_data(data)
 
            self.update_dashboard()
 
            if website == "":
                self.show_temp_message(
                    "#edit-website-message",
                    f"[yellow]Cleared website for {selected_subject}.[/yellow]",
                )
            else:
                self.show_temp_message(
                    "#edit-website-message",
                    f"[green]Updated website for {selected_subject}: {website}[/green]",
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
            website_input = self.query_one("#focus-website-input", Input)
            focus_message = self.query_one("#focus-message", Static)
 
            subject = focus_subject_select.value
            website = website_input.value.strip()
            data = load_data()
 
            if is_blank_select_value(subject):
                self.show_temp_message("#focus-message", "[red]Please choose a subject first.[/red]")
                return
 
            if website == "":
                website = data["subject_websites"].get(str(subject), "")
 
            if website == "":
                self.show_temp_message("#focus-message", "[red]No website saved for this subject. Please enter one manually.[/red]")
                return
 
            website = format_website_url(website)
 
            webbrowser.open(website)
 
            self.show_temp_message("#focus-message", f"[green]Opened study website: {website}[/green]")
            return
        
        if event.button.id == "show-timetable-form-button":
            #show timetable form
            timetable_form_panel = self.query_one("#timetable-form-panel")
            timetable_form_panel.display = True
            return
        
        if event.button.id == "hide-timetable-form-button":
            #hide timetable form
            timetable_form_panel = self.query_one("#timetable-form-panel")
            timetable_form_panel.display = False
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

            timetable_item = {
                "subject": str(subject).lower(),
                "day": str(day),
                "start_time": start_time,
                "minutes": minutes,
            }

            data["timetable"].append(timetable_item)
            save_data(data)

            self.update_dashboard()

            subject_select.clear()
            day_select.clear()
            start_input.value = ""
            minutes_input.value = ""

            self.show_temp_message(
                "#timetable-message",
                f"[green]Added {subject} on {day} at {start_time}.[/green]",
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
            }
 
            data["sessions"].append(session)
            save_data(data)
 
            self.update_dashboard()
 
            updated_data = load_data()
            streak_count = calculate_current_streak(updated_data)
 
            if not already_studied_today:
                self.show_streak_effect(streak_count)
 
            self.show_temp_message("#message", f"[green]Logged {minutes} minutes of {subject} study.[/green]")
 
            subject_select.clear()
            minutes_input.value = ""
            return
