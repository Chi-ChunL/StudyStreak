import base64
import os
from hashlib import pbkdf2_hmac

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_salt() -> str:
    return base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8")


def derive_encryption_key(password: str, salt: str) -> bytes:
    padded_salt = salt + "=" * (-len(salt) % 4)

    salt_bytes = base64.urlsafe_b64decode(padded_salt.encode("utf-8"))

    key = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        390000,
        dklen=32,
    )

    return base64.urlsafe_b64encode(key)


def encrypt_text(text: str, password: str, salt: str) -> str:
    key = derive_encryption_key(password, salt)
    fernet = Fernet(key)

    encrypted_text = fernet.encrypt(text.encode("utf-8"))
    return encrypted_text.decode("utf-8")


def decrypt_text(encrypted_text: str, password: str, salt: str) -> str:
    key = derive_encryption_key(password, salt)
    fernet = Fernet(key)

    decrypted_text = fernet.decrypt(encrypted_text.encode("utf-8"))
    return decrypted_text.decode("utf-8")

