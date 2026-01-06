# backend/app/routes/samples.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import SampleSubmission, EmailRecipient, User
from ..schemas import (
    SampleSubmissionCreate,
    SampleSubmission as SampleSubmissionSchema,
    EmailRecipient as EmailRecipientSchema,
    EmailRecipientCreate,
    EmailRecipientUpdate
)
from ..auth import get_current_user, get_current_admin
from ..email_service import send_sample_submission_email

router = APIRouter(prefix="/samples", tags=["Sample Submissions"])

@router.post("/submit", response_model=SampleSubmissionSchema)
async def submit_sample(
    submission: SampleSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a new sample and send email notification"""
    try:
        # Create submission record
        db_submission = SampleSubmission(
            **submission.dict(),
            submitted_by_user_id=current_user.id
        )
        db.add(db_submission)
        db.commit()
        db.refresh(db_submission)
        
        # Prepare email data
        email_data = {
            'project': submission.project,
            'sample_name': submission.sample_name,
            'batch_no': submission.batch_no,
            'label_claim': submission.label_claim,
            'sample_quantity': submission.sample_quantity,
            'packaging_configuration': submission.packaging_configuration,
            'recommended_storage': submission.recommended_storage,
            'condition': submission.condition,
            'tests_to_be_performed': submission.tests_to_be_performed,
            'remarks': submission.remarks,
            'submitted_to': submission.submitted_to,
            'submitted_by': submission.submitted_by,
            'created_at': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }
        
        # Send email and track status
        try:
            email_sent = await send_sample_submission_email(
                recipient_email=submission.recipient_email,
                submission_data=email_data
            )
            
            if email_sent:
                print(f"✅ Email sent successfully to {submission.recipient_email}")
            else:
                print(f"⚠️ Email failed to send to {submission.recipient_email}")
                
        except Exception as email_error:
            # Log email error but don't fail the submission
            print(f"❌ Email error: {str(email_error)}")
        
        return db_submission
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting sample: {str(e)}"
        )


@router.get("/submissions", response_model=List[SampleSubmissionSchema])
def get_submissions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all sample submissions"""
    submissions = db.query(SampleSubmission)\
        .order_by(SampleSubmission.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return submissions


@router.get("/submissions/{submission_id}", response_model=SampleSubmissionSchema)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific submission"""
    submission = db.query(SampleSubmission).filter(SampleSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


# Email Recipients Management Routes
@router.get("/recipients", response_model=List[EmailRecipientSchema])
def get_email_recipients(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of email recipients for the dropdown"""
    query = db.query(EmailRecipient)
    if active_only:
        query = query.filter(EmailRecipient.is_active == True)
    recipients = query.order_by(EmailRecipient.name).all()
    return recipients


@router.post("/recipients", response_model=EmailRecipientSchema)
def create_email_recipient(
    recipient: EmailRecipientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a new email recipient (admin only)"""
    # Check if email already exists
    existing = db.query(EmailRecipient).filter(EmailRecipient.email == recipient.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    db_recipient = EmailRecipient(**recipient.dict())
    db.add(db_recipient)
    db.commit()
    db.refresh(db_recipient)
    return db_recipient


@router.put("/recipients/{recipient_id}", response_model=EmailRecipientSchema)
def update_email_recipient(
    recipient_id: int,
    recipient_update: EmailRecipientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update email recipient (admin only)"""
    db_recipient = db.query(EmailRecipient).filter(EmailRecipient.id == recipient_id).first()
    if not db_recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Update fields
    for field, value in recipient_update.dict(exclude_unset=True).items():
        setattr(db_recipient, field, value)
    
    db.commit()
    db.refresh(db_recipient)
    return db_recipient


@router.delete("/recipients/{recipient_id}")
def delete_email_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Delete email recipient (admin only)"""
    db_recipient = db.query(EmailRecipient).filter(EmailRecipient.id == recipient_id).first()
    if not db_recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    db.delete(db_recipient)
    db.commit()
    return {"message": "Recipient deleted successfully"}
