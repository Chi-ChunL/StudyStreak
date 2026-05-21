from typing import Any 

_current_username: str | None = None
_current_password: str | None = None
_current_private_data: dict[str, Any] | None = None

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

    _current_username = None
    _current_password = None
    _current_private_data = None

def is_logged_in() -> bool:
    #check if a user is logged in
    return(
        _current_username is not None
        and _current_password is not None
        and _current_private_data is not None
    )

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