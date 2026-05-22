import json
from pathlib import Path

import keyring


APP_NAME = "StudyStreak"
CACHE_FILE = Path("auth_cache.json")

def save_remembered_login(username: str, password: str) -> None:
    #save remembered login securely
    username = username.strip().lower()

    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump({"username": username}, file, indent=4)
    
    keyring.set_password(APP_NAME, username, password)


def get_remembered_username() -> str | None:
    #get remembered username
    if not CACHE_FILE.exists():
        return None
    
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return None
    
    return data.get("username")

def get_remembered_password(username: str) -> str | None:
    #get remembered password
    return keyring.get_password(APP_NAME, username)

def clear_remembered_login() -> None:
    #clear remembered login
    username = get_remembered_username()

    if username is not None:
        try:
            keyring.delete_password(APP_NAME, username)
        except keyring.errors.PasswordDeleteError:
            pass
    
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
