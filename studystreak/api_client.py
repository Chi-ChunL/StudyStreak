import os

from dotenv import load_dotenv
import requests


load_dotenv()
BASE_URL = os.getenv("STUDYSTREAK_API_URL", "http://127.0.0.1:8000")

def login_to_server(username: str, password: str) -> str:
    #login to backend server
    response = requests.post(
        f"{BASE_URL}/login",
        json={
            "username": username,
            "password": password,
        },
        timeout=10
    )

    if response.status_code != 200:
        raise ValueError("Server login failed")
    
    data = response.json()
    return data["access_token"]


def upload_focus_session(token: str, subject: str, minutes: int, website: str | None) -> None:
    #upload completed focus session
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

    if response.status_code != 200:
        raise ValueError("Could not upload focus session")
    

def get_leaderboard(period="all") -> list[dict]:
    #get server leaderboard
    response = requests.get(
        f"{BASE_URL}/leaderboard",
        params={"period": period},
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError("Could not load leaderboard")
    
    return response.json()

def signup_to_server(username: str, password: str, display_name: str | None = None) -> None:
    #create backend server account
    response = requests.post(
        f"{BASE_URL}/signup",
        json={
            "username": username,
            "password": password,
            "display_name": display_name,
        },
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError("Server signup failed.")


def check_server_status() -> bool:
    #checl if backend server is online
    try:
        response = requests.get(
            f"{BASE_URL}/",
            timeout=5,
        )

        return response.status_code == 200
    
    except requests.RequestException:
        return False
    