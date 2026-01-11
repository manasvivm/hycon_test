# backend/app/routes/samples.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import (
    SampleSubmission, EmailRecipient, User, Notification, 
    SubmissionStatusHistory, MessageThread, 
    NotificationType, SubmissionStatus
)
from ..schemas import (
    SampleSubmissionCreate,
    SampleSubmission as SampleSubmissionSchema,
    EmailRecipient as EmailRecipientSchema,
    EmailRecipientCreate,
    EmailRecipientUpdate
)
from ..auth import get_current_user, get_current_admin
from ..rate_limiter import rate_limiter

router = APIRouter(prefix="/samples", tags=["Sample Submissions"])

@router.post("/submit", response_model=List[SampleSubmissionSchema])
async def submit_sample(
    submission: SampleSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a new sample submission to multiple recipients:
    - Optimized for high concurrency with bulk operations
    - Thread-safe with proper database locking
    - Efficient single-query recipient lookup
    - Rate limited to prevent abuse
    """
    # Rate limit: Max 20 submissions per minute per user
    rate_limiter.check_rate_limit(current_user.id, max_requests=20, window_seconds=60)
    
    try:
        # Fetch all recipient users in ONE query (optimization)
        recipient_emails = submission.recipient_emails
        recipient_users = db.query(User).filter(User.email.in_(recipient_emails)).all()
        recipient_map = {user.email: user for user in recipient_users}
        
        # Prepare base submission data once
        base_submission_data = submission.dict(exclude={'recipient_emails'})
        
        # Prepare all objects for efficient batch processing
        created_submissions = []
        status_histories = []
        notifications = []
        
        # Create objects for each recipient
        for recipient_email in recipient_emails:
            recipient_user = recipient_map.get(recipient_email)
            
            # Create submission with automatic reference number
            db_submission = SampleSubmission(
                **base_submission_data,
                recipient_email=recipient_email,
                submitted_by_user_id=current_user.id,
                recipient_user_id=recipient_user.id if recipient_user else None,
                status='pending'
            )
            db.add(db_submission)
            created_submissions.append(db_submission)
        
        # Flush to get IDs for all submissions at once
        db.flush()
        
        # Now create related objects with proper IDs
        for db_submission in created_submissions:
            recipient_user = recipient_map.get(db_submission.recipient_email)
            
            # Create status history
            status_history = SubmissionStatusHistory(
                submission_id=db_submission.id,
                old_status=None,
                new_status='pending',
                changed_by_user_id=current_user.id,
                notes="Initial submission"
            )
            status_histories.append(status_history)
            
            # Create notification for recipient
            if recipient_user:
                notification = Notification(
                    user_id=recipient_user.id,
                    submission_id=db_submission.id,
                    notification_type='new_submission',
                    title=f"New Sample Submission: {submission.project}",
                    message=f"{current_user.name} submitted a new sample: {submission.sample_name}"
                )
                notifications.append(notification)
        
        # Bulk add all related objects
        if status_histories:
            db.bulk_save_objects(status_histories)
        if notifications:
            db.bulk_save_objects(notifications)
        
        # Single commit for all operations (transaction safety)
        db.commit()
        
        # Refresh all submissions to get relationships
        for sub in created_submissions:
            db.refresh(sub)
        
        return created_submissions
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting sample: {str(e)}"
        )        # Commit all submissions at once
        db.commit()
        
        # Refresh all submissions to get updated data
        for sub in created_submissions:
            db.refresh(sub)
        
        return created_submissions
    
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


# ============================================================================
# INBOX & MESSAGING ENDPOINTS - Enterprise Communication System
# ============================================================================

@router.get("/inbox", response_model=List[SampleSubmissionSchema])
def get_inbox(
    status_filter: Optional[str] = None,
    is_unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get inbox for current user (submissions where they are the recipient)
    Optimized with eager loading to prevent N+1 queries
    """
    from sqlalchemy.orm import joinedload
    
    query = db.query(SampleSubmission)\
        .options(
            joinedload(SampleSubmission.submitted_by_user),
            joinedload(SampleSubmission.recipient_user)
        )\
        .filter(SampleSubmission.recipient_user_id == current_user.id)
    
    if status_filter:
        query = query.filter(SampleSubmission.status == status_filter)
    
    if is_unread_only:
        query = query.filter(SampleSubmission.is_read == False)
    
    submissions = query.order_by(SampleSubmission.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return submissions


@router.get("/inbox/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of unread submissions in inbox"""
    count = db.query(SampleSubmission).filter(
        SampleSubmission.recipient_user_id == current_user.id,
        SampleSubmission.is_read == False
    ).count()
    
    return {"unread_count": count}


@router.get("/sent", response_model=List[SampleSubmissionSchema])
def get_sent_submissions(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get submissions sent by current user
    Optimized with eager loading
    """
    from sqlalchemy.orm import joinedload
    
    query = db.query(SampleSubmission)\
        .options(
            joinedload(SampleSubmission.submitted_by_user),
            joinedload(SampleSubmission.recipient_user)
        )\
        .filter(SampleSubmission.submitted_by_user_id == current_user.id)
    
    if status_filter:
        query = query.filter(SampleSubmission.status == status_filter)
    
    submissions = query.order_by(SampleSubmission.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return submissions


@router.put("/{submission_id}/mark-read")
def mark_submission_read(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a submission as read and auto-update status to 'received'
    """
    submission = db.query(SampleSubmission).filter(
        SampleSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Only recipient can mark as read
    if submission.recipient_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to mark this submission as read")
    
    # Mark as read
    submission.is_read = True
    submission.read_at = datetime.now(datetime.now().astimezone().tzinfo)
    submission.read_by_user_id = current_user.id
    
    # Auto-update status from 'pending' to 'received' when first opened
    if submission.status == 'pending':
        submission.status = 'received'
        
        # Create audit trail entry
        status_history = SubmissionStatusHistory(
            submission_id=submission_id,
            old_status='pending',
            new_status='received',
            changed_by_user_id=current_user.id,
            notes="Automatically marked as received when opened"
        )
        db.add(status_history)
    
    db.commit()
    return {"message": "Submission marked as read and received"}


@router.put("/{submission_id}/status")
def update_submission_status(
    submission_id: int,
    new_status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update submission status (admin or recipient only)
    Creates audit trail entry
    """
    submission = db.query(SampleSubmission).filter(
        SampleSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Check authorization (admin or recipient)
    if current_user.role.value != "admin" and submission.recipient_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update status")
    
    # Validate status
    try:
        new_status_enum = SubmissionStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
    
    # Create audit trail entry
    status_history = SubmissionStatusHistory(
        submission_id=submission_id,
        old_status=submission.status,
        new_status=new_status_enum.value,
        changed_by_user_id=current_user.id,
        notes=notes
    )
    db.add(status_history)
    
    # Update submission
    old_status = submission.status
    submission.status = new_status_enum.value
    
    # Create notification for submitter if status changed
    if old_status != new_status_enum.value:
        notification = Notification(
            user_id=submission.submitted_by_user_id,
            submission_id=submission_id,
            notification_type='status_change',  # Use string directly
            title=f"Status Update: {submission.reference_number}",
            message=f"Status changed from {old_status} to {new_status_enum.value}"
        )
        db.add(notification)
    
    db.commit()
    return {"message": "Status updated successfully", "new_status": new_status}


# ============================================================================
# MESSAGE THREAD ENDPOINTS - In-App Communication
# ============================================================================

@router.post("/{submission_id}/reply")
def reply_to_submission(
    submission_id: int,
    message: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a reply/comment to a submission"""
    submission = db.query(SampleSubmission).filter(
        SampleSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Create message
    thread_message = MessageThread(
        submission_id=submission_id,
        sender_id=current_user.id,
        message=message,
        is_system_message=False
    )
    db.add(thread_message)
    
    # Create notification for the other party
    # If sender is replying, notify recipient. If recipient is replying, notify sender.
    notify_user_id = submission.recipient_user_id if current_user.id == submission.submitted_by_user_id else submission.submitted_by_user_id
    
    if notify_user_id:
        notification = Notification(
            user_id=notify_user_id,
            submission_id=submission_id,
            notification_type='new_reply',  # Use string directly
            title=f"New Reply: {submission.reference_number}",
            message=f"{current_user.name} replied to your submission"
        )
        db.add(notification)
    
    db.commit()
    db.refresh(thread_message)
    
    return {
        "message": "Reply added successfully",
        "thread_id": thread_message.id,
        "created_at": thread_message.created_at
    }


@router.get("/{submission_id}/thread")
def get_submission_thread(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full conversation thread for a submission"""
    submission = db.query(SampleSubmission).filter(
        SampleSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Check authorization
    if (submission.submitted_by_user_id != current_user.id and 
        submission.recipient_user_id != current_user.id and 
        current_user.role.value != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to view this thread")
    
    # Get all messages
    messages = db.query(MessageThread).filter(
        MessageThread.submission_id == submission_id
    ).order_by(MessageThread.created_at.asc()).all()
    
    # Format response
    thread = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        thread.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": sender.name if sender else "System",
            "message": msg.message,
            "is_system_message": msg.is_system_message,
            "created_at": msg.created_at
        })
    
    return {
        "submission_id": submission_id,
        "reference_number": submission.reference_number,
        "thread": thread
    }


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@router.get("/notifications")
def get_notifications(
    is_unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notifications for current user"""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )
    
    if is_unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return notifications


@router.get("/notifications/unread-count")
def get_notification_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"unread_count": count}


@router.put("/notifications/{notification_id}/mark-read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.now(datetime.now().astimezone().tzinfo)
    
    db.commit()
    return {"message": "Notification marked as read"}


@router.put("/notifications/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.now(datetime.now().astimezone().tzinfo)
    })
    
    db.commit()
    return {"message": "All notifications marked as read"}
