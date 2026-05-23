from typing import Any 

from studystreak.accounts import save_user_private_data

_current_username: str | None = None
_current_password: str | None = None
_current_private_data: dict[str, Any] | None = None
_server_token: str | None = None

def set_session(username: str, password: str, private_data: dict[str, Any]) -> None:
    #store active login for this run
    global _current_username
    global _current_password
    global _current_private_data

    _current_username = username
    _current_password = password
    _current_private_data = private_data

def clear_session() -> None:
    #clear active login
    global _current_username
    global _current_password
    global _current_private_data
    global _server_token

    _current_username = None
    _current_password = None
    _current_private_data = None
    _server_token = None

def is_logged_in() -> bool:
    #check if a user is logged in
    return(
        _current_username is not None
        and _current_password is not None
        and _current_private_data is not None
    )

def get_session_username() -> str:
    #get active username for this run
    if _current_username is None:
        raise RuntimeError("No user is currently logged in")

    return _current_username

def get_session_password() -> str:
    #get active password for this run
    if _current_password is None:
        raise RuntimeError("No user is currently logged in")
    
    return _current_password

def get_session_data() -> dict[str, Any]:
    #get active user data
    if _current_private_data is None:
        raise RuntimeError("No user is currently logged in")
    
    return _current_private_data

def update_session_data(private_data: dict[str, Any]) -> None:
    #update active user data
    global _current_private_data

    if _current_private_data is None:
        raise RuntimeError("No user is currently logged in")
    
    _current_private_data = private_data


def save_session_data(private_data: dict[str, Any]) -> None:
    #save active user data back encrypted

    global _current_private_data

    if not is_logged_in():
        raise RuntimeError("No user is currently logged in")
    
    username = get_session_username()
    password = get_session_password()

    save_user_private_data(username, password, private_data)
    _current_private_data = private_data

def set_server_token(token: str) -> None:
    #store server login token
    global _server_token

    _server_token = token

def get_server_token() -> str | None:
    #get server login token
    return _server_token
