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

    focus_sessions = relationship(
        "FocusSession",
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