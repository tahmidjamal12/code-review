from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class ProcessRun(Base):
    __tablename__ = 'process_run'
    
    id = Column(Integer, primary_key=True)
    image_path = Column(String(255), nullable=False)
    transcription = Column(Text, nullable=True)
    bottlenecks = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True)
    status = Column(String(50), default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)