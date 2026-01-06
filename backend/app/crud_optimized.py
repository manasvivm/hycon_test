# backend/app/crud_optimized.py
"""
Optimized CRUD operations with proper concurrency control.
Critical operations that require locking to prevent race conditions.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, select
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import logging

from .models import (
    User, Equipment, UsageSession, DescriptionHistory,
    UserRole, EquipmentStatus, SessionStatus
)
from .schemas import SessionStart, SessionEnd
from .db_utils import (
    db_lock_row, retry_on_lock_error, ConcurrencyError,
    LockTimeoutError, QueryOptimizer
)

logger = logging.getLogger(__name__)

def ensure_timezone_aware(dt):
    """Ensure a datetime is timezone-aware, converting to UTC if it isn't"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

@retry_on_lock_error(max_retries=3, backoff=0.2)
def start_session_atomic(db: Session, session_data: SessionStart, user_id: int) -> Dict[str, Any]:
    """
    Start a new session with atomic locking to prevent race conditions.
    
    Race condition scenarios handled:
    1. Two users trying to start session on same equipment simultaneously
    2. User trying to start session while another is ending theirs
    3. Equipment status being updated while session is being created
    
    Returns:
        Dict with 'error' (bool) and either 'message' or 'session'
    """
    try:
        # Lock the equipment row to prevent concurrent modifications
        with db_lock_row(db, Equipment, session_data.equipment_id, timeout=10) as equipment:
            
            # Double-check equipment exists
            if equipment is None:
                return {"error": True, "message": "Equipment not found"}
            
            # Check if equipment is in maintenance
            if equipment.current_status == EquipmentStatus.MAINTENANCE:
                return {
                    "error": True,
                    "message": f"Equipment '{equipment.name}' is currently under maintenance"
                }
            
            # Get current time
            start_time = session_data.start_time or datetime.now(timezone.utc)
            start_time = ensure_timezone_aware(start_time)
            
            # Check if this user already has an active session with this equipment
            existing_user_session = db.query(UsageSession).filter(
                UsageSession.equipment_id == session_data.equipment_id,
                UsageSession.user_id == user_id,
                UsageSession.status == SessionStatus.ACTIVE
            ).first()
            
            if existing_user_session:
                return {
                    "error": True,
                    "message": "You already have an active session with this equipment"
                }
            
            # Check for ANY active session on this equipment (from any user)
            # This is the critical race condition check
            any_active_session = db.query(UsageSession).filter(
                UsageSession.equipment_id == session_data.equipment_id,
                UsageSession.status == SessionStatus.ACTIVE
            ).with_for_update().first()  # Lock the session row too
            
            if any_active_session:
                # Get user info for the conflicting session
                conflicting_user = db.query(User).filter(
                    User.id == any_active_session.user_id
                ).first()
                
                return {
                    "error": True,
                    "message": f"Equipment is currently in use by {conflicting_user.name if conflicting_user else 'another user'}. "
                               f"Started at {any_active_session.start_time.strftime('%I:%M %p')}"
                }
            
            # Check for planned/completed sessions that overlap with now
            # (For edge case of scheduled sessions)
            overlapping_session = db.query(UsageSession).filter(
                UsageSession.equipment_id == session_data.equipment_id,
                UsageSession.status == SessionStatus.COMPLETED,
                UsageSession.start_time <= start_time,
                UsageSession.end_time > start_time
            ).first()
            
            if overlapping_session:
                return {
                    "error": True,
                    "message": "This time slot conflicts with a scheduled session"
                }
            
            # All checks passed - create the session
            db_session = UsageSession(
                equipment_id=session_data.equipment_id,
                user_id=user_id,
                start_time=start_time,
                planned_end_time=ensure_timezone_aware(session_data.planned_end_time) if session_data.planned_end_time else None,
                description=session_data.description,
                remarks=session_data.remarks,
                scientist_signature=session_data.scientist_signature if hasattr(session_data, 'scientist_signature') else None,
                status=SessionStatus.ACTIVE
            )
            
            db.add(db_session)
            
            # Update equipment status atomically
            equipment.current_status = EquipmentStatus.IN_USE
            equipment.current_user_id = user_id
            equipment.current_session_start = start_time
            
            # Update description history for autocomplete
            if session_data.description:
                _update_description_history(db, session_data.description)
            
            # Commit everything atomically
            db.commit()
            db.refresh(db_session)
            
            logger.info(
                f"Session started successfully: user_id={user_id}, "
                f"equipment_id={session_data.equipment_id}, session_id={db_session.id}"
            )
            
            return {"error": False, "session": db_session}
            
    except LockTimeoutError as e:
        logger.warning(f"Lock timeout in start_session_atomic: {str(e)}")
        return {
            "error": True,
            "message": "Equipment is being accessed by another user. Please try again in a moment."
        }
    except Exception as e:
        logger.error(f"Error in start_session_atomic: {str(e)}", exc_info=True)
        db.rollback()
        return {"error": True, "message": f"Failed to start session: {str(e)}"}

@retry_on_lock_error(max_retries=3, backoff=0.2)
def end_session_atomic(db: Session, session_id: int, session_data: SessionEnd, user_id: int) -> Dict[str, Any]:
    """
    End an active session with atomic locking.
    
    Race condition scenarios handled:
    1. User trying to end session while another operation is updating it
    2. Multiple attempts to end the same session (e.g., button double-click)
    3. Equipment status being updated while session is being ended
    
    Returns:
        Dict with 'error' (bool) and 'message' or 'session'
    """
    try:
        # Lock the session row first
        session = db.query(UsageSession).filter(
            UsageSession.id == session_id
        ).with_for_update(nowait=False).first()
        
        if not session:
            return {"error": True, "message": "Session not found"}
        
        # Verify ownership
        if session.user_id != user_id:
            return {"error": True, "message": "You can only end your own sessions"}
        
        # Check if already ended (prevents double-ending)
        if session.status == SessionStatus.COMPLETED:
            return {
                "error": True,
                "message": "This session has already been ended"
            }
        
        # Lock the equipment row
        with db_lock_row(db, Equipment, session.equipment_id, timeout=10) as equipment:
            
            # Handle end time
            end_time = session_data.end_time if session_data and hasattr(session_data, 'end_time') and session_data.end_time else datetime.now(timezone.utc)
            end_time = ensure_timezone_aware(end_time)
            
            # Ensure start_time is timezone-aware
            session.start_time = ensure_timezone_aware(session.start_time)
            
            # Validate end time is after start time
            if end_time <= session.start_time:
                return {
                    "error": True,
                    "message": f"End time must be after start time"
                }
            
            # Update session
            session.end_time = end_time
            session.status = SessionStatus.COMPLETED
            
            if session_data and hasattr(session_data, 'remarks') and session_data.remarks:
                session.remarks = session_data.remarks
            if session_data and hasattr(session_data, 'scientist_signature') and session_data.scientist_signature:
                session.scientist_signature = session_data.scientist_signature
            
            # Check if there are other active sessions for this equipment
            other_active_sessions = db.query(UsageSession).filter(
                UsageSession.equipment_id == equipment.id,
                UsageSession.status == SessionStatus.ACTIVE,
                UsageSession.id != session_id
            ).count()
            
            # Update equipment status only if no other active sessions
            if other_active_sessions == 0:
                equipment.current_status = EquipmentStatus.AVAILABLE
                equipment.current_user_id = None
                equipment.current_session_start = None
            
            db.commit()
            db.refresh(session)
            
            logger.info(
                f"Session ended successfully: session_id={session_id}, "
                f"user_id={user_id}, equipment_id={equipment.id}"
            )
            
            return {"error": False, "session": session}
            
    except LockTimeoutError as e:
        logger.warning(f"Lock timeout in end_session_atomic: {str(e)}")
        return {
            "error": True,
            "message": "Session is being accessed by another process. Please try again."
        }
    except Exception as e:
        logger.error(f"Error in end_session_atomic: {str(e)}", exc_info=True)
        db.rollback()
        return {"error": True, "message": f"Failed to end session: {str(e)}"}

@retry_on_lock_error(max_retries=3, backoff=0.2)
def log_past_usage_atomic(
    db: Session, 
    equipment_id: int, 
    user_id: int, 
    start_time: datetime, 
    end_time: datetime,
    description: str = None,
    remarks: str = None
) -> Dict[str, Any]:
    """
    Log past equipment usage with validation and locking.
    
    Race condition scenarios handled:
    1. Multiple users logging overlapping past sessions
    2. Logging session while active session exists
    
    Returns:
        Dict with 'error' (bool) and 'message' or 'session'
    """
    try:
        # Lock equipment to check for conflicts
        with db_lock_row(db, Equipment, equipment_id, timeout=10) as equipment:
            
            if equipment is None:
                return {"error": True, "message": "Equipment not found"}
            
            # Validate times
            start_time = ensure_timezone_aware(start_time)
            end_time = ensure_timezone_aware(end_time) if end_time else None
            
            if not start_time or not end_time:
                return {"error": True, "message": "Both start and end times are required for past usage"}
            
            if end_time <= start_time:
                return {"error": True, "message": "End time must be after start time"}
            
            # Check if trying to log future session
            now = datetime.now(timezone.utc)
            if start_time > now:
                return {"error": True, "message": "Cannot log future usage. Use 'Start Session' instead"}
            
            # Check for overlapping sessions (locked for update to prevent race)
            overlapping = db.query(UsageSession).filter(
                UsageSession.equipment_id == equipment_id,
                or_(
                    # New session starts during existing session
                    and_(
                        UsageSession.start_time <= start_time,
                        UsageSession.end_time > start_time
                    ),
                    # New session ends during existing session
                    and_(
                        UsageSession.start_time < end_time,
                        UsageSession.end_time >= end_time
                    ),
                    # New session completely contains existing session
                    and_(
                        UsageSession.start_time >= start_time,
                        UsageSession.end_time <= end_time
                    )
                )
            ).with_for_update().first()
            
            if overlapping:
                return {
                    "error": True,
                    "message": f"This time period overlaps with an existing session from "
                               f"{overlapping.start_time.strftime('%I:%M %p')} to "
                               f"{overlapping.end_time.strftime('%I:%M %p') if overlapping.end_time else 'ongoing'}"
                }
            
            # Create past usage session
            db_session = UsageSession(
                equipment_id=equipment_id,
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                description=description,
                remarks=remarks,
                scientist_signature=None,  # Not applicable for past usage
                status=SessionStatus.COMPLETED,  # Past usage is always completed
                is_past_usage_log=True  # Mark as retroactive log
            )
            
            db.add(db_session)
            
            # Update description history
            if description:
                _update_description_history(db, description)
            
            db.commit()
            db.refresh(db_session)
            
            logger.info(
                f"Past usage logged successfully: user_id={user_id}, "
                f"equipment_id={equipment_id}, session_id={db_session.id}"
            )
            
            return {"error": False, "session": db_session}
            
    except LockTimeoutError as e:
        logger.warning(f"Lock timeout in log_past_usage_atomic: {str(e)}")
        return {
            "error": True,
            "message": "Equipment is being accessed. Please try again."
        }
    except Exception as e:
        logger.error(f"Error in log_past_usage_atomic: {str(e)}", exc_info=True)
        db.rollback()
        return {"error": True, "message": f"Failed to log past usage: {str(e)}"}

def _update_description_history(db: Session, description: str):
    """Helper to update description history for autocomplete"""
    existing = db.query(DescriptionHistory).filter(
        DescriptionHistory.description == description
    ).first()
    
    if existing:
        existing.usage_count += 1
        existing.last_used = datetime.now(timezone.utc)
    else:
        new_entry = DescriptionHistory(
            description=description,
            usage_count=1,
            last_used=datetime.now(timezone.utc)
        )
        db.add(new_entry)

def get_equipment_optimized(db: Session, skip: int = 0, limit: int = 100) -> List[Equipment]:
    """
    Get equipment with optimized eager loading to prevent N+1 queries.
    """
    query = db.query(Equipment).options(
        joinedload(Equipment.current_user),
        # Only load recent sessions to avoid loading too much data
        joinedload(Equipment.usage_sessions).joinedload(UsageSession.user)
    )
    
    return QueryOptimizer.paginate_query(query, page=(skip//limit)+1, per_page=limit).all()

def get_sessions_optimized(
    db: Session,
    user_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    status: Optional[SessionStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 1000
) -> List[UsageSession]:
    """
    Optimized session query with eager loading and efficient filtering.
    """
    query = db.query(UsageSession).options(
        joinedload(UsageSession.user),
        joinedload(UsageSession.equipment)
    )
    
    # Apply filters
    if user_id:
        query = query.filter(UsageSession.user_id == user_id)
    if equipment_id:
        query = query.filter(UsageSession.equipment_id == equipment_id)
    if status:
        query = query.filter(UsageSession.status == status)
    if start_date:
        query = query.filter(UsageSession.start_time >= start_date)
    if end_date:
        query = query.filter(UsageSession.start_time <= end_date)
    
    # Order by most recent first
    query = query.order_by(UsageSession.start_time.desc())
    
    return QueryOptimizer.paginate_query(query, page=(skip//limit)+1, per_page=limit).all()
