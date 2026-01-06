# backend/seed_email_recipients.py
"""Add default email recipients"""
from app.database import SessionLocal
from app.models import EmailRecipient

def seed_recipients():
    db = SessionLocal()
    try:
        # Check if recipients already exist
        existing_count = db.query(EmailRecipient).count()
        if existing_count > 0:
            print(f"Email recipients already exist ({existing_count} found). Skipping seed.")
            return
        
        # Default recipients - using working email for testing
        recipients = [
            {
                "name": "Lab Manager (Test)",
                "email": "thegreatjunkbob@gmail.com",
                "department": "Management",
                "is_active": True
            }
        ]
        
        for recipient_data in recipients:
            recipient = EmailRecipient(**recipient_data)
            db.add(recipient)
        
        db.commit()
        print(f"Successfully added {len(recipients)} email recipients")
        
        # Display the added recipients
        print("\nAdded recipients:")
        for r in recipients:
            print(f"  - {r['name']} ({r['department']}) - {r['email']}")
            
    except Exception as e:
        db.rollback()
        print(f"Error seeding recipients: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_recipients()
