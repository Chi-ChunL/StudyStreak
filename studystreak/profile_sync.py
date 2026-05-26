import base64
import json
from hashlib import pbkdf2_hmac

from cryptography.fernet import Fernet

def derive_profile_key(username: str, password: str) -> bytes:
    #derive cloud profile encryption key
    salt = f"studystreak-profile:{username.lower()}".encode("utf-8")

    key = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        390000,
        dklen=32,
    )

    return base64.urlsafe_b64encode(key)

def encrypt_profile_data(data: dict, username: str, password: str) -> str:
    #encrypt profile data for server sync
    key = derive_profile_key(username, password)
    fernet = Fernet(key)

    text = json.dumps(data)
    encrypted_data = fernet.encrypt(text.encode("utf-8"))

    return encrypted_data.decode("utf-8")


def decrypt_profile_data(encrypted_data: str, username: str, password: str) -> dict:
    #decrypt profile data from server sync
    key = derive_profile_key(username, password)
    fernet = Fernet(key)

    decrypted_data = fernet.decrypt(encrypted_data.encode("utf-8"))
    return json.loads(decrypted_data.decode("utf-8"))