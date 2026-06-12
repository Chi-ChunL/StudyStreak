import os
from pathlib import Path

from dotenv import load_dotenv
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = os.getenv("STUDYSTREAK_API_URL", "http://127.0.0.1:8000")


def get_error_detail(response: requests.Response) -> str:
    #return the useful FastAPI error instead of hiding it behind a generic message
    try:
        data = response.json()
    except ValueError:
        return response.text.strip() or response.reason

    detail = data.get("detail")

    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        messages = []

        for item in detail:
            if isinstance(item, dict):
                message = item.get("msg", str(item))
                location = item.get("loc", [])

                if location:
                    messages.append(f"{'.'.join(str(part) for part in location)}: {message}")
                else:
                    messages.append(message)
            else:
                messages.append(str(item))

        return "; ".join(messages)

    if detail is not None:
        return str(detail)

    return response.text.strip() or response.reason


def raise_server_error(action: str, response: requests.Response) -> None:
    detail = get_error_detail(response)
    raise ValueError(f"{action} failed ({response.status_code}): {detail}")


def login_to_server(username: str, password: str) -> str:
    #login to backend server
    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "username": username,
                "password": password,
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Server login", response)

    data = response.json()
    return data["access_token"]


def signup_to_server(username: str, password: str, display_name: str | None = None) -> None:
    #create backend server account
    try:
        response = requests.post(
            f"{BASE_URL}/signup",
            json={
                "username": username,
                "password": password,
                "display_name": display_name,
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Server signup", response)


def upload_focus_session(token: str, subject: str, minutes: int, website: str | None) -> None:
    #upload completed focus session
    try:
        response = requests.post(
            f"{BASE_URL}/focus-sessions",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "subject": subject,
                "minutes": minutes,
                "website": website,
                "completed": True,
                "source": "focus_cli",
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Focus upload", response)


def get_leaderboard(period="all") -> list[dict]:
    #get server leaderboard
    try:
        response = requests.get(
            f"{BASE_URL}/leaderboard",
            params={"period": period},
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Leaderboard load", response)

    return response.json()


def check_server_status() -> bool:
    #check if backend server is online
    try:
        response = requests.get(
            f"{BASE_URL}/",
            timeout=5,
        )

        return response.status_code == 200

    except requests.RequestException:
        return False
    
def get_profile_data(token: str) -> str | None:
    #get encrypted profile data from server
    try:
        response = requests.get(
            f"{BASE_URL}/profile-data",
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Profile load", response)

    data = response.json()
    return data["encrypted_profile_data"]


def upload_profile_data(token: str, encrypted_profile_data: str) -> None:
    #upload encrypted profile data to server
    try:
        response = requests.put(
            f"{BASE_URL}/profile-data",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "encrypted_profile_data": encrypted_profile_data,
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Profile upload", response)


def upload_subjects(token: str, subjects: list[str]) -> None:
    #upload subject list for the Chrome extension
    try:
        response = requests.put(
            f"{BASE_URL}/subjects",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "subjects": subjects,
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Subject sync", response)


def get_focus_quality_sessions(token: str) -> list[dict]:
    #download rich Chrome focus-quality summaries for the logged-in user
    try:
        response = requests.get(
            f"{BASE_URL}/focus-quality-sessions",
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )

    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error

    if response.status_code != 200:
        raise_server_error("Focus quality sync", response)

    return response.json()

def upload_streak(token: str, current_streak: int) -> None:
    try:
        response = requests.put(
            f"{BASE_URL}/streak",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "current_streak": current_streak,
            },
            timeout=10,
        )
    except requests.RequestException as error:
        raise ValueError(f"Could not connect to server at {BASE_URL}: {error}") from error
    
    if response.status_code !=200:
        raise_server_error("Streak sync", response)