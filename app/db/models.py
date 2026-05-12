from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(String(32), primary_key=True, index=True)
    user = Column(String(128), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    audio_file = Column(String(255))
    audio_bytes = Column(Integer)
    transcript_file = Column(String(255))
    report_file = Column(String(255))

class UserPrompt(Base):
    __tablename__ = "user_prompts"

    user = Column(String(128), primary_key=True, index=True)
    report_prompt = Column(String)
    email_prompt = Column(String)
