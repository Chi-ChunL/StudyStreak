from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.auth import create_access_token, hash_password, verify_password, get_current_user
from backend.database import Base, engine, get_db
from backend.models import FocusSession, User
from backend.schemas import(
    FocusSessionCreate,
    LeaderboardEntry,
    ProfileDataResponse,
    ProfileDataUpdate,
    TokenResponse,
    UserCreate,
    UserLogin,
)

Base.metadata.create_all(bind=engine)

load_dotenv()

IS_PRODUCTION = os.getenv("STUDYSTREAK_ENV") == "production"

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="StudyStreak Backend",
              focs_url=None if IS_PRODUCTION else "/docs",
              redoc_url=None if IS_PRODUCTION else "/redoc",
              )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
def root():
    #server health check
    return {"message": "StudyStreak backend is running"}


@app.post("/signup")
@limiter.limit("5/minute")
def signup(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    #create server account
    username = user_data.username.strip().lower()

    existing_user = db.query(User).filter(User.username == username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exist")
    
    display_name = user_data.display_name or username

    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(user_data.password),
    )

    db.add(user)
    db.commit()

    return {"message": "Account created."}

@app.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    #login server account
    username = login_data.username.strip().lower()

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=401, detail="Username or password is incorrect")
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username or password is incorrect")
    
    token = create_access_token({"sub": user.username})

    return TokenResponse(access_token=token)

@app.post("/token", response_model=TokenResponse)
@limiter.limit("10/minute")
def token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    #login through Swagger authorise button
    username = form_data.username.strip().lower()

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=401, detail="Username or password is incorrect.")

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username or password is incorrect.")

    token = create_access_token({"sub": user.username})

    return TokenResponse(access_token=token)

@app.post("/focus-sessions")
@limiter.limit("20/minute")
def create_focus_session(
    request: Request,
    session_data: FocusSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not session_data.completed:
        raise HTTPException(status_code=400, detail="Only completed focus sessions count.")

    focus_session = FocusSession(
        user_id=current_user.id,
        subject=session_data.subject.strip().lower(),
        minutes=session_data.minutes,
        website=session_data.website,
        completed=session_data.completed,
        source=session_data.source,
    )

    db.add(focus_session)
    db.commit()

    return {"message": "Focus session saved."}


@app.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(period: str = "all" , db: Session = Depends(get_db)):
    #get leaderboard by focus minutes
    query = (
        db.query(
            User.display_name,
            func.sum(FocusSession.minutes).label("total_minutes"),
        )
        .join(FocusSession)
        .filter(FocusSession.completed.is_(True))
    )

    now = datetime.utcnow()

    if period == "today":
        start_time = datetime(now.year, now.month, now.day)
        query = query.filter(FocusSession.created_at >= start_time)
    
    elif period == "week":
        start_time = now - timedelta(days=now.weekday())
        start_time = datetime(start_time.year, start_time.month, start_time.day)
        query = query.filter(FocusSession.created_at >= start_time)
    
    elif period == "all":
        pass

    else:
        raise HTTPException(status_code=400, detail="Invalid Leaderboard period.")
    

    results = (
        query
        .group_by(User.id)
        .order_by(func.sum(FocusSession.minutes).desc())
        .limit(10)
        .all()
    )

    return [
        LeaderboardEntry(
            display_name=result.display_name,
            total_minutes=result.total_minutes,
        )
        for result in results
    ]

@app.get("/profile-data", response_model=ProfileDataResponse)
def get_profile_data(
    current_user: User = Depends(get_current_user),
):
    #get encrypted profile data
    return ProfileDataResponse(
        encrypted_profile_data=current_user.encrypted_profile_data
    )

@app.put("/profile-data")
def update_profile_data(
    profile_data: ProfileDataUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    #save encrypted profile data
    current_user.encrypted_profile_data = profile_data.encrypted_profile_data
    db.commit()

    return {"message": "Profile data saved"}

