"""Background task to check and end expired sessions"""
from datetime import datetime, timezone
from sqlalchemy import and_
from .models import UsageSession, SessionStatus, EquipmentStatus

def check_and_end_expired_sessions(db):
    """Check for sessions that have passed their planned end time and end them"""
    now = datetime.now(timezone.utc)
    
    # Find all active sessions that have passed their planned end time
    expired_sessions = db.query(UsageSession).filter(
        and_(
            UsageSession.status == SessionStatus.ACTIVE,
            UsageSession.planned_end_time <= now,
            UsageSession.planned_end_time.isnot(None)
        )
    ).all()
    
    for session in expired_sessions:
        # End the session
        session.status = SessionStatus.COMPLETED
        session.end_time = session.planned_end_time
        
        # Update equipment status
        equipment = session.equipment
        equipment.current_status = EquipmentStatus.AVAILABLE
        equipment.current_user_id = None
        equipment.current_session_start = None
    
    if expired_sessions:
        db.commit()