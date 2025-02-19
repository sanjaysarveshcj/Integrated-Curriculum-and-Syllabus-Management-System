from app import app, db
from models import User

def create_default_users():
    with app.app_context():
        # Create principal user
        principal = User(
            username='principal',
            email='principal@school.edu',
            role='principal',
            department='Administration'
        )
        principal.set_password('admin123')
        
        # Create HOD user
        hod = User(
            username='hod_cs',
            email='hod.cs@school.edu',
            role='hod',
            department='Computer Science'
        )
        hod.set_password('admin123')
        
        # Create advisor user
        advisor = User(
            username='advisor_cs',
            email='advisor.cs@school.edu',
            role='advisor',
            department='Computer Science',
            semester=1
        )
        advisor.set_password('admin123')
        
        # Create teacher user
        teacher = User(
            username='teacher_cs',
            email='teacher.cs@school.edu',
            role='teacher',
            department='Computer Science',
            semester=1
        )
        teacher.set_password('admin123')
        
        # Add all users
        db.session.add(principal)
        db.session.add(hod)
        db.session.add(advisor)
        db.session.add(teacher)
        
        try:
            db.session.commit()
            print("Default users created successfully!")
            print("\nUser Credentials:")
            print("-" * 50)
            print("Principal:")
            print("Email: principal@school.edu")
            print("Password: admin123")
            print("-" * 50)
            print("HOD:")
            print("Email: hod.cs@school.edu")
            print("Password: admin123")
            print("-" * 50)
            print("Advisor:")
            print("Email: advisor.cs@school.edu")
            print("Password: admin123")
            print("-" * 50)
            print("Teacher:")
            print("Email: teacher.cs@school.edu")
            print("Password: admin123")
        except Exception as e:
            print(f"Error creating users: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    create_default_users()
