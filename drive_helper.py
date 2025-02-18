from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from models import db, DriveDirectory
from google_auth_oauthlib.flow import Flow
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_google_drive_service():
    """Get an authorized Google Drive service instance."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if os.path.exists('credentials.json'):
            flow = Flow.from_client_secrets_file(
                'credentials.json',
                scopes=SCOPES,
                redirect_uri='http://localhost:5000/oauth2callback'
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            return None, auth_url
        else:
            raise Exception("credentials.json not found")

    try:
        service = build('drive', 'v3', credentials=creds)
        return service, None
    except Exception as e:
        raise Exception(f"Error getting drive service: {str(e)}")

def create_folder(service, folder_name, parent_id=None):
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        file = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        return file.get('id')
    except Exception as e:
        raise Exception(f"Error creating folder {folder_name}: {str(e)}")

def folder_exists(service, folder_name, parent_id=None):
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        return len(results.get('files', [])) > 0
    except Exception as e:
        raise Exception(f"Error checking folder existence: {str(e)}")

def create_directory_structure(service, department, regulation_code=None, parent_folder_id=None):
    """Create directory structure and store information in database"""
    try:
        # Create department folder
        dept_metadata = {
            'name': department,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            dept_metadata['parents'] = [parent_folder_id]
            
        dept_folder = service.files().create(body=dept_metadata, fields='id').execute()
        
        # Store department folder info
        dept_dir = DriveDirectory(
            drive_id=dept_folder['id'],
            name=department,
            type='department',
            department=department
        )
        db.session.add(dept_dir)
        
        # Create regulation folder if provided
        reg_folder_id = dept_folder['id']
        if regulation_code:
            reg_metadata = {
                'name': regulation_code,
                'parents': [dept_folder['id']],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            reg_folder = service.files().create(body=reg_metadata, fields='id').execute()
            reg_folder_id = reg_folder['id']
        
        # Create semester folders
        for sem in range(1, 9):
            sem_metadata = {
                'name': f'Semester_{sem}',
                'parents': [reg_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            sem_folder = service.files().create(body=sem_metadata, fields='id').execute()
            
            # Store semester folder info
            sem_dir = DriveDirectory(
                drive_id=sem_folder['id'],
                name=f'Semester_{sem}',
                parent_id=reg_folder_id,
                type='semester',
                department=department,
                semester=sem
            )
            db.session.add(sem_dir)
            
            # Create subjects folder
            subj_metadata = {
                'name': 'Subjects',
                'parents': [sem_folder['id']],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            subj_folder = service.files().create(body=subj_metadata, fields='id').execute()
            
            # Store subjects folder info
            subj_dir = DriveDirectory(
                drive_id=subj_folder['id'],
                name='Subjects',
                parent_id=sem_folder['id'],
                type='subject',
                department=department,
                semester=sem
            )
            db.session.add(subj_dir)
        
        db.session.commit()
        return dept_folder['id']
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error creating directory structure: {str(e)}")

def get_viewable_folder_id(user):
    """Get the appropriate folder ID based on user role and department"""
    if user.role == 'hod':
        # HOD can view their department folder
        dir = DriveDirectory.query.filter_by(
            department=user.department,
            type='department'
        ).first()
        return dir.drive_id if dir else None
        
    elif user.role == 'advisor':
        # Advisor can view their semester folder
        dir = DriveDirectory.query.filter_by(
            department=user.department,
            type='semester',
            semester=user.semester
        ).first()
        return dir.drive_id if dir else None
        
    elif user.role == 'teacher':
        # Teacher can view their semester's subjects folder
        dir = DriveDirectory.query.filter_by(
            department=user.department,
            type='subject',
            semester=user.semester
        ).first()
        return dir.drive_id if dir else None
    
    return None
