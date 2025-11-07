# backend/app/routes/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import User, AnalyticsDashboard, EquipmentUtilization, UserActivity
from ..auth import get_current_admin
from ..crud import get_equipment_utilization, get_user_activity
from ..models import UsageSession, SessionStatus
from sqlalchemy import func

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    days: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get analytics dashboard data (admin only)"""
    
    # Get equipment utilization
    equipment_util = get_equipment_utilization(db, days)
    equipment_utilization = [
        EquipmentUtilization(**util) for util in equipment_util
    ]
    
    # Get user activity
    user_activity_data = get_user_activity(db, days)
    user_activity = [
        UserActivity(**activity) for activity in user_activity_data
    ]
    
    # Get session counts
    total_sessions = db.query(func.count(UsageSession.id)).scalar()
    active_sessions = db.query(func.count(UsageSession.id)).filter(
        UsageSession.status == SessionStatus.ACTIVE
    ).scalar()
    
    return AnalyticsDashboard(
        equipment_utilization=equipment_utilization,
        user_activity=user_activity,
        total_sessions=total_sessions,
        active_sessions=active_sessions
    )

@router.get("/equipment-utilization")
async def get_equipment_utilization_data(
    days: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed equipment utilization data"""
    return get_equipment_utilization(db, days)

@router.get("/user-activity")
async def get_user_activity_data(
    days: int = 30,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed user activity data"""
    return get_user_activity(db, days)