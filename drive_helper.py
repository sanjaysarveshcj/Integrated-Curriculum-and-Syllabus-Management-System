from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_google_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            redirect_uri='http://localhost:5000/oauth2callback'
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        return None, auth_url

    try:
        service = build('drive', 'v3', credentials=creds)
        return service, None
    except Exception as e:
        return None, str(e)

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

def create_curriculum_structure(service, department, regulation_code, main_folder_id):
    try:
        # Check/Create Department folder
        dept_exists = folder_exists(service, department, main_folder_id)
        if dept_exists:
            raise Exception(f"Department {department} already exists")
        
        dept_folder_id = create_folder(service, department, main_folder_id)
        
        # Check/Create Regulation folder
        reg_exists = folder_exists(service, regulation_code, dept_folder_id)
        if reg_exists:
            raise Exception(f"Regulation {regulation_code} already exists")
            
        reg_folder_id = create_folder(service, regulation_code, dept_folder_id)
        
        # Create Semesters folder
        semesters_folder_id = create_folder(service, "semesters", reg_folder_id)
        
        # Create semester folders (1-8)
        for sem in range(1, 9):
            sem_name = f"Semester_{sem}"
            sem_folder_id = create_folder(service, sem_name, semesters_folder_id)
            create_folder(service, "Subjects", sem_folder_id)
            
        return True
    except Exception as e:
        raise Exception(f"Error creating curriculum structure: {str(e)}")
