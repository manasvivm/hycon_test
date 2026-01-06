# backend/app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Float, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

def get_utc_now():
    return datetime.now(timezone.utc)

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
    name = Column(String(100), nullable=False, index=True)  # Index for search
    equipment_id = Column(String(50), unique=True, index=True, nullable=False)
    location = Column(String(100), index=True)  # Index for location-based queries
    description = Column(Text)
    current_status = Column(Enum(EquipmentStatus), default=EquipmentStatus.AVAILABLE, index=True)  # Index for status filtering
    current_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    current_session_start = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    
    # Relationships
    current_user = relationship("User", back_populates="current_sessions")
    usage_sessions = relationship(
        "UsageSession", 
        back_populates="equipment",
        order_by="desc(UsageSession.start_time)",
        lazy="select"
    )
    
    # Composite index for common queries
    __table_args__ = (
        Index('idx_equipment_status_name', 'current_status', 'name'),
        Index('idx_equipment_location_status', 'location', 'current_status'),
    )

class UsageSession(Base):
    __tablename__ = "usage_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)  # Index for time-based queries
    planned_end_time = Column(DateTime(timezone=True), nullable=True, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True, index=True)
    description = Column(Text)
    remarks = Column(Text)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, index=True)  # Index for status queries
    is_past_usage_log = Column(Boolean, default=False, index=True)  # Track if session was logged retroactively
    scientist_signature = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
    
    # Relationships
    user = relationship("User", back_populates="usage_sessions")
    equipment = relationship("Equipment", back_populates="usage_sessions")
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_session_equipment_status', 'equipment_id', 'status'),
        Index('idx_session_user_status', 'user_id', 'status'),
        Index('idx_session_status_start', 'status', 'start_time'),
        Index('idx_session_equipment_time', 'equipment_id', 'start_time', 'end_time'),
        # Constraint to ensure end_time is after start_time
        CheckConstraint('end_time IS NULL OR end_time > start_time', name='check_end_after_start'),
    )

class DescriptionHistory(Base):
    __tablename__ = "description_history"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(500), unique=True, nullable=False)
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class SampleSubmission(Base):
    __tablename__ = "sample_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    project = Column(String(100), nullable=False, index=True)
    sample_name = Column(String(200), nullable=False)
    batch_no = Column(String(100), nullable=False)
    label_claim = Column(String(200), nullable=False)
    sample_quantity = Column(String(100), nullable=False)
    packaging_configuration = Column(String(200), nullable=False)
    recommended_storage = Column(String(100), nullable=False)
    condition = Column(String(100), nullable=False)
    tests_to_be_performed = Column(Text, nullable=False)
    remarks = Column(Text, nullable=True)
    submitted_to = Column(String(200), nullable=False)  # Name & Dept
    submitted_by = Column(String(200), nullable=False)  # Name & Dept
    submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_email = Column(String(100), nullable=False)  # Email sent to
    created_at = Column(DateTime(timezone=True), default=get_utc_now, index=True)
    
    # Relationships
    user = relationship("User")
    
    # Index for searching submissions
    __table_args__ = (
        Index('idx_submission_project_date', 'project', 'created_at'),
    )

class EmailRecipient(Base):
    __tablename__ = "email_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Display name like "Shruti & ARD"
    email = Column(String(100), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)