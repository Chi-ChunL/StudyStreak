import json
import re
from pathlib import Path
from typing import Any

from cryptography.fernet import InvalidToken

from studystreak.security import (
    hash_password,
    verify_password,
    generate_salt,
    encrypt_text,
    decrypt_text,
)


ACCOUNTS_FILE = Path("accounts.json")

def get_empty_private_data() -> dict[str, Any]:
    return{
        "sessions": [],
        "weekly_goal": 300,
        "subjects": [],
        "subject_websites": {},
        "leaderboard_opt_in": False,
        "public_summary": {
            "weekly_minutes": 0,
            "current_streak": 0,
            "average_focsu_score": 0,
        },
    }

def get_default_accounts_data() -> dict[str, Any]:
    return {
        "current_user": None,
        "users": {},
    }

def load_account_data() -> dict[str, Any]:
    if not ACCOUNTS_FILE.exists():
        return get_default_accounts_data()
    
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return get_default_accounts_data()

    if "current_user" not in data:
        data["current_user"] = None
    
    if "users" not in data:
        data["users"] = {}
    
    return data

def save_accounts_data(data: dict[str, Any]) -> None:
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    

def normalise_username(username: str) -> str:
    return username.strip().lower()

def validate_username(username: str) -> None:
    if username == "":
        raise ValueError("Username cannot be empty")
    
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    
    if len(username) > 24:
        raise ValueError("Username must be 24 characters or fewer.")

    if not re.fullmatch(r"[a-zA-Z0-9_-]+", username):
        raise ValueError("Username can only contain letters, numbers, underscores and hyphens.")

def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(password) > 128:
        raise ValueError("Password must be 128 characters or fewer.")
    
    if password.strip() == "":
        raise ValueError("Password cannot be blank.")

def create_account(username: str, password: str, display_name: str | None = None) -> None:
    username = normalise_username(username)
    validate_username(username)
    validate_password(password)

    data = load_account_data()

    if username in data["users"]:
        raise ValueError("That username already exist.")
    
    encryption_salt = generate_salt()
    private_data = get_empty_private_data()
    private_data_json = json.dumps(private_data)

    encrypted_private_data = encrypt_text(
        text=private_data_json,
        password=password,
        salt=encryption_salt,
    )

    data["users"][username] = {
        "display_name": display_name.strip() if display_name else username,
        "password_hash": hash_password(password),
        "encryption_salt": encryption_salt,
        "encrypted_private_data": encrypted_private_data,
    }

    if data["current_user"] is None:
        data["current_user"] = username
    
    save_accounts_data(data)


def login_account(username: str, password: str) -> dict[str, Any]:
    username = normalise_username(username)
    data = load_account_data()

    if username not in data["users"]:
        raise ValueError("Username or password is incorrect.")
    
    user_record = data["users"][username]

    password_is_valid = verify_password(
        password_hash=user_record["password_hash"],
        password=password,
    )

    if not password_is_valid:
        raise ValueError("Username or password is incorrect.")
    
    try:
        decrypt_json = decrypt_text(
            encrypted_text=user_record["encrypted_private_data"],
            password=password,
            salt=user_record["encryption_salt"],
        )

    except InvalidToken:
        raise ValueError("Could not decrypt user data. The password may be incorrect.")
    
    private_data = json.loads(decrypt_json)

    data["current_user"] = username
    save_accounts_data(data)

    return private_data

def save_user_private_data(username: str, password: str, private_data: dict[str, Any]) -> None:
    username = normalise_username(username)
    data = load_account_data()

    if username not in data["users"]:
        raise ValueError("User does not exist")
    
    user_record = data["users"][username]

    if not verify_password(user_record["password_hash"], password):
        raise ValueError("Password is incorrect")
    
    private_data_json = json.dumps(private_data)

    encrypted_private_data = encrypt_text(
        text=private_data_json,
        password=password,
        salt=user_record["encryption_salt"],
    )

    user_record["encrypted_private_data"] = encrypted_private_data
    save_accounts_data(data)

def get_current_user() -> str | None:
    data = load_account_data()
    return data["current_user"]

def list_accounts() -> list[str]:
    data = load_account_data()
    return sorted(data["users"].keys())

def logout_account() -> None:
    data = load_account_data()
    data["current_user"] = None
    save_accounts_data(data)


    

