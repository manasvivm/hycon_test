# backend/app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import timedelta
import csv
import io
import openpyxl
from pydantic import ValidationError
from ..database import get_db
from ..schemas import UserLogin, Token, UserCreate, User
from ..auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, get_current_admin
from ..crud import create_user, get_user_by_email, get_users

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User.from_orm(user)
    }

@router.post("/register", response_model=User)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (for POC purposes)"""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = create_user(db, user_data)
    return User.from_orm(user)

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    """Get all users (for admin filters)"""
    users = get_users(db)
    return [User.from_orm(user) for user in users]

@router.post("/users/batch-upload")
async def batch_upload_users(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Batch upload users from CSV/XLSX file (admin only)
    Expected columns: name, email, password, role
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
                    
                    # Check if user already exists
                    existing = get_user_by_email(db, str(row_vals.get('email', '')).strip())
                    if existing:
                        errors.append(f"Row {row_num}: Email {row_vals.get('email', '')} already exists")
                        continue
                    
                    user_data = UserCreate(
                        name=str(row_vals.get('name', '')).strip(),
                        email=str(row_vals.get('email', '')).strip(),
                        password=str(row_vals.get('password', '')).strip(),
                        role=str(row_vals.get('role', 'employee')).strip().lower()
                    )
                    create_user(db, user_data)
                    created_count += 1
                except ValidationError as e:
                    errors.append(f"Row {row_num}: Validation error - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
        else:
            # CSV handling
            decoded = contents.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded))
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    cleaned_row = {k.strip().lower().replace('\ufeff', ''): (v.strip() if v is not None else '') for k, v in row.items()}
                    
                    # Check if user already exists
                    existing = get_user_by_email(db, cleaned_row.get('email', ''))
                    if existing:
                        errors.append(f"Row {row_num}: Email {cleaned_row.get('email', '')} already exists")
                        continue
                    
                    user_data = UserCreate(
                        name=cleaned_row.get('name', ''),
                        email=cleaned_row.get('email', ''),
                        password=cleaned_row.get('password', ''),
                        role=cleaned_row.get('role', 'employee').lower()
                    )
                    create_user(db, user_data)
                    created_count += 1
                    
                except ValidationError as e:
                    errors.append(f"Row {row_num}: Validation error - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
        
        return {
            "message": f"Successfully created {created_count} user(s)",
            "created": created_count,
            "errors": errors if errors else None
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File encoding error. Please ensure the file is UTF-8 encoded"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )