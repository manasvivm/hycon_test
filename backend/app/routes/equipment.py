# backend/app/routes/equipment.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas import Equipment, EquipmentCreate, User, DescriptionSuggestion
from ..auth import get_current_user, get_current_admin
from ..crud import get_equipment, create_equipment, get_equipment_by_id, get_description_suggestions

router = APIRouter(prefix="/equipment", tags=["Equipment"])

@router.get("/", response_model=List[Equipment])
async def list_equipment(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all equipment with current status"""
    equipment = get_equipment(db, skip=skip, limit=limit)
    return [Equipment.from_orm(eq) for eq in equipment]

@router.get("/{equipment_id}", response_model=Equipment)
async def get_equipment_detail(
    equipment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific equipment details"""
    equipment = get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )
    return Equipment.from_orm(equipment)

@router.post("/", response_model=Equipment)
async def create_new_equipment(
    equipment_data: EquipmentCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create new equipment (admin only)"""
    equipment = create_equipment(db, equipment_data)
    return Equipment.from_orm(equipment)

@router.put("/{equipment_id}", response_model=Equipment)
async def update_equipment(
    equipment_id: int,
    equipment_data: EquipmentCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update equipment details (admin only)"""
    from ..crud import update_equipment as update_eq
    equipment = update_eq(db, equipment_id, equipment_data)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )
    return Equipment.from_orm(equipment)

@router.delete("/{equipment_id}")
async def delete_equipment(
    equipment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete equipment (admin only)"""
    from ..crud import delete_equipment as delete_eq
    success = delete_eq(db, equipment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )
    return {"message": "Equipment deleted successfully"}

@router.get("/descriptions/suggestions", response_model=List[DescriptionSuggestion])
async def get_autocomplete_suggestions(
    query: str = "",
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get description suggestions for autocomplete"""
    suggestions = get_description_suggestions(db, query, limit)
    return [
        DescriptionSuggestion(
            description=suggestion.description,
            usage_count=suggestion.usage_count
        )
        for suggestion in suggestions
    ]