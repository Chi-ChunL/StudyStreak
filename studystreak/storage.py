import json
from pathlib import Path
from typing import Any

from studystreak.session import is_logged_in, get_session_data, save_session_data

DATA_FILE = Path("study_data.json")


def get_default_data():
    return {
        "sessions": [],
        "weekly_goal": 300,
        "subjects": [],
        "subject_websites": {}
    }

def repair_data(data):
    #repair missing data keys
    if "sessions" not in data:
        data["sessions"] = []

    if "weekly_goal" not in data:
        data["weekly_goal"] = 300

    if "subjects" not in data:
        data["subjects"] = []
    
    if "subject_websites" not in data:
        data["subject_websites"] = {}

    if "timetable" not in data:
        data["timetable"] = []

    return data

def load_legacy_data() -> dict[str, Any]:
    #load old unencrypted study data
    if not DATA_FILE.exists():
        return get_default_data()
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    
    except json.JSONDecodeError:
        return get_default_data()

    return repair_data(data)

def save_legacy_data(data: dict[str, Any]) -> None:
    #save old unencrypted study data
    data = repair_data(data)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def load_data() -> dict[str, Any]:
    #load active study data
    if is_logged_in():
        return repair_data(get_session_data())

    return load_legacy_data()


def save_data(data):
    #save active study data
    data = repair_data(data)

    if is_logged_in():
        save_session_data(data)
        return
    
    save_legacy_data(data)
