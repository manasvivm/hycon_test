# backend/app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional
from .models import User, Equipment, UsageSession, DescriptionHistory, UserRole, EquipmentStatus, SessionStatus
from .schemas import UserCreate, EquipmentCreate, SessionStart, SessionEnd
from .auth import get_password_hash

# User CRUD
def create_user(db: Session, user: UserCreate):
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users"""
    return db.query(User).offset(skip).limit(limit).all()

# Equipment CRUD
def create_equipment(db: Session, equipment: EquipmentCreate):
    """Create new equipment"""
    db_equipment = Equipment(
        name=equipment.name,
        equipment_id=equipment.equipment_id,
        location=equipment.location,
        description=equipment.description
    )
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    return db_equipment

def get_equipment(db: Session, skip: int = 0, limit: int = 100):
    """Get all equipment with current user info"""
    return db.query(Equipment).offset(skip).limit(limit).all()

def get_equipment_by_id(db: Session, equipment_id: int):
    """Get equipment by ID"""
    return db.query(Equipment).filter(Equipment.id == equipment_id).first()

def update_equipment_status(db: Session, equipment_id: int, status: EquipmentStatus, user_id: Optional[int] = None):
    """Update equipment status"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if equipment:
        equipment.current_status = status
        equipment.current_user_id = user_id
        if status == EquipmentStatus.IN_USE and user_id:
            equipment.current_session_start = datetime.utcnow()
        else:
            equipment.current_session_start = None
        db.commit()
        db.refresh(equipment)
    return equipment

# Session CRUD
def check_time_conflict(db: Session, equipment_id: int, start_time: datetime, end_time: Optional[datetime] = None, exclude_session_id: Optional[int] = None):
    """Check for time conflicts with existing sessions"""
    query = db.query(UsageSession).filter(
        UsageSession.equipment_id == equipment_id,
        UsageSession.status == SessionStatus.COMPLETED
    )
    
    if exclude_session_id:
        query = query.filter(UsageSession.id != exclude_session_id)
    
    existing_sessions = query.all()
    
    for session in existing_sessions:
        # Check for overlap
        session_start = session.start_time
        session_end = session.end_time
        
        if end_time is None:  # Checking for active session start
            if session_start <= start_time <= session_end:
                return {
                    "conflict": True,
                    "message": f"Time conflicts with {session.user.name}'s session ({session_start.strftime('%H:%M')} - {session_end.strftime('%H:%M')})",
                    "conflicting_session": {
                        "user_name": session.user.name,
                        "start_time": session_start.isoformat(),
                        "end_time": session_end.isoformat()
                    }
                }
        else:  # Checking for completed session
            # Check if time ranges overlap
            if (start_time < session_end and end_time > session_start):
                return {
                    "conflict": True,
                    "message": f"Time conflicts with {session.user.name}'s session ({session_start.strftime('%H:%M')} - {session_end.strftime('%H:%M')})",
                    "conflicting_session": {
                        "user_name": session.user.name,
                        "start_time": session_start.isoformat(),
                        "end_time": session_end.isoformat()
                    }
                }
    
    # Check for active sessions
    active_session = db.query(UsageSession).filter(
        UsageSession.equipment_id == equipment_id,
        UsageSession.status == SessionStatus.ACTIVE
    ).first()
    
    if active_session and (exclude_session_id is None or active_session.id != exclude_session_id):
        return {
            "conflict": True,
            "message": f"Equipment currently in use by {active_session.user.name} since {active_session.start_time.strftime('%H:%M')}",
            "conflicting_session": {
                "user_name": active_session.user.name,
                "start_time": active_session.start_time.isoformat(),
                "end_time": None
            }
        }
    
    return {"conflict": False}

def start_session(db: Session, session_data: SessionStart, user_id: int):
    """Start a new equipment session"""
    # Check for conflicts
    start_time = session_data.start_time or datetime.utcnow()
    conflict = check_time_conflict(db, session_data.equipment_id, start_time)
    
    if conflict["conflict"]:
        return {"error": True, "message": conflict["message"]}
    
    # Create session
    db_session = UsageSession(
        equipment_id=session_data.equipment_id,
        user_id=user_id,
        start_time=start_time,
        description=session_data.description,
        remarks=session_data.remarks,
        status=SessionStatus.ACTIVE
    )
    
    db.add(db_session)
    
    # Update equipment status
    update_equipment_status(db, session_data.equipment_id, EquipmentStatus.IN_USE, user_id)
    
    # Update description history
    if session_data.description:
        update_description_history(db, session_data.description)
    
    db.commit()
    db.refresh(db_session)
    
    return {"error": False, "session": db_session}

def end_session(db: Session, session_id: int, session_data: SessionEnd, user_id: int):
    """End an active session"""
    session = db.query(UsageSession).filter(
        UsageSession.id == session_id,
        UsageSession.user_id == user_id,
        UsageSession.status == SessionStatus.ACTIVE
    ).first()
    
    if not session:
        return {"error": True, "message": "Active session not found"}
    
    end_time = session_data.end_time or datetime.utcnow()
    
    # Check if end time is after start time
    if end_time <= session.start_time:
        return {"error": True, "message": "End time must be after start time"}
    
    # Check for conflicts with completed sessions
    conflict = check_time_conflict(db, session.equipment_id, session.start_time, end_time, session.id)
    if conflict["conflict"]:
        return {"error": True, "message": conflict["message"]}
    
    # Update session
    session.end_time = end_time
    session.status = SessionStatus.COMPLETED
    session.scientist_signature = f"Digital signature by {session.user.name} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
    if session_data.remarks:
        session.remarks = session_data.remarks
    
    # Update equipment status
    update_equipment_status(db, session.equipment_id, EquipmentStatus.AVAILABLE)
    
    db.commit()
    db.refresh(session)
    
    return {"error": False, "session": session}

def get_user_sessions(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get sessions for a specific user"""
    return db.query(UsageSession).filter(UsageSession.user_id == user_id).offset(skip).limit(limit).all()

def get_active_session(db: Session, user_id: int):
    """Get active session for user"""
    return db.query(UsageSession).filter(
        UsageSession.user_id == user_id,
        UsageSession.status == SessionStatus.ACTIVE
    ).first()

def get_all_sessions(db: Session, skip: int = 0, limit: int = 100):
    """Get all sessions (admin only)"""
    return db.query(UsageSession).offset(skip).limit(limit).all()

# Description History CRUD
def update_description_history(db: Session, description: str):
    """Update description usage history for autocomplete"""
    existing = db.query(DescriptionHistory).filter(DescriptionHistory.description == description).first()
    
    if existing:
        existing.usage_count += 1
        existing.last_used = datetime.utcnow()
    else:
        new_description = DescriptionHistory(
            description=description,
            usage_count=1,
            last_used=datetime.utcnow()
        )
        db.add(new_description)
    
    db.commit()

def get_description_suggestions(db: Session, query: str = "", limit: int = 10):
    """Get description suggestions for autocomplete"""
    if query:
        descriptions = db.query(DescriptionHistory).filter(
            DescriptionHistory.description.contains(query)
        ).order_by(DescriptionHistory.usage_count.desc()).limit(limit).all()
    else:
        descriptions = db.query(DescriptionHistory).order_by(
            DescriptionHistory.usage_count.desc()
        ).limit(limit).all()
    
    return descriptions

# Analytics CRUD
def get_equipment_utilization(db: Session, days: int = 30):
    """Get equipment utilization statistics"""
    since_date = datetime.utcnow() - timedelta(days=days)
    
    equipment_stats = []
    equipment_list = db.query(Equipment).all()
    
    for equipment in equipment_list:
        sessions = db.query(UsageSession).filter(
            UsageSession.equipment_id == equipment.id,
            UsageSession.status == SessionStatus.COMPLETED,
            UsageSession.start_time >= since_date
        ).all()
        
        total_hours = sum([
            (session.end_time - session.start_time).total_seconds() / 3600
            for session in sessions if session.end_time
        ])
        
        # Calculate utilization percentage (assuming 12 hours/day available)
        available_hours = days * 12
        utilization_percentage = (total_hours / available_hours) * 100 if available_hours > 0 else 0
        
        equipment_stats.append({
            "equipment_id": equipment.equipment_id,
            "equipment_name": equipment.name,
            "total_hours": round(total_hours, 2),
            "utilization_percentage": round(utilization_percentage, 2)
        })
    
    return equipment_stats

def get_user_activity(db: Session, days: int = 30):
    """Get user activity statistics"""
    since_date = datetime.utcnow() - timedelta(days=days)
    
    user_stats = db.query(
        User.name,
        func.count(UsageSession.id).label('session_count'),
        func.sum(
            func.julianday(UsageSession.end_time) - func.julianday(UsageSession.start_time)
        ).label('total_days')
    ).join(UsageSession).filter(
        UsageSession.status == SessionStatus.COMPLETED,
        UsageSession.start_time >= since_date
    ).group_by(User.id).all()
    
    return [
        {
            "user_name": stat.name,
            "session_count": stat.session_count,
            "total_hours": round((stat.total_days or 0) * 24, 2)
        }
        for stat in user_stats
    ]