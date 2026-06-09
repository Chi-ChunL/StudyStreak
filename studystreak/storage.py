import json
from copy import deepcopy
from pathlib import Path
from threading import Lock, Thread
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone
import hmac
import hashlib

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
_SYNC_LOCK = Lock()
_latest_sync_snapshot = None
_sync_worker_running = False


def get_default_data():
    return {
        "sessions": [],
        "focus_quality_sessions": [],
        "weekly_goal": 300,
        "subjects": [],
        "subject_websites": {},
        "sync": {
            "device_id": None,
            "last_local_update": None,
            "last_cloud_sync": None,
            "last_sync_error": None,
        },
        "sound_settings": {
            "ui": True,
            "focus_complete": True,
            "streak_protected": True,
            "achievement": True,
        },

        "notification-settings": {
            "focus_complete": True,
            "sync_failed": True,
            "achievement": True,
        },
        "appearance_settings": {
            "theme": "dark",
        },
        "achievements": {
            "unlocked": [],
        },
        "focus_import_settings": {
            "secret": "",
        },

    }

def get_utc_now_text():
    return datetime.now(timezone.utc).isoformat()

def repair_data(data):
    #repair missing data keys
    if "sessions" not in data:
        data["sessions"] = []
    
    if "focus_quality_sessions" not in data:
        data["focus_quality_sessions"] = []
    
    if not isinstance(data["focus_quality_sessions"], list):
        data["focus_quality_sessions"] = []

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

    if "notification_settings" in data:
        data["notification-settings"] = data.pop("notification_settings")

    if "notification-settings" not in data:
        data["notification-settings"] = {}
    
    if "focus_complete" not in data["notification-settings"]:
        data["notification-settings"]["focus_complete"] = True

    if "sync_failed" not in data["notification-settings"]:
        data["notification-settings"]["sync_failed"] = True

    if "appearance_settings" not in data:
        data["appearance_settings"] = {}

    if "theme" not in data["appearance_settings"]:
        data["appearance_settings"]["theme"] = "dark"

    if data["appearance_settings"]["theme"] not in ["dark", "light"]:
        data["appearance_settings"]["theme"] = "dark"

    if "achievements" not in data:
        data["achievements"] = {}

    if "unlocked" not in data["achievements"]:
        data["achievements"]["unlocked"] = []

    if "achievement" not in data["notification-settings"]:
        data["notification-settings"]["achievement"] = True
    
    if "achievement" not in data["sound_settings"]:
        data["sound_settings"]["achievement"] = True

    if "focus_import_settings" not in data:
        data["focus_import_settings"] = {}
    
    if "secret" not in data["focus_import_settings"]:
        data["focus_import_settings"]["secret"] = ""

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

def get_focus_signature_payload(summary):
    return json.dumps(
        summary,
        sort_keys=True,
        separators=(",", ":")
    )

def sign_focus_summary(summary, secret):
    return hmac.new(
        secret.encode("utf-8"),
        get_focus_signature_payload(summary).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

def unwrap_signed_focus_summary(raw_summary, secret):
    if not str(secret).strip():
        raise ValueError("Set a focus import key in Settings first.")

    if "payload" not in raw_summary or "signature" not in raw_summary:
        raise ValueError("Set a focus import key in Settings first.")
    
    payload = raw_summary["payload"]
    signature = str(raw_summary["signature"])

    expected_signature = sign_focus_summary(payload, secret)

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Focus summary signature is invalid.")

    return payload

def normalise_focus_quality_session(raw_summary):
    if not isinstance(raw_summary, dict):
        raise ValueError("Focus summary must be a JSON object.")

    if raw_summary.get("source") != "chrome_extension":
        raise ValueError("Focus summary must come from the Chrome extension.")

    completed_at = str(raw_summary.get("completed_at", "")).strip()
    if completed_at == "":
        raise ValueError("Focus summary is missing completed_at.")

    try:
        datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Focus summary has an invalid completed_at date.") from error

    try:
        session = {
            "source": "chrome_extension",
            "score": int(raw_summary.get("score", 0)),
            "focused_seconds": int(raw_summary.get("focused_seconds", 0)),
            "distracted_seconds": int(raw_summary.get("distracted_seconds", 0)),
            "idle_seconds": int(raw_summary.get("idle_seconds", 0)),
            "top_distracted_domain": str(
                raw_summary.get("top_distracted_domain", "none")
            ),
            "completed_at": completed_at,
            "imported_at": get_utc_now_text(),
        }
    except (TypeError, ValueError) as error:
        raise ValueError("Focus summary has invalid number fields.") from error

    if session["score"] < 0 or session["score"] > 100:
        raise ValueError("Focus score must be between 0 and 100.")

    for key in ["focused_seconds", "distracted_seconds", "idle_seconds"]:
        if session[key] < 0:
            raise ValueError("Focus times cannot be negative.")

    return session


def save_focus_quality_session(raw_summary):
    data = load_data()

    secret = data.get("focus_import_settings", {}).get("secret", "")
    raw_summary = unwrap_signed_focus_summary(raw_summary, secret)
    session = normalise_focus_quality_session(raw_summary)

    existing_sessions = data.get("focus_quality_sessions", [])
    data["focus_quality_sessions"] = [
        session,
        *[
            existing
            for existing in existing_sessions
            if existing.get("completed_at") != session["completed_at"]
        ],
    ][:20]

    save_data(data)
    return session


def save_focus_quality_json(raw_text):
    raw_text = raw_text.strip()

    if raw_text == "":
        raise ValueError("Paste a focus summary JSON first.")

    try:
        raw_summary = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError("Focus summary JSON is not valid.") from error

    return save_focus_quality_session(raw_summary)

def sync_profile_data_in_background(data):
    #keep local saves fast even when the server is slow or offline
    global _latest_sync_snapshot
    global _sync_worker_running

    snapshot = deepcopy(data)

    with _SYNC_LOCK:
        _latest_sync_snapshot = snapshot

        if _sync_worker_running:
            return

        _sync_worker_running = True

    thread = Thread(target=run_sync_worker, daemon=True)
    thread.start()

def run_sync_worker():
    #upload snapshot in order while skipping unecesaary queued versions
    global _latest_sync_snapshot
    global _sync_worker_running

    while True:
        with _SYNC_LOCK:
            snapshot = _latest_sync_snapshot
            _latest_sync_snapshot = None

            if snapshot is None:
                _sync_worker_running = False
                return

        try:
            sync_profile_data(snapshot)
        except Exception:
            pass

def update_sync_result_if_current(data, synced_at=None, error_message=None):
    #ignore results from an upload if a newer local save already exists
    try:
        current_data = get_session_data()
    except RuntimeError:
        return

    current_sync = current_data.get("sync", {})

    if current_sync.get("last_local_update") != data["sync"]["last_local_update"]:
        return

    if synced_at is not None:
        current_data["sync"]["last_cloud_sync"] = synced_at

    current_data["sync"]["last_sync_error"] = error_message
    save_session_data(current_data)


def sync_profile_data(data):
    #upload encrypted profile data to the server
    token = get_server_token()

    if token is None:
        update_sync_result_if_current(
            data,
            error_message="Not logged in to server.",
        )
        return

    try:
        username = get_session_username()
        password = get_session_password()

        encrypted_profile_data = encrypt_profile_data(data, username, password)
        upload_profile_data(token, encrypted_profile_data)

    except Exception as error:
        update_sync_result_if_current(
            data,
            error_message=str(error),
        )
        return

    update_sync_result_if_current(
        data,
        synced_at=get_utc_now_text(),
        error_message=None,
    )
