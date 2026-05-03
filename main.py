import typer
from rich.console import Console
from datetime import date


from studystreak.storage import load_data, save_data


app = typer.Typer()
console = Console()


@app.command()
#log a study session manually
def log(subject: str, minutes:int):
    if minutes <= 0:
        console.print("[red]Minutes must be more than 0.[/red]")
        return
    
    data = load_data()

    session = {
        "subject": subject.lower(),
        "minutes": minutes,
        "date": str(date.today())
    }

    data["sessions"].append(session)
    save_data(data)

    console.print(f"[green]Logged {minutes} minutes of {subject} study![/green]")

@app.command()
#show all study session completed today
def today():

    data = load_data()
    today_date = str(date.today())

    today_sessions = []

    for session in data["sessions"]:
        if session["date"] == today_date:
            today_sessions.append(session)
    
    if len(today_sessions) == 0:
        console.print("[yellow]You have not studied today yet.[/yellow]")
        return
    
    total_minutes = 0
    console.print("[bold cyan]Today's Study Sessions[/bold cyan]")
    
    for session in today_sessions:
        console.print(f"- { session['subject']}: {session['minutes']} minutes")
        total_minutes += session["minutes"]

    
    console.print(f"\n[green]Total today: {total_minutes} minutes[/green]")

@app.command()
#show total study time for each subject
def stats():

    data = load_data()

    if len(data["sessions"]) == 0:
        console.print("[yellow]No study sessions logged yet.[/yellow]")
        return
    
    subject_totals = {}

    for session in data["sessions"]:
        subject = session["subject"]
        minutes = session["minutes"]

        if subject not in subject_totals:
            subject_totals[subject] = 0
        
        subject_totals[subject] += minutes

    console.print("[bold cyan]Study Statistics[/bold cyan]")

    for subject, minutes in subject_totals.items():
        hours = minutes //60
        remaining_minutes = minutes % 60

        console.print(f"- {subject}: {hours}h {remaining_minutes}m")

if __name__ == "__main__":
    app()