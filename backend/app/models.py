# backend/app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

def get_utc_now():
    return datetime.now(timezone.utc)
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"

class EquipmentStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"

class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    usage_sessions = relationship("UsageSession", back_populates="user")
    current_sessions = relationship("Equipment", back_populates="current_user")

class Equipment(Base):
    __tablename__ = "equipment"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    equipment_id = Column(String(50), unique=True, index=True, nullable=False)
    location = Column(String(100))
    description = Column(Text)
    current_status = Column(Enum(EquipmentStatus), default=EquipmentStatus.AVAILABLE)
    current_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    current_session_start = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    
    # Relationships
    current_user = relationship("User", back_populates="current_sessions")
    usage_sessions = relationship(
        "UsageSession", 
        back_populates="equipment",
        order_by="desc(UsageSession.start_time)",
        lazy="select"
    )

class UsageSession(Base):
    __tablename__ = "usage_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    planned_end_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text)
    remarks = Column(Text)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    scientist_signature = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
    
    # Relationships
    user = relationship("User", back_populates="usage_sessions")
    equipment = relationship("Equipment", back_populates="usage_sessions")

class DescriptionHistory(Base):
    __tablename__ = "description_history"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(500), unique=True, nullable=False)
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)