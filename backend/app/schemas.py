# backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
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

class Equipment(EquipmentBase):
    id: int
    current_status: EquipmentStatus
    current_user_id: Optional[int] = None
    current_session_start: Optional[datetime] = None
    created_at: datetime
    current_user: Optional[User] = None
    
    class Config:
        from_attributes = True

# Usage Session Schemas
class SessionBase(BaseModel):
    equipment_id: int
    start_time: datetime
    description: Optional[str] = None
    remarks: Optional[str] = None

class SessionStart(BaseModel):
    equipment_id: int
    start_time: Optional[datetime] = None
    description: Optional[str] = None
    remarks: Optional[str] = None

class SessionEnd(BaseModel):
    end_time: Optional[datetime] = None
    remarks: Optional[str] = None

class SessionCreate(SessionBase):
    end_time: Optional[datetime] = None

class UsageSession(SessionBase):
    id: int
    user_id: int
    end_time: Optional[datetime] = None
    status: SessionStatus
    scientist_signature: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: User
    equipment: Equipment
    
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