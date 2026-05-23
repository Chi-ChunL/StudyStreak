import webbrowser
from datetime import date, timedelta, datetime
 
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
from studystreak.accounts import create_account, login_account, logout_account
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
)




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
                    yield Button("Refresh Leaderboard", id="refresh-leaderboard-button")
                    yield Static("", id="leaderboard")

                with TabPane("Settings", id="settings-tab"):
                    yield Static("Settings", id="settings-title")
 
                    with Horizontal(id="settings-layout"):
                        with Vertical(id="settings-sidebar"):
                            yield Button("Weekly Goal", id="settings-weekly-button")
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
        subjects_panel.display = False

        subject_edit_panel = self.query_one("#subject-edit-panel")
        subject_delete_panel = self.query_one("#subject-delete-panel")

        subject_edit_panel.display = False
        subject_delete_panel.display = False

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
 
    def action_escape_quit(self):
        current_time = datetime.now()
        global_message = self.query_one("#global-message", Static)
 
        if self.last_escape_time is None:
            self.last_escape_time = current_time
            global_message.update("[yellow]Press Esc again to quit.[/yellow]")
            return
 
        time_difference = current_time - self.last_escape_time
 
        if time_difference.total_seconds() <= 2:
            self.exit()
        else:
            self.last_escape_time = current_time
            global_message.update("[yellow]Press Esc again to quit.[/yellow]")
 
    def show_streak_effect(self, streak_count):
        if streak_count > 0:
            self.push_screen(StreakEffectScreen(streak_count))
        else:
            global_message = self.query_one("#global-message", Static)
            global_message.update("[green]Your study session has been logged.[/green]")
            self.set_timer(4, lambda: global_message.update(""))
 
    def delete_subject_and_sessions(self, subject):
        data = load_data()
 
        if subject not in data["subjects"]:
            delete_subject_message = self.query_one("#delete-subject-message", Static)
            delete_subject_message.update("[red]That subject could not be found.[/red]")
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
 
        delete_subject_message.update(
            f"[yellow]Deleted subject: {subject}. "
            f"Removed {deleted_session_count} linked session(s).[/yellow]"
        )
 
    def start_focus_session(self, subject, minutes):
        focus_timer = self.query_one("#focus-timer", Static)
        focus_message = self.query_one("#focus-message", Static)
 
        self.focus_subject = subject
        self.focus_minutes = minutes
        self.focus_seconds_left = minutes * 60
 
        if self.focus_timer is not None:
            self.focus_timer.stop()
 
        focus_message.update(
            "[yellow]Focus session started. Stay focused until the timer ends.[/yellow]"
        )
 
        self.update_focus_display()
 
        self.focus_timer = self.set_interval(1, self.tick_focus_timer)
 
    def update_focus_display(self):
        focus_timer = self.query_one("#focus-timer", Static)
 
        minutes_left = self.focus_seconds_left // 60
        seconds_left = self.focus_seconds_left % 60
 
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
            try:
                upload_focus_session(
                    token=server_token,
                    subject=str(self.focus_subject).lower(),
                    minutes=self.focus_minutes,
                    website=None,
                )
            except ValueError:
                focus_message.update("[yellow]Focus saved locally, but server upload failed.[/yellow]")


        self.update_dashboard()
 
        updated_data = load_data()
        streak_count = calculate_current_streak(updated_data)
 
        completed_subject = self.focus_subject
        completed_minutes = self.focus_minutes
 
        self.focus_seconds_left = 0
        self.focus_subject = None
        self.focus_minutes = 0
 
        focus_timer.update("[bold green]Focus finished.[/bold green]")
        focus_message.update(
            f"[green]Completed focus session. Logged {completed_minutes} minutes of {completed_subject} study.[/green]"
        )
 
        if not already_studied_today:
            self.show_streak_effect(streak_count)
 
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
        focus_message.update("[yellow]Focus session cancelled. No study time was logged.[/yellow]")
 
    def on_select_changed(self, event: Select.Changed) -> None:
        data = load_data()

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
            login_message.update("[yellow]Enter your password to continue[/yellow]")
            return

        try:
            private_data = login_account(remembered_username, remembered_password)
            set_session(remembered_username, remembered_password, private_data)
        except ValueError:
            clear_remembered_login()
            login_message.update("[red]Saved login expired. Please log in again.[/red]")
            return
        self.show_main_app()

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
        self.update_dashboard()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        
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

            login_message.update("[yellow]Logged out.[/yellow]")
            return
        if event.button.id == "login-button":
            username_input = self.query_one("#login-username-input", Input)
            password_input = self.query_one("#login-password-input", Input)
            login_message = self.query_one("#login-message", Static)

            username = username_input.value.strip()
            password = password_input.value

            if username == "":
                login_message.update("[red]Please enter your username.[/red]")
                return
            
            if password == "":
                login_message.update("[red]Please enter your password.[/red]")
                return
            
            try:
                private_data = login_account(username, password)
                set_session(username, password, private_data)

                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)
                
                except ValueError:
                    login_message.update("[yellow]Local login worked, but server login failed.[/yellow]")

                remember_checkbox = self.query_one("#remember-me-checkbox", Checkbox)

                if remember_checkbox.value:
                    save_remembered_login(username, password)
                else:
                    clear_remembered_login()

            except ValueError as error:
                login_message.update(f"[red]{error}[/red]")
                return
            
            password_input.value = ""
            login_message.update("[green]Login successful.[/green]")
            self.show_main_app()
            return

        if event.button.id == "create-account-button":
            username_input = self.query_one("#login-username-input", Input)
            password_input = self.query_one("#login-password-input", Input)
            login_message = self.query_one("#login-message", Static)

            username = username_input.value.strip()
            password = password_input.value

            if username == "":
                login_message.update("[red]Please enter a username.[/red]")
                return

            if password == "":
                login_message.update("[red]Please enter a password.[/red]")
                return

            try:
                create_account(username=username, password=password)
                
                try:
                    signup_to_server(username, password)
                except ValueError:
                    login_message.update("[yellow]Local account created, but server signup failed.[/yellow]")
                    return

                private_data = login_account(username, password)
                set_session(username, password, private_data)

                try:
                    server_token = login_to_server(username, password)
                    set_server_token(server_token)
                except ValueError:
                    login_message.update("[yellow]Local login worked, but server login failed.[/yellow]")

                remember_checkbox = self.query_one("#remember-me-checkbox", Checkbox)

                if remember_checkbox.value:
                    save_remembered_login(username, password)
                else:
                    clear_remembered_login()
            except ValueError as error:
                login_message.update(f"[red]{error}[/red]")
                return

            password_input.value = ""
            login_message.update("[green]Account created and logged in.[/green]")
            self.show_main_app()
            return

        if event.button.id == "settings-weekly-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
 
            weekly_goal_panel.display = True
            subjects_panel.display = False
            return
 
 
        if event.button.id == "settings-subjects-button":
            weekly_goal_panel = self.query_one("#weekly-goal-panel")
            subjects_panel = self.query_one("#subjects-panel")
 
            subject_add_panel = self.query_one("#subject-add-panel")
            subject_edit_panel = self.query_one("#subject-edit-panel")
            subject_delete_panel = self.query_one("#subject-delete-panel")
 
            weekly_goal_panel.display = False
            subjects_panel.display = True
 
            subject_add_panel.display = True
            subject_edit_panel.display = False
            subject_delete_panel.display = False
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
            return
 
        if event.button.id == "delete-selected-button":
            session_select = self.query_one("#session-select", Select)
            manage_message = self.query_one("#manage-message", Static)
 
            selected_index = session_select.value
            data = load_data()
 
            if len(data["sessions"]) == 0:
                manage_message.update("[yellow]There are no sessions to delete.[/yellow]")
                self.update_dashboard()
                return
 
            if selected_index is None or selected_index is False:
                manage_message.update("[yellow]Please select a session to delete.[/yellow]")
                return
 
            selected_index = int(selected_index)
 
            if selected_index < 0 or selected_index >= len(data["sessions"]):
                manage_message.update("[red]Selected session could not be found.[/red]")
                self.update_dashboard()
                return
 
            deleted_session = data["sessions"].pop(selected_index)
            save_data(data)
 
            subject = deleted_session["subject"]
            minutes = deleted_session["minutes"]
            session_date = deleted_session["date"]
 
            self.update_dashboard()
 
            manage_message.update(
                f"[yellow]Deleted: {session_date} - {subject} - {minutes} minutes.[/yellow]"
            )
            return
 
        if event.button.id == "save-goal-button":
            goal_input = self.query_one("#weekly-goal-input", Input)
            settings_message = self.query_one("#settings-message", Static)
 
            goal_text = goal_input.value.strip()
 
            if goal_text == "":
                settings_message.update("[red]Please enter a weekly goal.[/red]")
                return
 
            if not goal_text.isdigit():
                settings_message.update("[red]Weekly goal must be a whole number.[/red]")
                return
 
            weekly_goal = int(goal_text)
 
            if weekly_goal <= 0:
                settings_message.update("[red]Weekly goal must be more than 0.[/red]")
                return
 
            data = load_data()
            data["weekly_goal"] = weekly_goal
            save_data(data)
 
            self.update_dashboard()
 
            settings_message.update(
                f"[green]Weekly goal updated to {weekly_goal} minutes.[/green]"
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
                subject_message.update("[red]Please enter a subject name.[/red]")
                return
 
            website = format_website_url(website)
 
            data = load_data()
 
            if new_subject in data["subjects"]:
                subject_message.update("[yellow]That subject already exists.[/yellow]")
                return
 
            data["subjects"].append(new_subject)
            data["subjects"].sort()
 
            data["subject_websites"][new_subject] = website
 
            save_data(data)
 
            self.update_dashboard()
 
            if website == "":
                subject_message.update(f"[green]Added subject: {new_subject}[/green]")
            else:
                subject_message.update(
                    f"[green]Added subject: {new_subject} with website: {website}[/green]"
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
                edit_website_message.update("[yellow]Please choose a subject first.[/yellow]")
                return
 
            data = load_data()
 
            if str(selected_subject) not in data["subjects"]:
                edit_website_message.update("[red]That subject could not be found.[/red]")
                self.update_dashboard()
                return
 
            website = format_website_url(website)
 
            data["subject_websites"][str(selected_subject)] = website
            save_data(data)
 
            self.update_dashboard()
 
            if website == "":
                edit_website_message.update(
                    f"[yellow]Cleared website for {selected_subject}.[/yellow]"
                )
            else:
                edit_website_message.update(
                    f"[green]Updated website for {selected_subject}: {website}[/green]"
                )
 
            return
 
        if event.button.id == "delete-subject-button":
            delete_subject_select = self.query_one("#delete-subject-select", Select)
            delete_subject_message = self.query_one("#delete-subject-message", Static)
 
            selected_subject = delete_subject_select.value
 
            if is_blank_select_value(selected_subject):
                delete_subject_message.update("[yellow]Please choose a subject to delete.[/yellow]")
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
                focus_message.update("[red]Please choose a subject first.[/red]")
                return
 
            if website == "":
                website = data["subject_websites"].get(str(subject), "")
 
            if website == "":
                focus_message.update("[red]No website saved for this subject. Please enter one manually.[/red]")
                return
 
            website = format_website_url(website)
 
            webbrowser.open(website)
 
            focus_message.update(f"[green]Opened study website: {website}[/green]")
            return
 
        if event.button.id == "start-focus-button":
            focus_subject_select = self.query_one("#focus-subject-select", Select)
            focus_minutes_input = self.query_one("#focus-minutes-input", Input)
            focus_message = self.query_one("#focus-message", Static)
 
            subject = focus_subject_select.value
            minutes_text = focus_minutes_input.value.strip()
 
            if is_blank_select_value(subject):
                focus_message.update("[red]Please choose a subject.[/red]")
                return
 
            if minutes_text == "":
                focus_message.update("[red]Please enter a focus duration.[/red]")
                return
 
            if not minutes_text.isdigit():
                focus_message.update("[red]Focus duration must be a whole number.[/red]")
                return
 
            minutes = int(minutes_text)
 
            if minutes <= 0:
                focus_message.update("[red]Focus duration must be more than 0.[/red]")
                return
 
            self.start_focus_session(str(subject), minutes)
            return

        if event.button.id == "refresh-leaderboard-button":
            leaderboard = self.query_one("#leaderboard", Static)

            try:
                rows = get_leaderboard()
            except ValueError:
                leaderboard.update("[red]Could not load leaderboard.[/red]")
                return
            
            if len(rows) == 0:
                leaderboard.update("[yellow]No leaderboard data yet.[/yellow]")
                return
            
            lines = ["[bold]Leaderboard[/bold]"]

            for index, row in enumerate(rows, start=1):
                lines.append(
                    f"{index}. {row['display_name']} - {row['total_minutes']} minutes"
                )
            leaderboard.update("\n".join(lines))
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
                message.update("[red]Please choose a subject.[/red]")
                return
 
            if minutes_text == "":
                message.update("[red]Please enter the number of minutes.[/red]")
                return
 
            if not minutes_text.isdigit():
                message.update("[red]Minutes must be a whole number.[/red]")
                return
 
            minutes = int(minutes_text)
 
            if minutes <= 0:
                message.update("[red]Minutes must be more than 0.[/red]")
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
 
            message.update(f"[green]Logged {minutes} minutes of {subject} study.[/green]")
 
            subject_select.clear()
            minutes_input.value = ""
            return