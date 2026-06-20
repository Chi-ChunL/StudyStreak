import typer
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from datetime import date
import pwinput

from studystreak.storage import (
    calculate_streak_days,
    load_data,
    protect_streak_today,
    save_data,
)
from studystreak.ui import plain_fire_art, coloured_fire_art, StudyStreakApp
from studystreak.accounts import (
    create_account,
    login_account,
    logout_account,
    list_accounts,
    get_current_user,
)
from studystreak.session import set_session, clear_session


app = typer.Typer(invoke_without_command=True)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    # Make the PyPI command feel like an app launcher.
    if ctx.invoked_subcommand is None:
        study_app = StudyStreakApp()
        study_app.run()


@app.command()
def log(subject: str, minutes: int):
    # Log a session from the command line.
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
    protect_streak_today(data)
    save_data(data)

    console.print(f"[green]Logged {minutes} minutes of {subject} study.[/green]")


@app.command()
def today():
    # Show today's study sessions.
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
    # Show current study streak.
    data = load_data()
    streak_count = calculate_streak_days(data.get("streak_days", []))

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
    # Open StudyStreak in Textual.
    study_app = StudyStreakApp()
    study_app.run()


@app.command()
def create_user(username: str, display_name: str = ""):
    # Create a local encrypted StudyStreak account.
    password = pwinput.pwinput(prompt="Password: ", mask="*")
    confirm_password = pwinput.pwinput(prompt="Confirm Password: ", mask="*")

    if password != confirm_password:
        console.print("[red]Passwords do not match.[/red]")
        return

    try:
        create_account(
            username=username,
            password=password,
            display_name=display_name if display_name else None,
        )
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        return

    console.print(f"[green]Created account: {username}[/green]")


@app.command()
def login(username: str):
    # Test login for a local StudyStreak account.
    password = pwinput.pwinput(prompt="Password: ", mask="*")

    try:
        private_data = login_account(username, password)
        set_session(username, password, private_data)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        return

    console.print(f"[green]Logged in as {username}.[/green]")
    console.print(
        f"[cyan]Loaded encrypted data with {len(private_data['sessions'])} saved session(s).[/cyan]"
    )


@app.command()
def logout():
    # Log out of the current account.
    logout_account()
    clear_session()
    console.print("[yellow]Logged out.[/yellow]")


@app.command()
def users():
    # Show local StudyStreak accounts.
    accounts = list_accounts()
    current_user = get_current_user()

    if len(accounts) == 0:
        console.print("[yellow]No accounts created yet.[/yellow]")
        return

    console.print("[bold cyan]Local accounts[/bold cyan]")

    for username in accounts:
        if username == current_user:
            console.print(f"- {username} [green](current)[/green]")
        else:
            console.print(f"- {username}")


if __name__ == "__main__":
    app()
