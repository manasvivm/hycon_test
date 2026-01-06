# backend/app/routes/sessions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from ..database import get_db
from ..schemas import UsageSession, SessionStart, SessionEnd, User, ConflictCheck, PastUsageLog
from ..auth import get_current_user, get_current_admin
from ..crud import (
    get_user_sessions, 
    get_active_session, get_active_sessions, get_all_sessions, check_time_conflict,
    get_filtered_sessions
)
# Import optimized atomic operations
from ..crud_optimized import (
    start_session_atomic,
    end_session_atomic,
    log_past_usage_atomic
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("/start")
async def start_equipment_session(
    session_data: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new active equipment session with atomic locking.
    Prevents race conditions when multiple users try to start sessions simultaneously.
    """
    logger.info(f"User {current_user.id} attempting to start session on equipment {session_data.equipment_id}")
    
    result = start_session_atomic(db, session_data, current_user.id)
    
    if result["error"]:
        logger.warning(f"Session start failed for user {current_user.id}: {result['message']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    logger.info(f"Session {result['session'].id} started successfully for user {current_user.id}")
    return {
        "message": "Session started successfully",
        "session": UsageSession.from_orm(result["session"])
    }

@router.post("/log-past-usage")
async def log_past_usage_session(
    usage_data: PastUsageLog,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a completed past usage session with overlap detection.
    Prevents overlapping time slots with atomic locking.
    """
    logger.info(f"User {current_user.id} logging past usage for equipment {usage_data.equipment_id}")
    
    result = log_past_usage_atomic(
        db=db,
        equipment_id=usage_data.equipment_id,
        user_id=current_user.id,
        start_time=usage_data.start_time,
        end_time=usage_data.end_time,
        description=usage_data.description,
        remarks=usage_data.remarks
    )
    
    if result["error"]:
        logger.warning(f"Past usage logging failed for user {current_user.id}: {result['message']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    logger.info(f"Past usage session {result['session'].id} logged successfully")
    return {
        "message": "Past usage logged successfully",
        "session": UsageSession.from_orm(result["session"])
    }

@router.put("/{session_id}/end")
async def end_equipment_session(
    session_id: int,
    session_data: SessionEnd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    End an active session with atomic locking.
    Prevents double-ending and concurrent modifications.
    """
    logger.info(f"User {current_user.id} attempting to end session {session_id}")
    
    result = end_session_atomic(db, session_id, session_data, current_user.id)
    
    if result["error"]:
        logger.warning(f"Session end failed for session {session_id}: {result['message']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    logger.info(f"Session {session_id} ended successfully by user {current_user.id}")
    return {
        "message": "Session ended successfully",
        "session": UsageSession.from_orm(result["session"])
    }

@router.get("/my-sessions", response_model=List[UsageSession])
async def get_my_sessions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's sessions"""
    sessions = get_user_sessions(db, current_user.id, skip, limit)
    return [UsageSession.from_orm(session) for session in sessions]

@router.get("/my-active")
async def get_my_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's active sessions"""
    sessions = get_active_sessions(db, current_user.id)
    return {
        "active_sessions": [UsageSession.from_orm(session) for session in sessions]
    }

@router.get("/", response_model=List[UsageSession])
async def get_all_sessions_admin(
    skip: int = 0,
    limit: int = 1000,
    equipment_id: int = None,
    user_id: int = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all sessions with optional filters (admin only)"""
    from datetime import datetime
    
    # Parse dates if provided
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    sessions = get_filtered_sessions(
        db=db,
        equipment_id=equipment_id,
        user_id=user_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        skip=skip,
        limit=limit
    )
    return [UsageSession.from_orm(session) for session in sessions]

@router.post("/check-conflict", response_model=ConflictCheck)
async def check_session_conflict(
    equipment_id: int,
    start_time: str,
    end_time: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check for time conflicts before creating session"""
    from datetime import datetime
    
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time) if end_time else None
    
    conflict = check_time_conflict(db, equipment_id, start_dt, end_dt)
    
    return ConflictCheck(
        conflict=conflict["conflict"],
        message=conflict.get("message"),
        conflicting_session=conflict.get("conflicting_session")
    )