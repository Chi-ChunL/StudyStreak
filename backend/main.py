from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.auth import create_access_token, hash_password, verify_password, get_current_user
from backend.database import Base, engine, get_db
from backend.models import FocusSession, User, FocusQualitySession
from backend.schemas import(
    FocusSessionCreate,
    LeaderboardEntry,
    ProfileDataResponse,
    ProfileDataUpdate,
    TokenResponse,
    UserCreate,
    UserLogin,
    SubjectList,
    SubjectWebsiteList,
    TimetableList,
    FocusQualitySessionCreate,
    FocusQualitySessionResponse,
    StreakUpdate,
)

Base.metadata.create_all(bind=engine)

with engine.connect() as connection:
    columns = connection.execute(text("PRAGMA table_info(users)")).fetchall()
    column_name = [column[1] for column in columns]

    if "encrypted_profile_data" not in column_name:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN encrypted_profile_data TEXT")
        )
        connection.commit()

    if "subjects_json" not in column_name:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN subjects_json TEXT")
        )
        connection.commit()

    if "subject_websites_json" not in column_name:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN subject_websites_json TEXT")
        )
        connection.commit()

    if "timetable_json" not in column_name:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN timetable_json TEXT")
        )
        connection.commit()
    
    if "current_streak" not in column_name:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN current_streak INTEGER DEFAULT 0 NOT NULL")
        )
        connection.commit()

load_dotenv()

IS_PRODUCTION = os.getenv("STUDYSTREAK_ENV") == "production"

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="StudyStreak Backend",
              docs_url=None if IS_PRODUCTION else "/docs",
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
            User.current_streak,
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
            current_streak=result.current_streak or 0,
        )
        for result in results
    ]

def clean_subjects(subjects: list[str]) -> list[str]:
    cleaned_subjects = []

    for subject in subjects:
        clean_subject = subject.strip().lower()

        if clean_subject and clean_subject not in cleaned_subjects:
            cleaned_subjects.append(clean_subject)

    return cleaned_subjects[:50]

def clean_subject_websites(subject_websites: dict[str, list[str]]) -> dict[str, list[str]]:
    cleaned = {}

    if not isinstance(subject_websites, dict):
        return cleaned

    for subject, websites in subject_websites.items():
        clean_subject = str(subject).strip().lower()

        if not clean_subject or len(clean_subject) > 50:
            continue

        if not isinstance(websites, list):
            websites = [websites]

        clean_websites = []

        for website in websites:
            clean_website = str(website).strip().lower()

            if clean_website and clean_website not in clean_websites:
                clean_websites.append(clean_website)

        cleaned[clean_subject] = clean_websites[:10]

    return cleaned

@app.get("/subjects", response_model=SubjectList)
def get_subjects(current_user: User = Depends(get_current_user)):
    if not current_user.subjects_json:
        return SubjectList(subjects=[])

    try:
        subjects = json.loads(current_user.subjects_json)
    except json.JSONDecodeError:
        subjects = []

    if not isinstance(subjects, list):
        subjects = []

    return SubjectList(subjects=clean_subjects(subjects))


@app.put("/subjects")
def update_subjects(
    subject_data: SubjectList,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.subjects_json = json.dumps(clean_subjects(subject_data.subjects))
    db.commit()

    return {"message": "Subjects saved."}

@app.get("/subject-websites", response_model=SubjectWebsiteList)
def get_subject_websites(current_user: User = Depends(get_current_user)):
    if not current_user.subject_websites_json:
        return SubjectWebsiteList(subject_websites={})

    try:
        subject_websites = json.loads(current_user.subject_websites_json)
    except json.JSONDecodeError:
        subject_websites = {}

    if not isinstance(subject_websites, dict):
        subject_websites = {}

    return SubjectWebsiteList(
        subject_websites=clean_subject_websites(subject_websites)
    )


@app.put("/subject-websites")
def update_subject_websites(
    subject_website_data: SubjectWebsiteList,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.subject_websites_json = json.dumps(
        clean_subject_websites(subject_website_data.subject_websites)
    )
    db.commit()

    return {"message": "Subject websites saved."}

@app.get("/timetable", response_model=TimetableList)
def get_timetable(current_user: User = Depends(get_current_user)):
    if not current_user.timetable_json:
        return TimetableList(timetable=[])

    try:
        timetable = json.loads(current_user.timetable_json)
    except json.JSONDecodeError:
        timetable = []

    if not isinstance(timetable, list):
        timetable = []

    return TimetableList(timetable=timetable)


@app.put("/timetable")
def update_timetable(
    timetable_data: TimetableList,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.timetable_json = json.dumps([
        item.model_dump()
        for item in timetable_data.timetable
    ])
    db.commit()

    return {"message": "Timetable saved."}

@app.post("/focus-quality-sessions")
def create_focus_quality_session(
    request: Request,
    session_data: FocusQualitySessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if session_data.source != "chrome_extension":
        raise HTTPException(status_code=400, detail="Focus quality must come from Chrome extension.")
    
    existing_session = (
        db.query(FocusQualitySession)
        .filter(
            FocusQualitySession.user_id == current_user.id,
            FocusQualitySession.completed_at == session_data.completed_at,
        )
        .first()
    )

    if existing_session is None:
        existing_session = FocusQualitySession(user_id=current_user.id)
        db.add(existing_session)
    
    existing_session.subject = session_data.subject.strip().lower()
    existing_session.score = session_data.score
    existing_session.focused_seconds = session_data.focused_seconds
    existing_session.distracted_seconds = session_data.distracted_seconds
    existing_session.idle_seconds = session_data.idle_seconds
    existing_session.top_distracted_domain = session_data.top_distracted_domain or "none"
    existing_session.completed_at = session_data.completed_at

    db.commit() 

    return {"message": "Focus quality session saved."}

@app.get("/focus-quality-sessions", response_model=list[FocusQualitySessionResponse])
def get_focus_quality_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(FocusQualitySession)
        .filter(FocusQualitySession.user_id == current_user.id)
        .order_by(FocusQualitySession.completed_at.desc())
        .limit(20)
        .all()
    )

    return sessions

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

@app.put("/streak")
def update_streak(
    streak_data: StreakUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.current_streak = streak_data.current_streak
    db.commit()

    return {"message": "Streak saved."}
