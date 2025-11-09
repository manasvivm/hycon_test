# backend/mock_data.py
from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models import User, Equipment, UsageSession, DescriptionHistory, UserRole, EquipmentStatus, SessionStatus
from app.auth import get_password_hash
from datetime import datetime, timedelta
import random

def create_mock_data():
    """Create mock data for POC"""
    create_tables()
    db = SessionLocal()
    
    try:
        # Clear existing data
        db.query(UsageSession).delete()
        db.query(DescriptionHistory).delete()
        db.query(Equipment).delete()
        db.query(User).delete()
        db.commit()
        
        print("Creating mock users...")
        # Create users
        users_data = [
            {"name": "Admin User", "email": "admin@hycon.com", "role": UserRole.ADMIN, "password": "admin123"},
            {"name": "Lab Manager", "email": "manager@hycon.com", "role": UserRole.ADMIN, "password": "manager123"},
            {"name": "John Doe", "email": "john.doe@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "Sarah Johnson", "email": "sarah.j@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "Mike Rodriguez", "email": "mike.r@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "Emily Chen", "email": "emily.c@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "David Kim", "email": "david.k@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "Lisa Wang", "email": "lisa.w@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "Robert Brown", "email": "robert.b@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
            {"name": "Jennifer Davis", "email": "jennifer.d@hycon.com", "role": UserRole.EMPLOYEE, "password": "user123"},
        ]
        
        users = []
        for user_data in users_data:
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"]
            )
            db.add(user)
            users.append(user)
        
        db.commit()
        print(f"Created {len(users)} users")
        
        print("Creating mock equipment...")
        # Create equipment
        equipment_data = [
            {"name": "High Performance Liquid Chromatograph", "equipment_id": "HPLC-001", "location": "Lab A"},
            {"name": "Gas Chromatograph Mass Spectrometer", "equipment_id": "GCMS-002", "location": "Lab A"},
            {"name": "UV-Vis Spectrophotometer", "equipment_id": "UVVIS-003", "location": "Lab B"},
            {"name": "Fourier Transform Infrared Spectrometer", "equipment_id": "FTIR-004", "location": "Lab B"},
            {"name": "Nuclear Magnetic Resonance", "equipment_id": "NMR-005", "location": "Lab C"},
            {"name": "X-Ray Diffractometer", "equipment_id": "XRD-006", "location": "Lab C"},
            {"name": "Scanning Electron Microscope", "equipment_id": "SEM-007", "location": "Lab D"},
            {"name": "Transmission Electron Microscope", "equipment_id": "TEM-008", "location": "Lab D"},
            {"name": "Atomic Force Microscope", "equipment_id": "AFM-009", "location": "Lab D"},
            {"name": "Differential Scanning Calorimeter", "equipment_id": "DSC-010", "location": "Lab E"},
            {"name": "Thermogravimetric Analyzer", "equipment_id": "TGA-011", "location": "Lab E"},
            {"name": "Dynamic Light Scattering", "equipment_id": "DLS-012", "location": "Lab F"},
            {"name": "Particle Size Analyzer", "equipment_id": "PSA-013", "location": "Lab F"},
            {"name": "Dissolution Tester", "equipment_id": "DT-014", "location": "Lab G"},
            {"name": "Tablet Hardness Tester", "equipment_id": "THT-015", "location": "Lab G"},
            {"name": "Friability Tester", "equipment_id": "FT-016", "location": "Lab G"},
            {"name": "Disintegration Tester", "equipment_id": "DIT-017", "location": "Lab G"},
            {"name": "Content Uniformity Analyzer", "equipment_id": "CUA-018", "location": "Lab H"},
            {"name": "Karl Fischer Titrator", "equipment_id": "KFT-019", "location": "Lab H"},
            {"name": "pH Meter", "equipment_id": "PHM-020", "location": "Lab I"},
            {"name": "Conductivity Meter", "equipment_id": "CM-021", "location": "Lab I"},
            {"name": "Balance (Analytical)", "equipment_id": "BAL-022", "location": "Lab I"},
            {"name": "Centrifuge", "equipment_id": "CENT-023", "location": "Lab J"},
            {"name": "Incubator", "equipment_id": "INC-024", "location": "Lab J"},
            {"name": "Autoclave", "equipment_id": "AUTO-025", "location": "Lab K"},
            {"name": "Laminar Flow Hood", "equipment_id": "LFH-026", "location": "Lab K"},
            {"name": "Biosafety Cabinet", "equipment_id": "BSC-027", "location": "Lab K"},
            {"name": "Rotary Evaporator", "equipment_id": "ROT-028", "location": "Lab L"},
            {"name": "Vacuum Oven", "equipment_id": "VO-029", "location": "Lab L"},
            {"name": "Freeze Dryer", "equipment_id": "FD-030", "location": "Lab L"},
        ]
        
        equipment_list = []
        for eq_data in equipment_data:
            equipment = Equipment(
                name=eq_data["name"],
                equipment_id=eq_data["equipment_id"],
                location=eq_data["location"],
                description=f"Advanced {eq_data['name'].lower()} for pharmaceutical analysis",
                current_status=EquipmentStatus.AVAILABLE  # Set default status as available
            )
            db.add(equipment)
            equipment_list.append(equipment)
        
        db.commit()
        print(f"Created {len(equipment_list)} equipment pieces")
        
        print("Creating mock description history...")
        # Create description history for autocomplete
        descriptions = [
            "Protein analysis and purification",
            "Drug stability testing",
            "Compound identification and quantification",
            "Quality control testing",
            "Method development and validation",
            "Impurity profiling",
            "Dissolution testing",
            "Content uniformity analysis",
            "Particle size measurement",
            "Thermal analysis of compounds",
            "Molecular structure determination",
            "Surface characterization",
            "Crystalline form analysis",
            "Water content determination",
            "pH and conductivity measurement",
            "Microbial testing",
            "Sterility testing",
            "Tablet hardness and friability",
            "Sample preparation",
            "Research and development",
        ]
        
        for i, desc in enumerate(descriptions):
            desc_history = DescriptionHistory(
                description=desc,
                usage_count=random.randint(1, 20),
                last_used=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.add(desc_history)
        
        db.commit()
        print(f"Created {len(descriptions)} description entries")
        
        print("Creating mock usage sessions...")
        # Create historical usage sessions
        employee_users = [u for u in users if u.role == UserRole.EMPLOYEE]
        
        sessions_created = 0
        for days_back in range(30, 0, -1):  # Last 30 days
            date = datetime.utcnow() - timedelta(days=days_back)
            
            # Create 3-8 sessions per day
            daily_sessions = random.randint(3, 8)
            
            for _ in range(daily_sessions):
                user = random.choice(employee_users)
                equipment = random.choice(equipment_list)
                description = random.choice(descriptions)
                
                # Random start time during working hours (8 AM - 6 PM)
                start_hour = random.randint(8, 17)
                start_minute = random.randint(0, 59)
                session_start = date.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                # Session duration: 30 minutes to 4 hours
                duration_minutes = random.randint(30, 240)
                session_end = session_start + timedelta(minutes=duration_minutes)
                
                # Check if session would conflict with existing ones
                existing = db.query(UsageSession).filter(
                    UsageSession.equipment_id == equipment.id,
                    UsageSession.start_time <= session_end,
                    UsageSession.end_time >= session_start
                ).first()
                
                if not existing:  # Only create if no conflict
                    session = UsageSession(
                        equipment_id=equipment.id,
                        user_id=user.id,
                        start_time=session_start,
                        end_time=session_end,
                        description=description,
                        remarks=random.choice([
                            "Analysis completed successfully",
                            "Standard procedure followed",
                            "No issues encountered",
                            "Results documented",
                            "Equipment functioning normally",
                            ""
                        ]),
                        status=SessionStatus.COMPLETED,
                        scientist_signature=f"Digital signature by {user.name} at {session_end.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    db.add(session)
                    sessions_created += 1
        
        # Create 2-3 active sessions for demonstration
        active_users = random.sample(employee_users, 2)
        available_equipment = [eq for eq in equipment_list if eq.current_status == EquipmentStatus.AVAILABLE]
        
        for user in active_users:
            if available_equipment:
                equipment = random.choice(available_equipment)
                available_equipment.remove(equipment)
                
                # Start session 1-3 hours ago
                hours_ago = random.randint(1, 3)
                session_start = datetime.utcnow() - timedelta(hours=hours_ago)
                
                session = UsageSession(
                    equipment_id=equipment.id,
                    user_id=user.id,
                    start_time=session_start,
                    description=random.choice(descriptions),
                    status=SessionStatus.ACTIVE
                )
                db.add(session)
                
                # Update equipment status
                equipment.current_status = EquipmentStatus.IN_USE
                equipment.current_user_id = user.id
                equipment.current_session_start = session_start
                
                sessions_created += 1
        
        db.commit()
        print(f"Created {sessions_created} usage sessions")
        
        print("Mock data creation completed successfully!")
        print("\nLogin credentials:")
        print("Admin: admin@hycon.com / admin123")
        print("Manager: manager@hycon.com / manager123")
        print("Employee: john.doe@hycon.com / user123")
        print("(All employees use password: user123)")
        
    except Exception as e:
        print(f"Error creating mock data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_mock_data()