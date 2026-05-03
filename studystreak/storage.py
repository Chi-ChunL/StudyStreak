import json
from pathlib import Path


DATA_FILE = Path("study_data.json")

#load the study data from the json file
def load_data():
    if not DATA_FILE.exists():
        return {
            "sessions": []
        }
    
    with open(DATA_FILE, "r") as file:
        return json.load(file)

#saves study data into json file 
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
