import json
from pathlib import Path


DATA_FILE = Path("study_data.json")


def get_default_data():
    return {
        "sessions": [],
        "weekly_goal": 300,
        "subjects": [],
        "subject_websites": {}
    }


def load_data():
    if not DATA_FILE.exists():
        return get_default_data()

    with open(DATA_FILE, "r") as file:
        data = json.load(file)

    if "sessions" not in data:
        data["sessions"] = []

    if "weekly_goal" not in data:
        data["weekly_goal"] = 300

    if "subjects" not in data:
        data["subjects"] = []
    
    if "subject_websites" not in data:
        data["subject_websites"] = {}

    return data


def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)