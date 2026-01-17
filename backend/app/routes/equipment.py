# backend/app/routes/equipment.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import logging
import csv
import io
import openpyxl
from pydantic import ValidationError

from ..database import get_db
from ..schemas import Equipment, EquipmentCreate, User, DescriptionSuggestion
from ..auth import get_current_user, get_current_admin
from ..crud import create_equipment, get_equipment_by_id, get_description_suggestions
from ..crud_optimized import get_equipment_optimized
from ..websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/equipment", tags=["Equipment"])

@router.get("/", response_model=List[Equipment])
async def list_equipment(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all equipment with current status.
    Uses optimized query with eager loading to prevent N+1 queries.
    """
    equipment = get_equipment_optimized(db, skip=skip, limit=limit)
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
    
    # Broadcast equipment creation to all connected clients
    await manager.broadcast_equipment_update(
        equipment_id=equipment.id,
        action='create',
        data={
            'id': equipment.id,
            'name': equipment.name,
            'equipment_id': equipment.equipment_id,
            'location': equipment.location,
            'current_status': equipment.current_status.value
        }
    )
    
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
    
    # Broadcast equipment update to all connected clients
    await manager.broadcast_equipment_update(
        equipment_id=equipment.id,
        action='update',
        data={
            'id': equipment.id,
            'name': equipment.name,
            'equipment_id': equipment.equipment_id,
            'location': equipment.location,
            'current_status': equipment.current_status.value
        }
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
    
    # Broadcast equipment deletion to all connected clients
    await manager.broadcast_equipment_update(
        equipment_id=equipment_id,
        action='delete',
        data={'id': equipment_id}
    )
    
    return {"message": "Equipment deleted successfully"}

@router.post("/batch-upload")
async def batch_upload_equipment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Batch upload equipment from CSV file (admin only)
    Expected CSV columns: name, equipment_id, location, description
    """
    if not file.filename.endswith(('.csv', '.txt', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and XLSX files are supported"
        )
    
    try:
        contents = await file.read()
        created_count = 0
        errors = []

        if file.filename.endswith('.xlsx'):
            # Parse Excel file using openpyxl
            workbook = openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
            sheet = workbook.active
            rows = sheet.iter_rows(values_only=True)
            try:
                header = next(rows)
            except StopIteration:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty Excel file")

            headers = [str(h).strip().lower() if h is not None else '' for h in header]
            for row_num, row in enumerate(rows, start=2):
                try:
                    row_vals = {headers[i]: (row[i] if i < len(row) and row[i] is not None else '') for i in range(len(headers))}
                    equipment_data = EquipmentCreate(
                        name=str(row_vals.get('name', '')).strip(),
                        equipment_id=str(row_vals.get('equipment_id', '')).strip(),
                        location=str(row_vals.get('location', '')).strip(),
                        description=str(row_vals.get('description', '')).strip()
                    )
                    create_equipment(db, equipment_data)
                    created_count += 1
                except ValidationError as e:
                    errors.append(f"Row {row_num}: Validation error - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
        else:
            # CSV handling
            decoded = contents.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded))
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Clean up field names (remove BOM, whitespace)
                    cleaned_row = {k.strip().lower().replace('\ufeff', ''): (v.strip() if v is not None else '') for k, v in row.items()}
                    
                    # Map CSV columns to schema fields
                    equipment_data = EquipmentCreate(
                        name=cleaned_row.get('name', ''),
                        equipment_id=cleaned_row.get('equipment_id', ''),
                        location=cleaned_row.get('location', ''),
                        description=cleaned_row.get('description', '')
                    )
                    
                    create_equipment(db, equipment_data)
                    created_count += 1
                    
                except ValidationError as e:
                    errors.append(f"Row {row_num}: Validation error - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
        
        return {
            "message": f"Successfully created {created_count} equipment entries",
            "created": created_count,
            "errors": errors if errors else None
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File encoding error. Please ensure the file is UTF-8 encoded"
        )
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )

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