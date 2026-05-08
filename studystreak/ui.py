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
from textual.widgets import Header, Footer, Static, Input, Button, TabbedContent, TabPane

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

def get_recent_sessions(data, limit=5):
    sessions = data["sessions"]
    
    if len(sessions) == 0:
        return "No study session logged yet."
    
    recent_sessions = sessions[-limit:]
    recent_sessions.reverse()

    lines = ["[bold]Recent study sessions[/bold]"]

    for session in recent_sessions:
        subject = session["subject"]
        minutes = session["minutes"]
        session_date = session["date"]

        lines.append(f"{subject} - {minutes} minutes - {session_date}")
    
    return "\n".join(lines)

class StudyStreakApp(App):

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("escape", "escape_quit", "Quit"),
        ("q", "quit", "Quit")
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

                with TabPane("Log Session", id="log-tab"):
                    yield Static("Log your study session below.", id="log-title")

                    yield Input(placeholder="Subject, e.g. maths", id="subject-input")
                    yield Input(placeholder="Minutes, e.g. 30", id="minutes-input")

                    with Horizontal(id="button-row"):
                        yield Button("Log Session", id="log-button")
                        yield Button("Clear", id="clear-button")
                
                    yield Static("", id="message")

        yield Footer()
    

    def on_mount(self):
        self.update_dashboard()

    def update_dashboard(self):
        data = load_data()

        streak_count = calculate_current_streak(data)
        today_minutes = calculate_today_minutes(data)
        today_sessions = calculate_today_sessions(data)

        dashboard = self.query_one("#dashboard", Static)
        recent_sessions = self.query_one("#recent-sessions", Static)

        dashboard.update(
            f"[bold]Current streak:[/bold] {streak_count} days\n"
            f"[bold] Studied today:[/bold] {today_minutes} minutes \n"
            f"[bold]Sessions today:[/bold] {today_sessions}"
        )

        recent_sessions.update(get_recent_sessions(data))


    def action_escape_quit(self):
        current_time = datetime.now()

        message = self.query_one("#message", Static)

        if self.last_escape_time is None:
            self.last_escape_time = current_time
            message.update("[yellow]Press Esc again to quit.[/yellow]")
            return
        
        time_difference = current_time - self.last_escape_time

        if time_difference.total_seconds() <= 2:
            self.exit()
        else:
            self.last_escape_time = current_time
            message.update("[yellow]Press Esc again to quit.[/yellow]")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        subject_input = self.query_one("#subject-input", Input)
        minutes_input = self.query_one("#minutes-input", Input)
        message = self.query_one("#message", Static)

        if event.button.id == "clear-button":
            subject_input.value = ""
            minutes_input.value = ""
            message.update("")
            return
        
        if event.button.id == "log-button":
            subject = subject_input.value.strip()
            minutes_text = minutes_input.value.strip()

            if subject == "":
                message.update("[red]Please enter a subject.[/red]")
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

            session = {
                "subject": subject.lower(),
                "minutes": minutes,
                "date": str(date.today())
            }

            data["sessions"].append(session)
            save_data(data)

            self.update_dashboard()

            message.update(f"[green]Logged {minutes} minutes of {subject} study.[/green]")

            subject_input.value = ""
            minutes_input.value = ""


