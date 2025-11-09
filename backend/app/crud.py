# backend/app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta, timezone
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
    """Get all equipment with current user info and usage sessions"""
    from sqlalchemy.orm import joinedload
    return db.query(Equipment).options(
        joinedload(Equipment.usage_sessions).joinedload(UsageSession.user)
    ).offset(skip).limit(limit).all()

def get_equipment_by_id(db: Session, equipment_id: int):
    """Get equipment by ID with usage sessions"""
    from sqlalchemy.orm import joinedload
    return db.query(Equipment).options(
        joinedload(Equipment.usage_sessions).joinedload(UsageSession.user)
    ).filter(Equipment.id == equipment_id).first()

def update_equipment(db: Session, equipment_id: int, equipment: EquipmentCreate):
    """Update equipment details"""
    db_equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if db_equipment:
        db_equipment.name = equipment.name
        db_equipment.equipment_id = equipment.equipment_id
        db_equipment.location = equipment.location
        db_equipment.description = equipment.description
        db.commit()
        db.refresh(db_equipment)
    return db_equipment

def delete_equipment(db: Session, equipment_id: int):
    """Delete equipment"""
    db_equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if db_equipment:
        db.delete(db_equipment)
        db.commit()
        return True
    return False

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
        session_start = ensure_timezone_aware(session.start_time)
        session_end = ensure_timezone_aware(session.end_time)
        start_time = ensure_timezone_aware(start_time)
        end_time = ensure_timezone_aware(end_time)
        
        if end_time is None:  # Checking for active session start
            # For active sessions, check if there's a conflict with another active session
            if session.end_time is None:
                # Both sessions are active - this is not a conflict since we allow multiple active sessions
                continue
            else:
                # Check if we're starting during a scheduled future session
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

def ensure_timezone_aware(dt):
    """Ensure a datetime is timezone-aware, converting to UTC if it isn't"""
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            # Assume the naive datetime is in UTC
            return dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC if it's in a different timezone
            return dt.astimezone(timezone.utc)
    except Exception as e:
        # If anything goes wrong, return current UTC time
        print(f"Error handling datetime: {e}")
        return datetime.now(timezone.utc)

def start_session(db: Session, session_data: SessionStart, user_id: int):
    """Start a new active equipment usage session"""
    # Check for conflicts
    start_time = session_data.start_time or datetime.now(timezone.utc)
    start_time = ensure_timezone_aware(start_time)
    
    # Check if this user already has an active session with this equipment
    existing_session = db.query(UsageSession).filter(
        UsageSession.equipment_id == session_data.equipment_id,
        UsageSession.user_id == user_id,
        UsageSession.status == SessionStatus.ACTIVE
    ).first()
    
    if existing_session:
        return {"error": True, "message": "You already have an active session with this equipment"}
    
    # Check for other conflicts (scheduled future sessions)
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
    
    # Handle end time
    end_time = session_data.end_time if session_data and hasattr(session_data, 'end_time') and session_data.end_time else datetime.now(timezone.utc)
    end_time = ensure_timezone_aware(end_time)
    
    # Ensure start_time is timezone-aware
    session.start_time = ensure_timezone_aware(session.start_time)
    
    # Convert both times to UTC for comparison
    start_time_utc = session.start_time.astimezone(timezone.utc)
    end_time_utc = end_time.astimezone(timezone.utc)
    
    # Check if end time is after start time
    if end_time_utc <= start_time_utc:
        return {"error": True, "message": f"End time ({end_time_utc.isoformat()}) must be after start time ({start_time_utc.isoformat()})"}
    
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

def log_past_usage(db: Session, equipment_id: int, user_id: int, start_time: datetime, end_time: datetime, description: str, remarks: Optional[str] = None):
    """Log a completed past usage session"""
    # Ensure times are timezone-aware
    start_time = ensure_timezone_aware(start_time)
    end_time = ensure_timezone_aware(end_time)
    
    # Validate that end time is after start time
    if end_time <= start_time:
        return {"error": True, "message": "End time must be after start time"}
    
    # Check for conflicts with existing sessions
    conflict = check_time_conflict(db, equipment_id, start_time, end_time)
    if conflict["conflict"]:
        return {"error": True, "message": conflict["message"]}
    
    # Create a COMPLETED session for past usage
    db_session = UsageSession(
        equipment_id=equipment_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        description=description,
        remarks=remarks,
        status=SessionStatus.COMPLETED
    )
    
    db.add(db_session)
    
    # Update description history
    if description:
        update_description_history(db, description)
    
    db.commit()
    db.refresh(db_session)
    
    return {"error": False, "session": db_session}

def get_user_sessions(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get sessions for a specific user with equipment info"""
    from sqlalchemy.orm import joinedload
    return db.query(UsageSession).options(
        joinedload(UsageSession.equipment)
    ).filter(UsageSession.user_id == user_id).order_by(UsageSession.start_time.desc()).offset(skip).limit(limit).all()

def get_active_sessions(db: Session, user_id: int):
    """Get all of user's active sessions"""
    return db.query(UsageSession).filter(
        UsageSession.user_id == user_id,
        UsageSession.status == SessionStatus.ACTIVE
    ).all()

def get_active_session(db: Session, user_id: int):
    """Get user's active session (deprecated - use get_active_sessions instead)"""
    return db.query(UsageSession).filter(
        UsageSession.user_id == user_id,
        UsageSession.status == SessionStatus.ACTIVE
    ).first()

def get_all_sessions(db: Session, skip: int = 0, limit: int = 100):
    """Get all sessions (admin only)"""
    return db.query(UsageSession).offset(skip).limit(limit).all()

def get_filtered_sessions(
    db: Session,
    equipment_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 1000
):
    """Get filtered sessions for admin dashboard"""
    from sqlalchemy.orm import joinedload
    
    query = db.query(UsageSession).options(
        joinedload(UsageSession.equipment),
        joinedload(UsageSession.user)
    )
    
    # Apply filters
    if equipment_id:
        query = query.filter(UsageSession.equipment_id == equipment_id)
    
    if user_id:
        query = query.filter(UsageSession.user_id == user_id)
    
    if status:
        query = query.filter(UsageSession.status == status.upper())
    
    if start_date:
        query = query.filter(UsageSession.start_time >= start_date)
    
    if end_date:
        # Add one day to end_date to include the entire end date
        end_date_inclusive = end_date + timedelta(days=1)
        query = query.filter(UsageSession.start_time < end_date_inclusive)
    
    # Order by start time descending
    query = query.order_by(UsageSession.start_time.desc())
    
    return query.offset(skip).limit(limit).all()

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