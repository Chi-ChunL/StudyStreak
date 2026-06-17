from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    #user signup data
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None

class UserLogin(BaseModel):
    #user login data
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=8, max_length=128)

class TokenResponse(BaseModel):
    #login response
    access_token: str
    token_type: str = "bearer"

class FocusSessionCreate(BaseModel):
    #focus session upload data
    subject: str = Field(min_length=1, max_length=50)
    minutes: int = Field(gt=0, le=180)
    website: str | None = None
    completed: bool = True
    source: str = "focus_cli"

class FocusQualitySessionCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=50)
    score: int = Field(ge=0, le=100)
    focused_seconds: int = Field(ge=0)
    distracted_seconds: int = Field(ge=0)
    idle_seconds: int = Field(ge=0)
    top_distracted_domain: str | None = "none"
    completed_at: str
    source: str = "chrome_extension"

class FocusQualitySessionResponse(BaseModel):
    subject: str
    score: int
    focused_seconds: int
    distracted_seconds: int
    idle_seconds: int
    top_distracted_domain: str | None = "none"
    completed_at: str

class LeaderboardEntry(BaseModel):
    #leaderboard row
    display_name: str
    total_minutes: int
    current_streak: int = 0

class ProfileDataUpdate(BaseModel):
    #encrypted profile upload
    encrypted_profile_data: str = Field(min_length=1)

class ProfileDataResponse(BaseModel):
    #encrypted profile download
    encrypted_profile_data: str | None = None

class SubjectList(BaseModel):
    subjects: list[str] = Field(default_factory=list)

class SubjectWebsiteList(BaseModel):
    subject_websites: dict[str, list[str]] = Field(default_factory=dict)

class TodoItem(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=120)
    done: bool = False

class TodoItemList(BaseModel):
    todo_items: list[TodoItem] = Field(default_factory=list, max_length=50)

class StreakUpdate(BaseModel):
    current_streak: int = Field(ge=0, le=3650)

class TimetableSession(BaseModel):
    subject: str = Field(min_length=1, max_length=50)
    day: str = Field(pattern="^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
    start_time: str = Field(pattern="^([01][0-9]|2[0-3]):[0-5][0-9]$")
    minutes: int = Field(gt=0, le=720)

class TimetableList(BaseModel):
    timetable: list[TimetableSession] = Field(default_factory=list, max_length=100)
