import typer
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from datetime import date, timedelta

from studystreak.storage import load_data, save_data
from studystreak.ui import plain_fire_art, coloured_fire_art, StudyStreakApp


app = typer.Typer()
console = Console()


def calculate_streak(data):
    study_dates = set()

    for session in data["sessions"]:
        study_dates.add(session["date"])

    current_day = date.today()
    streak_count = 0

    while str(current_day) in study_dates:
        streak_count += 1
        current_day = current_day - timedelta(days=1)

    return streak_count


@app.command()
def log(subject: str, minutes: int):
    """
    Log a study session from the command line.
    """
    if minutes <= 0:
        console.print("[red]Minutes must be more than 0.[/red]")
        return

    data = load_data()

    session = {
        "subject": subject.lower(),
        "minutes": minutes,
        "date": str(date.today()),
    }

    data["sessions"].append(session)
    save_data(data)

    console.print(f"[green]Logged {minutes} minutes of {subject} study.[/green]")


@app.command()
def today():
    """
    Show today's study sessions.
    """
    data = load_data()
    today_date = str(date.today())

    today_sessions = [
        session for session in data["sessions"]
        if session["date"] == today_date
    ]

    if len(today_sessions) == 0:
        console.print("[yellow]You have not studied today yet.[/yellow]")
        return

    total_minutes = 0
    console.print("[bold cyan]Today's Study Sessions[/bold cyan]")

    for session in today_sessions:
        console.print(f"- {session['subject']}: {session['minutes']} minutes")
        total_minutes += session["minutes"]

    console.print(f"\n[green]Total today: {total_minutes} minutes[/green]")


@app.command()
def streak():
    """
    Show the current study streak.
    """
    data = load_data()
    streak_count = calculate_streak(data)

    if streak_count == 0:
        message = f"""
{plain_fire_art}

Study streak: 0 days

You do not currently have an active streak.
Log a session today to start one.
"""
        border_colour = "white"

    elif streak_count == 1:
        message = f"""
{coloured_fire_art}

[bold orange1]Study streak: 1 day[/bold orange1]

Good start. Study again tomorrow to keep it going.
"""
        border_colour = "orange1"

    else:
        message = f"""
{coloured_fire_art}

[bold orange1]Study streak: {streak_count} days[/bold orange1]

Great work. Your consistency is building.
"""
        border_colour = "orange1"

    console.print(
        Panel(
            Align.center(message),
            title="StudyStreak",
            border_style=border_colour,
        )
    )


@app.command()
def ui():
    """
    Open the StudyStreak Textual interface.
    """
    study_app = StudyStreakApp()
    study_app.run()


if __name__ == "__main__":
    app()