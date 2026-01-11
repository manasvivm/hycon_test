# backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from typing import Optional, List
from .models import UserRole, EquipmentStatus, SessionStatus

# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.EMPLOYEE

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Equipment Schemas
class EquipmentBase(BaseModel):
    name: str
    equipment_id: str
    location: Optional[str] = None
    description: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    pass

# Simple session schema without equipment to avoid circular reference
class SimpleUsageSession(BaseModel):
    id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    remarks: Optional[str] = None
    status: SessionStatus
    scientist_signature: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: User
    
    class Config:
        from_attributes = True

class Equipment(EquipmentBase):
    id: int
    current_status: EquipmentStatus
    current_user_id: Optional[int] = None
    current_session_start: Optional[datetime] = None
    created_at: datetime
    current_user: Optional[User] = None
    usage_sessions: Optional[List[SimpleUsageSession]] = []
    
    class Config:
        from_attributes = True

# Usage Session Schemas
class SessionBase(BaseModel):
    equipment_id: int
    start_time: datetime
    planned_end_time: Optional[datetime] = None
    description: Optional[str] = None
    remarks: Optional[str] = None

class SessionStart(BaseModel):
    equipment_id: int
    start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    description: Optional[str] = None
    remarks: Optional[str] = None

class PastUsageLog(BaseModel):
    equipment_id: int
    start_time: datetime
    end_time: datetime
    description: str
    remarks: Optional[str] = None

class SessionEnd(BaseModel):
    end_time: datetime
    remarks: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @classmethod
    def parse_obj(cls, obj):
        if isinstance(obj, dict) and "end_time" in obj:
            if isinstance(obj["end_time"], str):
                try:
                    # Parse the ISO format string and ensure it's UTC
                    dt = datetime.fromisoformat(obj["end_time"].replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    obj["end_time"] = dt
                except ValueError:
                    obj["end_time"] = datetime.now(timezone.utc)
        return super().parse_obj(obj)

    def __init__(self, **data):
        super().__init__(**data)
        if self.end_time:
            if self.end_time.tzinfo is None:
                self.end_time = self.end_time.replace(tzinfo=timezone.utc)
            else:
                self.end_time = self.end_time.astimezone(timezone.utc)

class SessionCreate(SessionBase):
    end_time: Optional[datetime] = None

class UsageSession(SessionBase):
    id: int
    user_id: int
    end_time: Optional[datetime] = None
    status: SessionStatus
    is_past_usage_log: Optional[bool] = False
    scientist_signature: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: User
    equipment: 'Equipment'
    
    class Config:
        from_attributes = True

# Response Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class ConflictCheck(BaseModel):
    conflict: bool
    message: Optional[str] = None
    conflicting_session: Optional[dict] = None

# Analytics Schemas
class EquipmentUtilization(BaseModel):
    equipment_id: str
    equipment_name: str
    total_hours: float
    utilization_percentage: float

class UserActivity(BaseModel):
    user_name: str
    session_count: int
    total_hours: float

class AnalyticsDashboard(BaseModel):
    equipment_utilization: List[EquipmentUtilization]
    user_activity: List[UserActivity]
    total_sessions: int
    active_sessions: int

# Description History
class DescriptionSuggestion(BaseModel):
    description: str
    usage_count: int

# Sample Submission Schemas
class SampleSubmissionCreate(BaseModel):
    project: str
    sample_name: str
    batch_no: str
    label_claim: str
    sample_quantity: str
    packaging_configuration: str
    recommended_storage: str
    condition: str
    tests_to_be_performed: str
    remarks: Optional[str] = None
    submitted_to: str
    submitted_by: str
    recipient_emails: List[str]  # Changed to support multiple recipients

class SampleSubmission(BaseModel):
    id: int
    reference_number: str
    project: str
    sample_name: str
    batch_no: str
    label_claim: str
    sample_quantity: str
    packaging_configuration: str
    recommended_storage: str
    condition: str
    tests_to_be_performed: str
    remarks: Optional[str] = None
    submitted_to: str
    submitted_by: str
    submitted_by_user_id: Optional[int] = None
    recipient_email: str  # Single email (from database)
    recipient_user_id: Optional[int] = None
    status: str  # pending, received, in_review, completed, rejected, archived
    is_read: bool
    read_at: Optional[datetime] = None
    read_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    submitted_by_user: Optional[User] = None  # Include sender info
    recipient_user: Optional[User] = None     # Include recipient info
    
    class Config:
        from_attributes = True

class SampleSubmissionList(BaseModel):
    """Summary view for list displays"""
    id: int
    reference_number: str
    project: str
    sample_name: str
    submitted_by: str
    submitted_to: str
    status: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Email Recipient Schemas
class EmailRecipientCreate(BaseModel):
    name: str
    email: EmailStr
    department: Optional[str] = None
    is_active: bool = True

class EmailRecipientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

class EmailRecipient(EmailRecipientCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Message Thread Schemas
class MessageThreadCreate(BaseModel):
    message: str

class MessageThread(BaseModel):
    id: int
    submission_id: int
    sender_id: Optional[int] = None
    message: str
    is_system_message: bool
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Status History Schemas
class SubmissionStatusHistory(BaseModel):
    id: int
    submission_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    changed_at: datetime
    
    class Config:
        from_attributes = True

# Notification Schemas
class Notification(BaseModel):
    id: int
    user_id: int
    submission_id: Optional[int] = None
    notification_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class NotificationSummary(BaseModel):
    """Summary for notification badges"""
    unread_count: int
    total_count: int