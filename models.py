from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # 'principal', 'hod', 'advisor', 'teacher'
    department = db.Column(db.String(50))
    semester = db.Column(db.Integer)  # New field for semester
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class DriveDirectory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drive_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.String(100))
    department = db.Column(db.String(50))
    type = db.Column(db.String(20))  # 'department', 'semester', 'subject'
    semester = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DocumentApproval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    merged_file_id = db.Column(db.String(100))  # Google Drive file ID
    document_name = db.Column(db.String(255))  # Name of the document
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp when sent for approval
    approved_at = db.Column(db.DateTime, nullable=True)  # Timestamp when approved
    rejected_at = db.Column(db.DateTime, nullable=True)  # Timestamp when rejected
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<DocumentApproval {self.department} {self.semester}>'
