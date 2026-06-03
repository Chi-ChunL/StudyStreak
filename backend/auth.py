import os
from datetime import datetime, timedelta

from jose import jwt, JWTError

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from dotenv import load_dotenv

load_dotenv()

password_hasher = PasswordHasher()

SECRET_KEY = os.getenv("STUDYSTREAK_SECRET_KEY", "dev-secret-change")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str) -> str:
    #hash password
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    #verify password
    try: 
        return password_hasher.verify(password_hash, password)

    except VerifyMismatchError:
        return False

def create_access_token(data: dict) -> str:
    #create login token
    to_encode  = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    #get user from login token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token.")
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user