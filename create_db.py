from app import app, db
from models import User, DriveDirectory, DocumentApproval
from werkzeug.security import generate_password_hash
from drive_helper import create_directory_structure, get_google_drive_service

CURRICULUM_FOLDER_ID = "11efeP3LJ23w2lFt1AJI_jJBNyseRHPfn"  # Your main folder ID

with app.app_context():
    # Only create tables that don't exist
    db.create_all()

    # Create test users if they don't exist
    test_users = [
        {
            'email': 'principal@example.com',
            'username': 'principal',
            'password': 'password123',
            'role': 'principal',
            'department': 'admin',
            'semester': 1
        },
        {
            'email': 'hod@example.com',
            'username': 'hod',
            'password': 'hod123',
            'role': 'hod',
            'department': 'CSE',
            'semester': 1
        },
        {
            'email': 'advisor@example.com',
            'username': 'advisor',
            'password': 'advisor123',
            'role': 'advisor',
            'department': 'CSE',
            'semester': 1
        },
        {
            'email': 'teacher@example.com',
            'username': 'teacher',
            'password': 'teacher123',
            'role': 'teacher',
            'department': 'CSE',
            'semester': 1
        }
    ]

    for user_data in test_users:
        if not User.query.filter_by(email=user_data['email']).first():
            user = User(
                email=user_data['email'],
                username=user_data['username'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role'],
                department=user_data['department'],
                semester=user_data['semester']
            )
            db.session.add(user)
    
    db.session.commit()

    # Get Google Drive service
    drive_service, auth_url = get_google_drive_service()
    if drive_service:
        try:
            # Create directory structure for CSE department
            department = 'CSE'
            regulation = 'R-2021'  # Add regulation code
            
            # Clear existing directory records
            DriveDirectory.query.filter_by(department=department).delete()
            db.session.commit()

            # Create new directory structure
            create_directory_structure(
                service=drive_service,
                department=department,
                regulation_code=regulation,
                parent_folder_id=CURRICULUM_FOLDER_ID
            )
            print("Directory structure created successfully!")
        except Exception as e:
            print(f"Error creating directory structure: {str(e)}")
    else:
        print("Warning: Could not create directory structure. Please authenticate with Google Drive first.")

    print("Database tables created and test users added successfully!")
