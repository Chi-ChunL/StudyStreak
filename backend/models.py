from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    #user table
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    encrypted_profile_data = Column(String, nullable=True)
    subjects_json = Column(String, nullable=True)
    subject_websites_json = Column(String, nullable=True)
    timetable_json = Column(String, nullable=True)
    todo_items_json = Column(String, nullable=True)
    current_streak = Column(Integer, default=0, nullable=False)

    focus_sessions = relationship(
        "FocusSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    focus_quality_sessions = relationship(
        "FocusQualitySession",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class FocusSession(Base):
    #verified focus session table
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    subject = Column(String, nullable=False)
    minutes = Column(Integer, nullable=False)
    website = Column(String, nullable=True)

    completed = Column(Boolean, default=True)
    source = Column(String, default="focus_cli")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="focus_sessions")

class FocusQualitySession(Base):
    __tablename__ = "focus_quality_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    subject = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    focused_seconds = Column(Integer, nullable=False)
    distracted_seconds = Column(Integer, nullable=False)
    idle_seconds = Column(Integer, nullable=False)
    top_distracted_domain = Column(String, nullable=True)
    completed_at = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="focus_quality_sessions")
