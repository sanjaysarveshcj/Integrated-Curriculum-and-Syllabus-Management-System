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

def create_directory_structure(drive_service, department, semester):
    try:
        # Create department folder if it doesn't exist
        department_folder = DriveDirectory.query.filter_by(
            department=department,
            type='department'
        ).first()

        if not department_folder:
            folder_metadata = {
                'name': f'{department} Department',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            department_folder_response = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            department_folder = DriveDirectory(
                department=department,
                semester='',
                drive_id=department_folder_response['id'],
                type='department'
            )
            db.session.add(department_folder)
            db.session.commit()

        # Create semester folder if it doesn't exist
        semester_folder = DriveDirectory.query.filter_by(
            department=department,
            semester=str(semester),
            type='semester'
        ).first()

        if not semester_folder:
            folder_metadata = {
                'name': f'Semester {semester}',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [department_folder.drive_id]
            }
            
            semester_folder_response = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            semester_folder = DriveDirectory(
                department=department,
                semester=str(semester),
                drive_id=semester_folder_response['id'],
                type='semester'
            )
            db.session.add(semester_folder)
            db.session.commit()

        # Create subject folder if it doesn't exist
        subject_folder = DriveDirectory.query.filter_by(
            department=department,
            semester=str(semester),
            type='subject'
        ).first()

        if not subject_folder:
            folder_metadata = {
                'name': 'Subject Documents',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [semester_folder.drive_id]
            }
            
            subject_folder_response = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            subject_folder = DriveDirectory(
                department=department,
                semester=str(semester),
                drive_id=subject_folder_response['id'],
                type='subject'
            )
            db.session.add(subject_folder)
            db.session.commit()

        # Create HOD folder if it doesn't exist
        hod_folder = DriveDirectory.query.filter_by(
            department=department,
            semester=str(semester),
            type='hod'
        ).first()

        if not hod_folder:
            folder_metadata = {
                'name': 'HOD Approval Documents',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [semester_folder.drive_id]
            }
            
            hod_folder_response = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            hod_folder = DriveDirectory(
                department=department,
                semester=str(semester),
                drive_id=hod_folder_response['id'],
                type='hod'
            )
            db.session.add(hod_folder)
            db.session.commit()

        # Create syllabus folder if it doesn't exist
        syllabus_folder = DriveDirectory.query.filter_by(
            department=department,
            semester=str(semester),
            type='syllabus'
        ).first()

        if not syllabus_folder:
            folder_metadata = {
                'name': 'Syllabus Documents',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [semester_folder.drive_id]
            }
            
            syllabus_folder_response = drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            syllabus_folder = DriveDirectory(
                department=department,
                semester=str(semester),
                drive_id=syllabus_folder_response['id'],
                type='syllabus'
            )
            db.session.add(syllabus_folder)
            db.session.commit()

        return True
    except Exception as e:
        print(f"Error creating directory structure: {str(e)}")
        return False

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
