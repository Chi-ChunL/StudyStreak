import json
from pathlib import Path


DATA_FILE = Path("study_data.json")


def get_deafault_data():
    return {
        "sessions": [],
        "weekly_goal": 300
    }

#load the study data from the json file
def load_data():
    if not DATA_FILE.exists():
        return get_deafault_data()
    
    with open(DATA_FILE, "r") as file:
        return json.load(file)
    
    if "sessions" not in data:
        data["sessions"] = []
    
    if "weekly_goal" not in data:
        data["weekly_goal"] = []
    
    return data

#saves study data into json file 
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
