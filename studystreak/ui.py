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


from datetime import date, timedelta, datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
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
)

from studystreak.storage import load_data, save_data


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
        return "No study session logged yet"

    subject_total = {}

    for session in sessions:
        subject = session["subject"]
        minutes = session["minutes"]

        if subject not in subject_total:
            subject_total[subject] = 0

        subject_total[subject] += minutes

    lines = ["[bold]Subject Stats[/bold]"]

    for subject, total_minutes in sorted(subject_total.items()):
        hours = total_minutes //60
        remaining_minutes = total_minutes % 60

        if hours > 0:
            time_text = f"{hours}h {remaining_minutes}m"
        else:
            time_text = f"{remaining_minutes}m"

        lines.append(f"{subject} - {time_text}")
    
    return "\n".join(lines)

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


class StudyStreakApp(App):

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("escape", "escape_quit", "Quit"),
    ]

    last_escape_time = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            yield Static("StudyStreak CLI", id="title")
            yield Static("Track your study streak and log your progress.", id="subtitle")

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

                with TabPane("Settings", id="settings-tab"):
                    yield Static("Set your weekly study goal.", id="settings-title")

                    yield Input(
                        placeholder="Weekly goal in minutes, e.g. 300",
                        id="weekly-goal-input",
                    )

                    with Horizontal(id="settings-button-row"):
                        yield Button("Save Goal", id="save-goal-button")

                    yield Static("", id="settings-message")

                    yield Static("Add a subject.", id="subject-settings-title")

                    yield Input(
                        placeholder="Subject name, e.g. maths",
                        id="new-subject-input",
                    )

                    with Horizontal(id="subject-button-row"):
                        yield Button("Add Subject", id="add-subject-button")

                    yield Static("", id="subject-message")

            yield Static("", id="global-message")

        yield Footer()

    def on_mount(self):
        self.update_dashboard()

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
        weekly_goal_input = self.query_one("#weekly-goal-input", Input)

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

    def on_button_pressed(self, event: Button.Pressed) -> None:

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
            subject_message = self.query_one("#subject-message", Static)

            new_subject = new_subject_input.value.strip().lower()

            if new_subject == "":
                subject_message.update("[red]Please enter a subject name.[/red]")
                return

            data = load_data()

            if new_subject in data["subjects"]:
                subject_message.update("[yellow]That subject already exists.[/yellow]")
                return

            data["subjects"].append(new_subject)
            data["subjects"].sort()

            save_data(data)

            self.update_dashboard()

            subject_message.update(f"[green]Added subject: {new_subject}[/green]")
            new_subject_input.value = ""
            return

        if event.button.id == "log-button":
            subject_select = self.query_one("#subject-select", Select)
            minutes_input = self.query_one("#minutes-input", Input)
            message = self.query_one("#message", Static)

            subject = subject_select.value
            minutes_text = minutes_input.value.strip()

            if subject is None or subject is False:
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