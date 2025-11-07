# backend/app/routes/sessions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas import UsageSession, SessionStart, SessionEnd, User, ConflictCheck
from ..auth import get_current_user, get_current_admin
from ..crud import (
    start_session, end_session, get_user_sessions, 
    get_active_session, get_all_sessions, check_time_conflict
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("/start")
async def start_equipment_session(
    session_data: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new equipment session"""
    # Check if user already has an active session
    active = get_active_session(db, current_user.id)
    if active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active session. Please end it first."
        )
    
    result = start_session(db, session_data, current_user.id)
    
    if result["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {
        "message": "Session started successfully",
        "session": UsageSession.from_orm(result["session"])
    }

@router.put("/{session_id}/end")
async def end_equipment_session(
    session_id: int,
    session_data: SessionEnd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """End an active session"""
    result = end_session(db, session_id, session_data, current_user.id)
    
    if result["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
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
async def get_my_active_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's active session"""
    session = get_active_session(db, current_user.id)
    if not session:
        return {"active_session": None}
    
    return {
        "active_session": UsageSession.from_orm(session)
    }

@router.get("/", response_model=List[UsageSession])
async def get_all_sessions_admin(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all sessions (admin only)"""
    sessions = get_all_sessions(db, skip, limit)
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