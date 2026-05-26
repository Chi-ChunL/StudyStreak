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

class LeaderboardEntry(BaseModel):
    #leaderboard row
    display_name: str
    total_minutes: int

class ProfileDataUpdate(BaseModel):
    #encrypted profile upload
    encrypted_profile_data: str = Field(min_length=1)

class ProfileDataResponse(BaseModel):
    #encrypted profile download
    encrypted_profile_data: str | None = None

