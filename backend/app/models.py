# backend/app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Float, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import secrets

def get_utc_now():
    return datetime.now(timezone.utc)

def generate_reference_number():
    """Generate unique reference number for submissions (e.g., SS-2026-0001)"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(3).upper()
    return f"SS-{timestamp}-{random_part}"

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"

class EquipmentStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"

class SubmissionStatus(str, enum.Enum):
    """Status workflow for sample submissions"""
    PENDING = "pending"           # Initial state
    RECEIVED = "received"         # Acknowledged by recipient
    IN_REVIEW = "in_review"       # Under review
    COMPLETED = "completed"       # Processing completed
    REJECTED = "rejected"         # Rejected with reason
    ARCHIVED = "archived"         # Archived for records

class NotificationType(str, enum.Enum):
    """Types of notifications"""
    NEW_SUBMISSION = "new_submission"
    STATUS_CHANGE = "status_change"
    NEW_REPLY = "new_reply"
    SUBMISSION_ASSIGNED = "submission_assigned"
    REMINDER = "reminder"

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
    """Enterprise-grade sample submission with full audit trail"""
    __tablename__ = "sample_submissions"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String(50), unique=True, nullable=False, index=True, default=generate_reference_number)
    
    # Sample details
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
    
    # Sender/Receiver information
    submitted_to = Column(String(200), nullable=False)  # Name & Dept
    submitted_by = Column(String(200), nullable=False)  # Name & Dept
    submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_email = Column(String(100), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Status and tracking
    status = Column(Enum(SubmissionStatus, native_enum=True, values_callable=lambda obj: [e.value for e in obj]), default='pending', nullable=False, index=True)
    
    # Read tracking
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    read_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps (immutable for audit)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)
    
    # Relationships
    submitted_by_user = relationship("User", foreign_keys=[submitted_by_user_id])
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    read_by_user = relationship("User", foreign_keys=[read_by_user_id])
    message_threads = relationship("MessageThread", back_populates="submission", cascade="all, delete-orphan")
    status_history = relationship("SubmissionStatusHistory", back_populates="submission", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="submission", cascade="all, delete-orphan")
    
    # Composite indexes for enterprise queries
    __table_args__ = (
        Index('idx_submission_project_date', 'project', 'created_at'),
        Index('idx_submission_status', 'status', 'created_at'),
        Index('idx_submission_recipient_unread', 'recipient_user_id', 'is_read', 'created_at'),
        Index('idx_submission_sender_status', 'submitted_by_user_id', 'status', 'created_at'),
        Index('idx_submission_reference', 'reference_number'),
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


class MessageThread(Base):
    """In-app messaging system for submission communication"""
    __tablename__ = "message_threads"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("sample_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    is_system_message = Column(Boolean, default=False)  # For automated status updates
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    
    # Relationships
    submission = relationship("SampleSubmission", back_populates="message_threads")
    sender = relationship("User")
    
    # Index for efficient thread retrieval
    __table_args__ = (
        Index('idx_message_submission_date', 'submission_id', 'created_at'),
        Index('idx_message_sender_date', 'sender_id', 'created_at'),
    )


class SubmissionStatusHistory(Base):
    """Immutable audit trail for status changes"""
    __tablename__ = "submission_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("sample_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(Enum(SubmissionStatus, native_enum=True, values_callable=lambda obj: [e.value for e in obj]), nullable=True)  # NULL for initial status
    new_status = Column(Enum(SubmissionStatus, native_enum=True, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    
    # Relationships
    submission = relationship("SampleSubmission", back_populates="status_history")
    changed_by = relationship("User")
    
    # Index for audit queries
    __table_args__ = (
        Index('idx_status_history_submission', 'submission_id', 'changed_at'),
        Index('idx_status_history_user', 'changed_by_user_id', 'changed_at'),
    )


class Notification(Base):
    """User notification system"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("sample_submissions.id", ondelete="CASCADE"), nullable=True, index=True)
    notification_type = Column(Enum(NotificationType, native_enum=True, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    submission = relationship("SampleSubmission", back_populates="notifications")
    
    # Indexes for notification queries
    __table_args__ = (
        Index('idx_notification_user_unread', 'user_id', 'is_read', 'created_at'),
        Index('idx_notification_type_date', 'notification_type', 'created_at'),
    )