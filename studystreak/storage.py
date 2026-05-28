import json
from copy import deepcopy
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from studystreak.session import (
    is_logged_in,
    get_session_data,
    save_session_data,
    get_session_username,
    get_session_password,
    get_server_token,
)

from studystreak.profile_sync import encrypt_profile_data
from studystreak.api_client import upload_profile_data


DATA_FILE = Path("study_data.json")


def get_default_data():
    return {
        "sessions": [],
        "weekly_goal": 300,
        "subjects": [],
        "subject_websites": {},
        "sync": {
            "device_id": None,
            "last_local_update": None,
            "last_cloud_sync": None,
            "last_sync_error": None,
        "sound_settings": {
            "ui": True,
            "focus_complete": True,
            "streak_protected": True,
        },
        },
    }

def get_utc_now_text():
    return datetime.now(timezone.utc).isoformat()

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

    if "sync" not in data:
        data["sync"] = {}
    
    if "device_id" not in data["sync"]:
        data["sync"]["device_id"] = None
    
    if "last_local_update" not in data["sync"]:
        data["sync"]["last_local_update"] = None
    
    if "last_cloud_sync" not in data["sync"]:
        data["sync"]["last_cloud_sync"] = None

    if "last_sync_error" not in data["sync"]:
        data["sync"]["last_sync_error"] = None

    if data["sync"]["device_id"] is None:
        data["sync"]["device_id"] = str(uuid4())
    
    if "sound_settings" not in data:
        data["sound_settings"] = {}
    
    if "ui" not in data["sound_settings"]:
        data["sound_settings"]["ui"] = True

    if "focus_complete" not in data["sound_settings"]:
        data["sound_settings"]["focus_complete"] = True
    
    if "streak_protected" not in data["sound_settings"]:
        data["sound_settings"]["streak_protected"] = True

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

    data["sync"]["last_local_update"] = get_utc_now_text()
    data["sync"]["last_sync_error"] = None

    if is_logged_in():
        save_session_data(data)
        sync_profile_data_in_background(data)
        return
    
    save_legacy_data(data)

def sync_profile_data_in_background(data):
    #keep local saves fast even when the server is slow or offline
    snapshot = deepcopy(data)
    thread = Thread(target=sync_profile_data, args=(snapshot,), daemon=True)
    thread.start()


def sync_profile_data(data):
    #upload encrypted profile data to the server
    token = get_server_token()

    if token is None:
        current_data = get_session_data()
        current_data["sync"]["last_sync_error"] = "Not logged in to server."
        save_session_data(current_data)
        return

    try:
        username = get_session_username()
        password = get_session_password()

        encrypted_profile_data = encrypt_profile_data(data, username, password)
        upload_profile_data(token, encrypted_profile_data)

        synced_at = get_utc_now_text()
        current_data = get_session_data()
        current_sync = current_data.get("sync", {})

        if current_sync.get("last_local_update") == data["sync"]["last_local_update"]:
            current_data["sync"]["last_cloud_sync"] = synced_at
            current_data["sync"]["last_sync_error"] = None
            save_session_data(current_data)

    except (RuntimeError, ValueError) as error:
        current_data = get_session_data()
        current_data["sync"]["last_sync_error"] = str(error)
        save_session_data(current_data)
