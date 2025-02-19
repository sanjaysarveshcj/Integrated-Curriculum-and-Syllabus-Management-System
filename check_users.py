from app import app, db
from models import User

with app.app_context():
    users = User.query.all()
    print("\nAll Users in Database:")
    print("-" * 50)
    for user in users:
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Department: {user.department}")
        print(f"Semester: {user.semester}")
        print("-" * 50)
