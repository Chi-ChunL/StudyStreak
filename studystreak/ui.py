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


from datetime import date

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Static, Input, Button

from studystreak.storage import load_data, save_data


class StudyStreakApp(App):

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            yield Static("StudyStreak CLI", id="title")
            yield Static("Log your study session below.", id="subtitle")

            yield Input(placeholder="Subject, e.g. maths", id="subject-input")
            yield Input(placeholder="Minutess, e.g. 30", id="minutes-input")

            with Horizontal(id="button-row"):
                yield Button("Log Session", id="log-button")
                yield Button("Clear", id="clear-button")
            
            yield Static("", id="message")

        yield Footer()
    
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

            message.update(f"[green]Logged {minutes} minutes of {subject} study.[/green]")

            subject_input.value = ""
            minutes_input.value = ""


