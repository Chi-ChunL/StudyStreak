import json
from copy import deepcopy
from threading import Lock, Thread
from typing import Any
from uuid import uuid4
from datetime import date, datetime, timezone, timedelta
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

from studystreak.paths import get_app_data_file, migrate_legacy_file
from studystreak.profile_sync import encrypt_profile_data
from studystreak.api_client import (
    upload_profile_data,
    upload_subject_websites,
    upload_subjects,
    upload_streak,
    upload_timetable,
    upload_todo_items,
)


DATA_FILE = get_app_data_file("study_data.json")
migrate_legacy_file("study_data.json", DATA_FILE)
_SYNC_LOCK = Lock()
_latest_sync_snapshot = None
_sync_worker_running = False


def get_default_data():
    return {
        "sessions": [],
        "streak_days": [],
        "focus_quality_sessions": [],
        "weekly_goal": 300,
        "subjects": [],
        "subject_websites": {},
        "subject_topics": {},
        "todo_items": [],
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
        "onboarding": {
            "tour_completed": False,
            "tour_declined": False,
        },
        "update_check": {
            "last_checked": None,
            "installed_version": None,
            "latest_version": None,
            "update_available": False,
            "last_error": None,
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

def get_today_text():
    return str(date.today())

def clean_streak_days(raw_days):
    today = date.today()
    cleaned_days = []

    if not isinstance(raw_days, list):
        return []

    for raw_day in raw_days:
        day_text = str(raw_day).strip()

        try:
            day = date.fromisoformat(day_text)
        except ValueError:
            continue

        if day > today:
            continue

        if day_text not in cleaned_days:
            cleaned_days.append(day_text)

    return sorted(cleaned_days)

def get_session_streak_days(data):
    days = []

    for session in data.get("sessions", []):
        if session.get("source") == "chrome_extension":
            continue

        day_text = str(session.get("date", "")).strip()

        if day_text and day_text not in days:
            days.append(day_text)

    return clean_streak_days(days)

def clean_website_list(raw_websites):
    if isinstance(raw_websites, str):
        raw_items = raw_websites.replace(",", "\n").splitlines()
    elif isinstance(raw_websites, list):
        raw_items = raw_websites
    else:
        raw_items = []

    websites = []

    for raw_website in raw_items:
        website = str(raw_website).strip()

        if website == "":
            continue

        if not website.startswith("http://") and not website.startswith("https://"):
            website = "https://" + website

        if website not in websites:
            websites.append(website)

    return websites[:10]

def clean_subject_websites(subject_websites):
    if not isinstance(subject_websites, dict):
        return {}

    cleaned = {}

    for subject, websites in subject_websites.items():
        clean_subject = str(subject).strip().lower()

        if clean_subject == "":
            continue

        cleaned[clean_subject] = clean_website_list(websites)

    return cleaned

def clean_topic_list(raw_topics):
    if isinstance(raw_topics, str):
        raw_items = raw_topics.replace(",", "\n").splitlines()
    elif isinstance(raw_topics, list):
        raw_items = raw_topics
    else:
        raw_items = []

    topics = []

    for raw_topic in raw_items:
        topic = str(raw_topic).strip()

        if topic == "":
            continue

        if topic not in topics:
            topics.append(topic)

    return topics[:30]

def clean_subject_topics(subject_topics):
    if not isinstance(subject_topics, dict):
        return {}

    cleaned = {}

    for subject, topics in subject_topics.items():
        clean_subject = str(subject).strip().lower()

        if clean_subject == "":
            continue

        cleaned[clean_subject] = clean_topic_list(topics)

    return cleaned

def clean_todo_items(raw_items):
    if not isinstance(raw_items, list):
        return []

    cleaned = []
    seen_ids = set()

    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            continue

        text = str(raw_item.get("text", "")).strip()

        if text == "":
            continue

        item_id = str(raw_item.get("id", "")).strip()

        if item_id == "":
            item_id = f"todo-{uuid4()}-{index}"

        item_id = item_id[:80]

        if item_id in seen_ids:
            continue

        seen_ids.add(item_id)
        cleaned.append({
            "id": item_id,
            "text": text[:120],
            "done": bool(raw_item.get("done", False)),
        })

        if len(cleaned) >= 50:
            break

    return cleaned

def merge_todo_items(data, server_todo_items):
    data = repair_data(data)
    server_items = clean_todo_items(server_todo_items)
    local_items = clean_todo_items(data.get("todo_items", []))
    local_by_id = {
        item["id"]: item
        for item in local_items
    }
    merged_items = []
    updates = 0

    for server_item in server_items:
        if local_by_id.get(server_item["id"]) != server_item:
            updates += 1

        merged_items.append(server_item)
        local_by_id.pop(server_item["id"], None)

    merged_items.extend(local_by_id.values())
    merged_items = clean_todo_items(merged_items)

    if data.get("todo_items", []) != merged_items:
        data["todo_items"] = merged_items

    return updates

def merge_subject_websites(data, server_subject_websites):
    data = repair_data(data)
    server_subject_websites = clean_subject_websites(server_subject_websites)
    changed_subjects = 0

    for subject, websites in server_subject_websites.items():
        if subject not in data["subjects"]:
            data["subjects"].append(subject)

        if data["subject_websites"].get(subject, []) != websites:
            data["subject_websites"][subject] = websites
            changed_subjects += 1

    data["subjects"].sort()
    data["subject_websites"] = clean_subject_websites(data["subject_websites"])
    return changed_subjects

def protect_streak_today(data):
    data = repair_data(data)
    today_text = get_today_text()

    if today_text in data["streak_days"]:
        return False

    data["streak_days"].append(today_text)
    data["streak_days"] = clean_streak_days(data["streak_days"])
    return True

def repair_data(data):
    #repair missing data keys
    if "sessions" not in data:
        data["sessions"] = []

    if "streak_days" not in data:
        data["streak_days"] = get_session_streak_days(data)
    else:
        data["streak_days"] = clean_streak_days(data["streak_days"])
    
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

    data["subject_websites"] = clean_subject_websites(data["subject_websites"])

    if "subject_topics" not in data:
        data["subject_topics"] = {}

    data["subject_topics"] = clean_subject_topics(data["subject_topics"])

    if "todo_items" not in data:
        data["todo_items"] = []

    data["todo_items"] = clean_todo_items(data["todo_items"])

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

    if "onboarding" not in data:
        data["onboarding"] = {}

    if "tour_completed" not in data["onboarding"]:
        data["onboarding"]["tour_completed"] = False

    if "tour_declined" not in data["onboarding"]:
        data["onboarding"]["tour_declined"] = False

    if "update_check" not in data:
        data["update_check"] = {}

    if "last_checked" not in data["update_check"]:
        data["update_check"]["last_checked"] = None

    if "installed_version" not in data["update_check"]:
        data["update_check"]["installed_version"] = None

    if "latest_version" not in data["update_check"]:
        data["update_check"]["latest_version"] = None

    if "update_available" not in data["update_check"]:
        data["update_check"]["update_available"] = False

    if "last_error" not in data["update_check"]:
        data["update_check"]["last_error"] = None

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

def save_local_data_without_sync(data):
    #save local data without starting a cloud sync worker
    data = repair_data(data)

    if is_logged_in():
        save_session_data(data)
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

    subject = str(raw_summary.get("subject", "unknown")).strip().lower()

    if subject == "":
        subject = "unknown"

    if len(subject) > 50:
        raise ValueError("Focus summary subject is too long.")

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
            "subject": subject,
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


def get_focus_quality_study_minutes(session):
    focused_seconds = int(session.get("focused_seconds", 0))

    if focused_seconds <= 0:
        return 0

    return max(1, int((focused_seconds + 30) // 60))


def get_focus_quality_study_date(session):
    completed_at = session["completed_at"]
    completed_datetime = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    if completed_datetime.tzinfo is not None:
        completed_datetime = completed_datetime.astimezone()

    return str(completed_datetime.date())


def focus_quality_session_protects_today(session):
    return (
        get_focus_quality_study_minutes(session) > 0
        and get_focus_quality_study_date(session) == get_today_text()
    )


def merge_focus_quality_study_sessions(data, focus_quality_sessions):
    existing_sessions_by_completed_at = {
        session.get("completed_at"): session
        for session in data.get("sessions", [])
        if session.get("source") == "chrome_extension"
        and session.get("completed_at")
    }
    changed_count = 0

    sorted_focus_sessions = sorted(
        focus_quality_sessions,
        key=lambda session: session.get("completed_at", ""),
    )

    for session in sorted_focus_sessions:
        completed_at = session["completed_at"]
        minutes = get_focus_quality_study_minutes(session)

        if minutes <= 0:
            continue

        study_session = {
            "subject": session["subject"],
            "minutes": minutes,
            "date": get_focus_quality_study_date(session),
            "source": "chrome_extension",
            "completed_at": completed_at,
        }
        existing_session = existing_sessions_by_completed_at.get(completed_at)

        if existing_session is None:
            data["sessions"].append(study_session)
            existing_sessions_by_completed_at[completed_at] = study_session
            changed_count += 1
            continue

        if any(
            existing_session.get(key) != value
            for key, value in study_session.items()
        ):
            existing_session.update(study_session)
            changed_count += 1

    return changed_count


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

    merge_focus_quality_study_sessions(data, [session])
    if focus_quality_session_protects_today(session):
        protect_streak_today(data)
    save_data(data)
    return session


def merge_focus_quality_sessions(data, server_sessions):
    data = repair_data(data)

    existing_sessions = data.get("focus_quality_sessions", [])
    sessions_by_completed_at = {
        session.get("completed_at"): session
        for session in existing_sessions
        if session.get("completed_at")
    }
    added_count = 0

    for raw_session in server_sessions:
        trusted_summary = {
            **raw_session,
            "source": "chrome_extension",
        }
        session = normalise_focus_quality_session(trusted_summary)
        completed_at = session["completed_at"]

        if completed_at not in sessions_by_completed_at:
            added_count += 1

        sessions_by_completed_at[completed_at] = session

    data["focus_quality_sessions"] = sorted(
        sessions_by_completed_at.values(),
        key=lambda session: session.get("completed_at", ""),
        reverse=True,
    )[:20]

    study_added_count = merge_focus_quality_study_sessions(
        data,
        sessions_by_completed_at.values(),
    )
    protected_today = any(
        focus_quality_session_protects_today(session)
        for session in sessions_by_completed_at.values()
    )
    streak_added_count = 1 if protected_today and protect_streak_today(data) else 0

    return added_count + study_added_count + streak_added_count


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

def calculate_streak_days(streak_days):
    protected_days = set(clean_streak_days(streak_days))
    current_day = date.today()
    streak_count = 0

    while str(current_day) in protected_days:
        streak_count += 1
        current_day = current_day - timedelta(days=1)
    
    return streak_count

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
        current_streak = calculate_streak_days(data.get("streak_days", []))

        sync_steps = [
            ("Profile upload", lambda: upload_profile_data(token, encrypted_profile_data)),
            ("Streak upload", lambda: upload_streak(token, current_streak)),
            ("Subject upload", lambda: upload_subjects(token, data.get("subjects", []))),
            (
                "Subject website upload",
                lambda: upload_subject_websites(token, data.get("subject_websites", {})),
            ),
            ("Todo upload", lambda: upload_todo_items(token, data.get("todo_items", []))),
            ("Timetable upload", lambda: upload_timetable(token, data.get("timetable", []))),
        ]

        for step_name, sync_step in sync_steps:
            try:
                sync_step()
            except Exception as error:
                raise ValueError(f"{step_name}: {error}") from error

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
