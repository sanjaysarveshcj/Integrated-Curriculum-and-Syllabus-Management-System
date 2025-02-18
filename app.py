from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from drive_helper import create_directory_structure, get_viewable_folder_id, get_google_drive_service
from models import db, User, DriveDirectory
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from docx import Document
from docxtpl import DocxTemplate
import os
import io
import re
import logging
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=30)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load environment variables
load_dotenv()

# Allow OAuth2 insecure transport for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_TYPE'] = 'filesystem'

CURRICULUM_FOLDER_ID = "11efeP3LJ23w2lFt1AJI_jJBNyseRHPfn"  # Your main folder ID

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            session.permanent = True  # Make the session permanent
            
            if user.role == 'principal':
                return redirect(url_for('principal_dashboard'))
            elif user.role == 'hod':
                return redirect(url_for('hod_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'advisor':
                return redirect(url_for('advisor_dashboard'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/principal')
@login_required
def principal_dashboard():
    if current_user.role != 'principal':
        return redirect(url_for('login'))
    hods = User.query.filter_by(role='hod').all()
    return render_template('principal_dashboard.html', hods=hods)

@app.route('/hod')
@login_required
def hod_dashboard():
    if current_user.role != 'hod':
        flash('Access denied')
        return redirect(url_for('index'))
        
    # Get staff members under this HOD
    staff = User.query.filter_by(
        department=current_user.department,
        created_by=current_user.id
    ).all()
    
    # Get department folder ID
    dept_folder = DriveDirectory.query.filter_by(
        department=current_user.department,
        type='department'
    ).first()
    
    folder_id = dept_folder.drive_id if dept_folder else None
    
    return render_template(
        'hod_dashboard.html',
        staff=staff,
        folder_id=folder_id
    )

@app.route('/advisor')
@login_required
def advisor_dashboard():
    if current_user.role != 'advisor':
        flash('Access denied')
        return redirect(url_for('index'))
        
    # Get semester folder ID
    semester_folder = DriveDirectory.query.filter_by(
        department=current_user.department,
        type='semester',
        semester=current_user.semester
    ).first()
    
    folder_id = semester_folder.drive_id if semester_folder else None
    
    return render_template('advisor_dashboard.html', folder_id=folder_id)

@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))
        
    # Get subjects folder ID
    subjects_folder = DriveDirectory.query.filter_by(
        department=current_user.department,
        type='subject',
        semester=current_user.semester
    ).first()
    
    folder_id = subjects_folder.drive_id if subjects_folder else None
    
    return render_template('teacher_dashboard.html', folder_id=folder_id)

@app.route('/front_form')
@login_required
def front_form_redirect():
    return redirect(url_for('frontform'))

@app.route('/frontform', methods=['GET', 'POST']) 
@login_required
def frontform():
    if request.method == "POST":
        try:
            form_data = process_form_data(request.form)
            doc_io = generate_docx(form_data)

            return send_file(
                doc_io,
                as_attachment=True,
                download_name="Completed_Curriculum.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            logging.error(f"Error processing document: {e}")
            return f"Error processing document: {e}", 500

    return render_template("frontform.html")

@app.route('/create_syllabus')
@login_required
def syllabusform():
    return render_template('syllabusform.html')  # Load the HTML form

@app.route('/generate', methods=['POST'])
def generate_doc():
    template_path = os.path.join(BASE_DIR, "template.docx")

    if not os.path.exists(template_path):
        return "Error: template.docx not found!", 404
    doc = Document(template_path)
   # Collect form data and clean all text fields if pasted from PDF
    semester = request.form.get('Semester', '')
    course_name = request.form.get('CourseName', '')
    course_code = request.form.get('CourseCode', '')
    course_description = clean_pdf_text(request.form.get('CourseDescription', ''))
    prerequisites =clean_pdf_text(request.form.get('Prerequisites', ''))
    objectives = [clean_pdf_text(obj.strip()) for obj in request.form.getlist('objective') if obj.strip()]
    experiments = [clean_pdf_text(obj.strip()) for obj in request.form.getlist('experiments') if obj.strip()]
    course_outcomes = [clean_pdf_text(outcome.strip()) for outcome in request.form.getlist('course_outcome') if outcome.strip()]
    textbooks = [clean_pdf_text(textbook.strip()) for textbook in request.form.getlist('textbook') if textbook.strip()]
    references = [clean_pdf_text(reference.strip()) for reference in request.form.getlist('reference') if reference.strip()]
    assessments_grading = clean_pdf_text(request.form.get('AssessmentsGrading', ''))
    course_format = clean_pdf_text(request.form.get('courseformat', ''))
    assessments = clean_pdf_text(request.form.get('assessments', ''))
    grading = clean_pdf_text(request.form.get('grading', ''))
    # Format placeholders into readable lists and apply `<REMOVE>` for empty values
    placeholders = {
        "{Semester}": semester if semester else "<REMOVE>",
        "{CourseName}": course_name if course_name else "<REMOVE>",
        "{CourseCode}": course_code if course_code else "<REMOVE>",
        "{Coursedescriptionname}": "COURSE DESCRIPTION" if course_description else "<REMOVE>",
        "{CourseDescription}": course_description if course_description else "<REMOVE>",
        "{prerequisitename}": "PREREQUISITES" if prerequisites else "<REMOVE>",
        "{Prerequisites}": prerequisites if prerequisites else "<REMOVE>",
        "{AssessmentsGrading}": assessments_grading if assessments_grading else "<REMOVE>",
        "{CourseFormat}": course_format if course_format else "<REMOVE>",
        "{Assessments}": assessments if assessments else "<REMOVE>",
        "{Grading}": grading if grading else "<REMOVE>",
    }

    # Collect Practical Periods checkbox and value
    has_practical = request.form.get('hasPractical')  
    practical_periods = request.form.get('practical_periods') if has_practical else "<REMOVE>"
    # Add practical periods to placeholders if applicable
    if has_practical and practical_periods:
        placeholders["{PracticalPeriodsName}"] = "PRACTICAL PERIODS "
        placeholders["{PracticalPeriods}"] = practical_periods if practical_periods else "<REMOVE>"
    else:
        placeholders["{PracticalPeriodsName}"] = "<REMOVE>"
        placeholders["{PracticalPeriods}"] = "<REMOVE>"

    # Dynamically collect and format units including the number of periods
    units = []
    total_periods = 0
    i = 1

    while True:
        unit_title = clean_pdf_text(request.form.get(f'unit_title_{i}', ''))
        unit_content = clean_pdf_text(request.form.get(f'unit_content_{i}', ''))
        unit_periods = request.form.get(f'unit_periods_{i}')

        if not unit_title or not unit_content:
            break

        try:
            unit_periods = int(unit_periods) if unit_periods else 0
        except ValueError:
            unit_periods = 0

        total_periods += unit_periods
        units.append((unit_title, unit_content, unit_periods))
        i += 1
    # Format units into a structured text block with periods
    units_text = ""
    for i, (unit_title, unit_content, unit_periods) in enumerate(units, 1):
        units_text += f"UNIT {i}: {unit_title} (No. of Periods: {unit_periods})\n{unit_content}"
    # Add formatted units and total periods to placeholders



    youtube_references = []
    i = 1

    while True:
        youtube_title = clean_pdf_text(request.form.get(f'youtube_title_{i}', ''))
        youtube_desc = clean_pdf_text(request.form.get(f'youtube_desc_{i}', ''))
        youtube_url = request.form.get(f'youtube_url_{i}', '')

        if not youtube_title or not youtube_desc or not youtube_url:
            break  # Stop if any field is missing

        youtube_references.append((youtube_title, youtube_desc, youtube_url))
        i += 1

    youtube_text = ""
    for i, (youtube_title, youtube_desc, youtube_url) in enumerate(youtube_references, 1):
        youtube_text += f"Video {i}: {youtube_title}\nDescription: {youtube_desc}\nURL: {youtube_url}\n\n"
    placeholders["{TotalPeriods}"] ="NUMBER OF THEORY PERIODS:" + str(total_periods) if total_periods > 0 else "<REMOVE>"
    replace_list_section(doc, "{Objectives}", objectives, title="COURSE OBJECTIVES")
    replace_list_section(doc, "{Experiments}", experiments,title = "LIST OF EXPERIMENTS")
    replace_list_section(doc, "{Textbooks}", textbooks, title="TEXTBOOKS")
    replace_list_section(doc, "{References}", references, title="REFERENCES")
    format_course_outcomes(doc, "{CourseOutcomes}", course_outcomes)
    replace_units_with_formatting(doc, units)
    replace_semester(doc, semester)
    replace_course_name_in_table(doc, course_name)
    replace_course_code_in_table(doc, course_code)
    replace_course_description(doc, course_description)
    replace_prerequisites(doc, prerequisites)
    replace_course_format(doc, course_format)
    replace_assessments_grading(doc, assessments_grading)
    replace_practical_periods(doc, practical_periods)    
    total_periods = request.form.get('TotalPeriods', '')
    practical_periods = request.form.get('PracticalPeriods', '')
    replace_youtube_references_with_formatting(doc, youtube_references)
    # ✅ Call functions to replace placeholders
    replace_total_periods(doc, units)
    replace_practical_periods(doc, practical_periods)
    # Save and return the generated document
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return send_file(file_stream, as_attachment=True, download_name="Course_Syllabus.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")



@app.route('/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.role == 'principal' and request.form.get('role') == 'hod':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        department = request.form.get('department')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('principal_dashboard'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('principal_dashboard'))
            
        hod = User(
            username=username,
            email=email,
            role='hod',
            department=department,
            created_by=current_user.id
        )
        hod.set_password(password)
        db.session.add(hod)
        db.session.commit()
        flash('HOD account created successfully')
        return redirect(url_for('principal_dashboard'))
        
    elif current_user.role == 'hod':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role')
        semester = request.form.get('semester')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('hod_dashboard'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('hod_dashboard'))
            
        staff = User(
            username=username,
            email=email,
            role=role,
            department=current_user.department,
            semester=semester,
            created_by=current_user.id
        )
        staff.set_password(password)
        db.session.add(staff)
        db.session.commit()
        flash('Staff account created successfully')
        return redirect(url_for('hod_dashboard'))
        
    return redirect(url_for('principal_dashboard'))

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    
    # Only principal can delete HODs
    if current_user.role == 'principal' and user_to_delete.role == 'hod':
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('HOD account deleted successfully')
        return redirect(url_for('principal_dashboard'))
    
    # Only HODs can delete their created staff
    elif current_user.role == 'hod' and user_to_delete.created_by == current_user.id:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('Staff account deleted successfully')
        return redirect(url_for('hod_dashboard'))
    
    flash('You do not have permission to delete this user')
    return redirect(request.referrer)

@app.route('/principal/create_directory', methods=['GET', 'POST'])
@login_required
def create_directory():
    if current_user.role != 'principal':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        department = request.form.get('department')
        regulation_code = request.form.get('regulation_code')
        
        try:
            service, auth_url = get_google_drive_service()
            if not service:
                # Store the form data in session
                session['pending_directory'] = {
                    'department': department,
                    'regulation_code': regulation_code
                }
                return redirect(auth_url)
            
            create_directory_structure(service, department, regulation_code, CURRICULUM_FOLDER_ID)
            flash('Directory structure created successfully!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            
        return redirect(url_for('create_directory'))
        
    return render_template('create_directory.html')

@app.route('/oauth2callback')
def oauth2callback():
    try:
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/drive.file'],
            redirect_uri=url_for('oauth2callback', _external=True)
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Save credentials
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
        
        # Store success message in flash
        flash('Successfully authenticated with Google Drive!', 'success')
        
        # Check if there is a pending directory creation
        if 'pending_directory' in session:
            pending_directory = session.pop('pending_directory')
            service, _ = get_google_drive_service()
            create_directory_structure(service, pending_directory['department'], pending_directory['regulation_code'], CURRICULUM_FOLDER_ID)
            flash('Directory structure created successfully!', 'success')
        
        # Redirect to create directory page
        return redirect(url_for('create_directory'))
    except Exception as e:
        flash(f'Error during authentication: {str(e)}', 'error')
        return redirect(url_for('create_directory'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))








def generate_doc():
    template_path = os.path.join(BASE_DIR, "template.docx")

    if not os.path.exists(template_path):
        return "Error: template.docx not found!", 404
    doc = Document(template_path)
   # Collect form data and clean all text fields if pasted from PDF
    semester = request.form.get('Semester', '')
    course_name = request.form.get('CourseName', '')
    course_code = request.form.get('CourseCode', '')
    course_description = clean_pdf_text(request.form.get('CourseDescription', ''))
    prerequisites =clean_pdf_text(request.form.get('Prerequisites', ''))
    objectives = [clean_pdf_text(obj.strip()) for obj in request.form.getlist('objective') if obj.strip()]
    experiments = [clean_pdf_text(obj.strip()) for obj in request.form.getlist('experiments') if obj.strip()]
    course_outcomes = [clean_pdf_text(outcome.strip()) for outcome in request.form.getlist('course_outcome') if outcome.strip()]
    textbooks = [clean_pdf_text(textbook.strip()) for textbook in request.form.getlist('textbook') if textbook.strip()]
    references = [clean_pdf_text(reference.strip()) for reference in request.form.getlist('reference') if reference.strip()]
    assessments_grading = clean_pdf_text(request.form.get('AssessmentsGrading', ''))
    course_format = clean_pdf_text(request.form.get('courseformat', ''))
    assessments = clean_pdf_text(request.form.get('assessments', ''))
    grading = clean_pdf_text(request.form.get('grading', ''))
    # Format placeholders into readable lists and apply `<REMOVE>` for empty values
    placeholders = {
        "{Semester}": semester if semester else "<REMOVE>",
        "{CourseName}": course_name if course_name else "<REMOVE>",
        "{CourseCode}": course_code if course_code else "<REMOVE>",
        "{Coursedescriptionname}": "COURSE DESCRIPTION" if course_description else "<REMOVE>",
        "{CourseDescription}": course_description if course_description else "<REMOVE>",
        "{prerequisitename}": "PREREQUISITES" if prerequisites else "<REMOVE>",
        "{Prerequisites}": prerequisites if prerequisites else "<REMOVE>",
        "{AssessmentsGrading}": assessments_grading if assessments_grading else "<REMOVE>",
        "{CourseFormat}": course_format if course_format else "<REMOVE>",
        "{Assessments}": assessments if assessments else "<REMOVE>",
        "{Grading}": grading if grading else "<REMOVE>",
    }

    # Collect Practical Periods checkbox and value
    has_practical = request.form.get('hasPractical')  
    practical_periods = request.form.get('practical_periods') if has_practical else "<REMOVE>"
    # Add practical periods to placeholders if applicable
    if has_practical and practical_periods:
        placeholders["{PracticalPeriodsName}"] = "PRACTICAL PERIODS "
        placeholders["{PracticalPeriods}"] = practical_periods if practical_periods else "<REMOVE>"
    else:
        placeholders["{PracticalPeriodsName}"] = "<REMOVE>"
        placeholders["{PracticalPeriods}"] = "<REMOVE>"

    # Dynamically collect and format units including the number of periods
    units = []
    total_periods = 0
    i = 1

    while True:
        unit_title = clean_pdf_text(request.form.get(f'unit_title_{i}', ''))
        unit_content = clean_pdf_text(request.form.get(f'unit_content_{i}', ''))
        unit_periods = request.form.get(f'unit_periods_{i}')

        if not unit_title or not unit_content:
            break

        try:
            unit_periods = int(unit_periods) if unit_periods else 0
        except ValueError:
            unit_periods = 0

        total_periods += unit_periods
        units.append((unit_title, unit_content, unit_periods))
        i += 1
    # Format units into a structured text block with periods
    units_text = ""
    for i, (unit_title, unit_content, unit_periods) in enumerate(units, 1):
        units_text += f"UNIT {i}: {unit_title} (No. of Periods: {unit_periods})\n{unit_content}"
    # Add formatted units and total periods to placeholders



    youtube_references = []
    i = 1

    while True:
        youtube_title = clean_pdf_text(request.form.get(f'youtube_title_{i}', ''))
        youtube_desc = clean_pdf_text(request.form.get(f'youtube_desc_{i}', ''))
        youtube_url = request.form.get(f'youtube_url_{i}', '')

        if not youtube_title or not youtube_desc or not youtube_url:
            break  # Stop if any field is missing

        youtube_references.append((youtube_title, youtube_desc, youtube_url))
        i += 1

    youtube_text = ""
    for i, (youtube_title, youtube_desc, youtube_url) in enumerate(youtube_references, 1):
        youtube_text += f"Video {i}: {youtube_title}\nDescription: {youtube_desc}\nURL: {youtube_url}\n\n"
    placeholders["{TotalPeriods}"] ="NUMBER OF THEORY PERIODS:" + str(total_periods) if total_periods > 0 else "<REMOVE>"
    replace_list_section(doc, "{Objectives}", objectives, title="COURSE OBJECTIVES")
    replace_list_section(doc, "{Experiments}", experiments,title = "LIST OF EXPERIMENTS")
    replace_list_section(doc, "{Textbooks}", textbooks, title="TEXTBOOKS")
    replace_list_section(doc, "{References}", references, title="REFERENCES")
    format_course_outcomes(doc, "{CourseOutcomes}", course_outcomes)
    replace_units_with_formatting(doc, units)
    replace_semester(doc, semester)
    replace_course_name_in_table(doc, course_name)
    replace_course_code_in_table(doc, course_code)
    replace_course_description(doc, course_description)
    replace_prerequisites(doc, prerequisites)
    replace_course_format(doc, course_format)
    replace_assessments_grading(doc, assessments_grading)
    replace_practical_periods(doc, practical_periods)    
    total_periods = request.form.get('TotalPeriods', '')
    practical_periods = request.form.get('PracticalPeriods', '')
    replace_youtube_references_with_formatting(doc, youtube_references)
    # ✅ Call functions to replace placeholders
    replace_total_periods(doc, units)
    replace_practical_periods(doc, practical_periods)
    # Save and return the generated document
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return send_file(file_stream, as_attachment=True, download_name="Course_Syllabus.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")



def replace_semester(doc, semester):
    """Replaces the {Semester} placeholder with the actual semester value."""
    placeholder = "{Semester}"
    value = semester if semester else "<REMOVE>"

    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            paragraph.text = paragraph.text.replace(placeholder, value)

            # Remove if marked as `<REMOVE>`
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)
            return

def replace_course_name_in_table(doc, course_name):
    """Finds and replaces {CourseName} inside tables while maintaining formatting."""
    placeholder = "{CourseName}"
    value = course_name if course_name else "<REMOVE>"

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if placeholder in paragraph.text:
                        full_text = "".join(run.text for run in paragraph.runs)  # Get full text
                        new_text = full_text.replace(placeholder, value)  # Replace placeholder

                        # Clear existing runs
                        for run in paragraph.runs:
                            run.text = ""

                        # Insert new text while maintaining formatting
                        if paragraph.runs:
                            paragraph.runs[0].text = new_text
                        return  # Stop after first replacement to prevent duplicates

def replace_course_code_in_table(doc, course_code):
    """Finds and replaces {CourseCode} inside tables while maintaining formatting."""
    placeholder = "{CourseCode}"
    value = course_code if course_code else "<REMOVE>"

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if placeholder in paragraph.text:
                        full_text = "".join(run.text for run in paragraph.runs)  # Get full text
                        new_text = full_text.replace(placeholder, value)  # Replace placeholder

                        # Clear existing runs
                        for run in paragraph.runs:
                            run.text = ""

                        # Insert new text while maintaining formatting
                        if paragraph.runs:
                            paragraph.runs[0].text = new_text
                        return  # Stop after first replacement to prevent duplicates

def replace_course_description(doc, course_description):
    """Replaces {CourseDescription} while maintaining formatting and indentation."""
    placeholder = "{CourseDescription}"
    value = course_description if course_description else "<REMOVE>"
    title = "COURSE DESCRIPTION" if course_description else "<REMOVE>"

    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            # Preserve original paragraph formatting
            paragraph_format = paragraph.paragraph_format  # Get original indentation

            # Insert title only if a course description exists
            if course_description:
                title_paragraph = paragraph.insert_paragraph_before("")
                title_paragraph.style = paragraph.style  # Keep the same style
                title_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  # Copy indentation
                title_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  # Copy first-line indent

                title_run = title_paragraph.add_run(title)
                title_run.bold = True
                title_run.font.size = Pt(11)

            # Preserve formatting while replacing text
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, value)

            # If placeholder is removed, delete paragraph
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)

            return  # Stop after replacing the first occurrence

def replace_youtube_references_with_formatting(doc, youtube_references):
    """Replaces {YouTubeReferences} placeholder in a DOCX file with formatted YouTube reference data."""
    for paragraph in doc.paragraphs:
        if "{YouTubeReferences}" in paragraph.text:
            p_element = paragraph._element  # Reference to remove placeholder
            parent = p_element.getparent()  # Get parent XML element
            paragraph_style = paragraph.style  # Store the style of the original paragraph

            new_paragraph = paragraph.insert_paragraph_before("")
            new_paragraph.style = paragraph_style
            parent.remove(p_element)  # Remove {YouTubeReferences} placeholder

            for i, (youtube_title, youtube_desc, youtube_url) in enumerate(youtube_references, 1):
                # Create a single paragraph for Title & Description
                single_paragraph = new_paragraph.insert_paragraph_before("")
                single_paragraph.style = paragraph_style

                # Insert Video Title (Bold & Clickable)
                title_run = single_paragraph.add_run(youtube_title)
                title_run.bold = True
                title_run.font.size = Pt(11)
                make_hyperlink(title_run, youtube_url)  # Make title clickable

                # Append Description (Normal) immediately after Title
                desc_run = single_paragraph.add_run(f" - {youtube_desc}")  
                desc_run.bold = False  # Ensure only title is bold
                desc_run.font.size = Pt(11)

            break  # Stop after replacing the first occurrence

def make_hyperlink(run, url):
    """Converts a run into a clickable hyperlink in a DOCX file."""
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), url)  # Set the link
    run_element = run._r
    run_element.append(hyperlink)

def replace_prerequisites(doc, prerequisites):
    """Adds 'PREREQUISITES' title above {Prerequisites} while maintaining formatting."""
    placeholder = "{Prerequisites}"
    title = "PREREQUISITES"
    value = prerequisites.strip() if prerequisites else "<REMOVE>"

    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            p_element = paragraph._element  
            parent = p_element.getparent()

            # ✅ If prerequisites are empty, remove the placeholder paragraph
            if not prerequisites.strip():
                parent.remove(p_element)
                return  

            # ✅ Insert Title Above Without Extra Blank Paragraph
            title_paragraph = paragraph.insert_paragraph_before("")
            title_paragraph.style = paragraph.style  # Keep the same style
            title_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  # Copy indentation
            title_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  # Copy first-line indent

            title_run = title_paragraph.add_run(title)
            title_run.bold = True
            title_run.font.size = Pt(11)

            # ✅ Replace placeholder with prerequisites content
            paragraph.text = value  

            # ✅ Remove the paragraph if `<REMOVE>` is present
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)

            return  # Stop after processing the first occurrence
  # Stop after processing the first occurrence

def replace_course_format(doc, course_format):
    """Adds 'COURSE FORMAT' title above {CourseFormat} while maintaining formatting."""
    placeholder = "{CourseFormat}"
    title = "COURSE FORMAT"
    value = course_format if course_format else "<REMOVE>"
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            if not course_format.strip():
                p_element = paragraph._element
                p_element.getparent().remove(p_element)
                return  
            # Preserve original paragraph formatting
            paragraph_format = paragraph.paragraph_format  

            # Insert title above the placeholder
            title_paragraph = paragraph.insert_paragraph_before("")
            title_paragraph.style = paragraph.style  # Keep the same style
            title_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  # Copy indentation
            title_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  # Copy first-line indent

            title_run = title_paragraph.add_run(title)
            title_run.bold = True
            title_run.font.size = Pt(11)

            # Preserve the {CourseFormat} content while replacing the placeholder
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, value)

            # Remove the paragraph if `<REMOVE>` is present
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)

            return  # Stop after processing the first occurrence

def replace_assessments_grading(doc, assessments_grading):
    """Adds 'ASSESSMENTS AND GRADING' title above {AssessmentsGrading} while maintaining formatting."""
    placeholder = "{AssessmentsGrading}"
    title = "ASSESSMENTS AND GRADING"
    value = assessments_grading if assessments_grading else "<REMOVE>"
# Skip processing if there is no data

    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            if not assessments_grading.strip():
                p_element = paragraph._element
                p_element.getparent().remove(p_element)
                return  
            # Preserve original paragraph formatting
            paragraph_format = paragraph.paragraph_format  

            # Insert title above the placeholder
            title_paragraph = paragraph.insert_paragraph_before("")
            title_paragraph.style = paragraph.style  # Keep the same style
            title_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  # Copy indentation
            title_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  # Copy first-line indent

            title_run = title_paragraph.add_run(title)
            title_run.bold = True
            title_run.font.size = Pt(11)

            # Preserve the {AssessmentsGrading} content while replacing the placeholder
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, value)

            # Remove the paragraph if `<REMOVE>` is present
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)

            return  # Stop after processing the first occurrence

def format_objectives(doc, placeholder, objectives):
    """Replaces {Objectives} with formatted course objectives while adding a title."""
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            p_element = paragraph._element
            parent = p_element.getparent()
            
            if not objectives:
                parent.remove(p_element)
                return 

            paragraph.text = ""  # Clear placeholder while keeping position

            # ✅ Insert Title Above Placeholder
            title_paragraph = paragraph.insert_paragraph_before()
            title_paragraph.style = paragraph.style
            title_paragraph.paragraph_format.space_before = Pt(14)  
            title_paragraph.paragraph_format.space_after = Pt(12)
            title_paragraph.paragraph_format.left_indent = paragraph.paragraph_format.left_indent
            title_paragraph.paragraph_format.first_line_indent = paragraph.paragraph_format.first_line_indent

            title_run = title_paragraph.add_run("COURSE OBJECTIVES")
            title_run.bold = True
            title_run.font.size = Pt(11)

            # ✅ Insert formatted Objectives
            for i, objective in enumerate(objectives, 1):
                obj_paragraph = paragraph.insert_paragraph_before()
                obj_paragraph.style = paragraph.style

                # **🔥 Apply Hanging Indentation using Word XML**
                pPr = obj_paragraph._element.get_or_add_pPr()
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "950")
                ind.set(qn("w:hanging"), "740")
                pPr.append(ind)

                # First line: Numbering (bold)
                obj_run = obj_paragraph.add_run(f"{i}.   ")
                obj_run.bold = True  
                obj_run.font.size = Pt(11)

                # Content (normal font)
                content_run = obj_paragraph.add_run(objective)
                content_run.bold = False
                content_run.font.size = Pt(11)

            return

def format_textbooks(doc, placeholder, textbooks):
    """Replaces {Textbooks} with formatted textbook list while adding a title."""
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            p_element = paragraph._element
            parent = p_element.getparent()

            if not textbooks:
                parent.remove(p_element)
                return 

            paragraph.text = ""

            # ✅ Insert Title Above Placeholder
            title_paragraph = paragraph.insert_paragraph_before()
            title_paragraph.style = paragraph.style
            title_paragraph.paragraph_format.space_before = Pt(14)  
            title_paragraph.paragraph_format.space_after = Pt(12)

            title_run = title_paragraph.add_run("TEXTBOOKS")
            title_run.bold = True
            title_run.font.size = Pt(11)

            # ✅ Insert formatted Textbooks
            for i, textbook in enumerate(textbooks, 1):
                tb_paragraph = paragraph.insert_paragraph_before()
                tb_paragraph.style = paragraph.style

                # **🔥 Apply Hanging Indentation using Word XML**
                pPr = tb_paragraph._element.get_or_add_pPr()
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "950")
                ind.set(qn("w:hanging"), "740")
                pPr.append(ind)

                # First line: Numbering (bold)
                tb_run = tb_paragraph.add_run(f"{i}.   ")
                tb_run.bold = True  
                tb_run.font.size = Pt(11)

                # Content (normal font)
                content_run = tb_paragraph.add_run(textbook)
                content_run.bold = False
                content_run.font.size = Pt(11)

            return

def format_references(doc, placeholder, references):
    """Replaces {References} with formatted reference list while adding a title."""
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            p_element = paragraph._element
            parent = p_element.getparent()

            if not references:
                parent.remove(p_element)
                return 

            paragraph.text = ""

            # ✅ Insert Title Above Placeholder
            title_paragraph = paragraph.insert_paragraph_before()
            title_paragraph.style = paragraph.style
            title_paragraph.paragraph_format.space_before = Pt(14)  
            title_paragraph.paragraph_format.space_after = Pt(12)

            title_run = title_paragraph.add_run("REFERENCES")
            title_run.bold = True
            title_run.font.size = Pt(11)

            # ✅ Insert formatted References
            for i, reference in enumerate(references, 1):
                ref_paragraph = paragraph.insert_paragraph_before()
                ref_paragraph.style = paragraph.style

                # **🔥 Apply Hanging Indentation using Word XML**
                pPr = ref_paragraph._element.get_or_add_pPr()
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "950")
                ind.set(qn("w:hanging"), "740")
                pPr.append(ind)

                # First line: Numbering (bold)
                ref_run = ref_paragraph.add_run(f"{i}.   ")
                ref_run.bold = True  
                ref_run.font.size = Pt(11)

                # Content (normal font)
                content_run = ref_paragraph.add_run(reference)
                content_run.bold = False
                content_run.font.size = Pt(11)

            return

def format_course_outcomes(doc, placeholder, course_outcomes):
    """Replaces {CourseOutcomes} with formatted course outcomes while adding a title."""
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            p_element = paragraph._element
            parent = p_element.getparent()
            
            if not course_outcomes:
                parent.remove(p_element)
                return  

            paragraph.text = ""  # Clear placeholder while keeping position

            # Preserve paragraph formatting
            paragraph_format = paragraph.paragraph_format
            
            # ✅ Insert Title Above Placeholder
            title_paragraph = paragraph.insert_paragraph_before()
            title_paragraph.style = paragraph.style
            title_paragraph.paragraph_format.space_before = Pt(14)  
            title_paragraph.paragraph_format.space_after = Pt(12)  
            title_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  
            title_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  

            title_run = title_paragraph.add_run("COURSE OUTCOMES")
            title_run.bold = True
            title_run.font.size = Pt(11)

            # ✅ Insert formatted COs **without adding an empty paragraph**
            for i, outcome in enumerate(course_outcomes, 1):
                co_paragraph = paragraph.insert_paragraph_before()  # ✅ Fix: No empty string inserted
                co_paragraph.style = paragraph.style

                # **🔥 Apply Hanging Indentation using Word XML**
                pPr = co_paragraph._element.get_or_add_pPr()
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "950")  
                ind.set(qn("w:hanging"), "740")  
                pPr.append(ind)

                # First line: CO label (bold)
                co_run = co_paragraph.add_run(f"CO{i}      ") 
                co_run.bold = True  
                co_run.font.size = Pt(11)

                # Content (normal font)
                content_run = co_paragraph.add_run(outcome)
                content_run.bold = False
                content_run.font.size = Pt(11)

            return  
        
def replace_units_with_formatting(doc, units):
    """Finds {Units} placeholder and inserts formatted units with proper indentation & normal content formatting."""
    for paragraph in doc.paragraphs:
        if "{Units}" in paragraph.text:
            p_element = paragraph._element  # Store reference to remove placeholder
            parent = p_element.getparent()  # Get parent XML element
            paragraph_style = paragraph.style  # Store the style of the original paragraph
            # Create a new paragraph at the same location before removing {Units}
            new_paragraph = paragraph.insert_paragraph_before("")
            new_paragraph.style = paragraph_style  # Apply the same style as the placeholder
            parent.remove(p_element)  # Remove {Units} placeholder

            for i, (unit_title, unit_content, unit_periods) in enumerate(units, 1):
                # Insert Unit Title (Bold) with correct style
                title_paragraph = new_paragraph.insert_paragraph_before("")
                title_paragraph.style = paragraph_style  # Apply same style
                title_run = title_paragraph.add_run(f"UNIT {i}: {unit_title} (No. of Periods: {unit_periods})")
                title_paragraph.paragraph_format.space_before = Pt(12)  # 🔥 Space before title
                title_paragraph.paragraph_format.space_after = Pt(10)  
                title_run.bold = True
                title_run.font.size = Pt(11)

                # Insert Unit Content (Normal) with correct indentation
                content_paragraph = new_paragraph.insert_paragraph_before("")
                content_paragraph.style = paragraph_style  # Apply same style  
                content_run = content_paragraph.add_run(f"{unit_content}")
                content_run.bold = False  # 🔥 Fix: Ensure normal text
                content_run.font.size = Pt(11)

            break 

def replace_practical_periods(doc, practical_periods):
    """Replaces {PracticalPeriods} with a single-line format while maintaining formatting."""
    placeholder = "{PracticalPeriods}"
    value = f"PRACTICAL PERIODS: {practical_periods}" if practical_periods else "<REMOVE>"

    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            # ✅ Replace the placeholder with formatted single-line text
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, value)

            # ✅ Remove placeholder if there is no practical period
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)

            return  # ✅ Stop after first occurrence
        
def replace_total_periods(doc, units):
    """Calculates total periods from all units and replaces {TotalPeriods} in a single line."""
    placeholder = "{TotalPeriods}"

    # ✅ Calculate total periods by summing unit periods
    total_periods = sum(unit[2] for unit in units) if units else 0
    value = f"TOTAL NUMBER OF PERIODS: {total_periods}" if total_periods > 0 else "<REMOVE>"

    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            # ✅ Combine all runs text (handles cases where {TotalPeriods} is split across runs)
            full_text = "".join(run.text for run in paragraph.runs)
            updated_text = full_text.replace(placeholder, value)

            # ✅ Clear existing runs before inserting updated text
            for run in paragraph.runs:
                run.text = ""

            # ✅ Set the new text in the first run
            if paragraph.runs:
                paragraph.runs[0].text = updated_text

            # ✅ Remove paragraph if `<REMOVE>` is present
            if "<REMOVE>" in paragraph.text:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)

            return  # ✅ Stop after first occurrence
        
def replace_list_of_experiments(doc, placeholder, experiments):
    """
    Replaces {ListOfExperiments} with a properly formatted numbered list while keeping formatting.
    - `placeholder`: The placeholder text to replace (e.g., {ListOfExperiments})
    - `experiments`: The list of experiments to insert
    """
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            parent = paragraph._element.getparent()  # Get parent XML element
            paragraph.text = ""  # Clear placeholder but keep paragraph position
            if not experiments:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)
                return 
            # Preserve the document’s original paragraph format
            paragraph_format = paragraph.paragraph_format
            
            # ✅ Insert Title: "PRACTICAL EXERCISES"
            title_paragraph = paragraph.insert_paragraph_before("")
            title_paragraph.style = paragraph.style  
            title_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  
            title_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  

            title_run = title_paragraph.add_run("PRACTICAL EXERCISES")
            title_run.bold = True
            title_run.font.size = Pt(11)

            # ✅ Insert formatted list of experiments
            for index, experiment in enumerate(experiments, 1):
                exp_paragraph = paragraph.insert_paragraph_before("")
                exp_paragraph.style = paragraph.style  
                exp_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  
                exp_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  

                # Add numbering (bold)
                exp_run = exp_paragraph.add_run(f"{index}. ")
                exp_run.bold = True  

                # Add the actual content
                content_run = exp_paragraph.add_run(experiment.strip())  
                content_run.bold = False  
                content_run.font.size = Pt(11)

            return  # ✅ Stop after first occurrence


def replace_general_placeholders(doc, placeholders):
    """
    Replaces placeholders related to Semester, Course Name, Course Code, 
    Course Description, Prerequisites, Course Format, Assessments & Grading 
    in both paragraphs and tables while maintaining formatting.
    """
    
    # Iterate over all paragraphs
    for paragraph in doc.paragraphs:
        replace_placeholders_in_paragraph(paragraph, placeholders)

    # Iterate over all tables (tables contain rows → cells → paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_placeholders_in_paragraph(paragraph, placeholders)


def replace_placeholders_in_paragraph(paragraph, placeholders):
    """
    Replaces placeholders inside a paragraph while keeping the formatting intact.
    If `<REMOVE>` is found, the paragraph is deleted.
    """
    if paragraph.runs:  # Ensure the paragraph contains text
        full_text = ''.join(run.text for run in paragraph.runs)  # Merge runs

        for placeholder, value in placeholders.items():
            if placeholder in full_text:
                full_text = full_text.replace(placeholder, value)

        # Remove the paragraph if it contains `<REMOVE>`
        if "<REMOVE>" in full_text:
            p_element = paragraph._element
            p_element.getparent().remove(p_element)
            return

        # Apply the modified text while keeping formatting
        for i, run in enumerate(paragraph.runs):
            if i == 0:
                run.text = full_text  # Set new text in the first run
            else:
                run.text = ""  # Clear other runs




def replace_list_section(doc, placeholder, items, title=""):
    """
    Replaces a placeholder with a properly formatted numbered list while keeping the content at the correct position.
    - `placeholder`: The placeholder text to replace (e.g., `{Objectives}`)
    - `items`: The list of items to insert
    - `title`: The title of the section (optional)
    """
    for i, paragraph in enumerate(doc.paragraphs):
        if placeholder in paragraph.text:
            parent = paragraph._element.getparent()  # Get parent XML element
            paragraph.text = ""  # Clear placeholder but keep paragraph position
            if not items:
                p_element = paragraph._element
                p_element.getparent().remove(p_element)
                return 
            # Preserve the document’s original paragraph format
            paragraph_format = paragraph.paragraph_format
            
            # Insert title (if provided)
            if title:
                title_paragraph = paragraph.insert_paragraph_before()
                title_paragraph.style = paragraph.style
                title_paragraph.paragraph_format.space_before = Pt(12)  # 🔥 Space before title
                title_paragraph.paragraph_format.space_after = Pt(6)    # Keep same style
                title_run = title_paragraph.add_run(title)
                title_run.bold = True
                title_run.font.size = Pt(11)

            # Insert list items directly after the placeholder
            for index, item in enumerate(items, 1):
                item_paragraph = paragraph.insert_paragraph_before("")
                item_paragraph.style = paragraph.style  # Keep same style
                item_paragraph.paragraph_format.left_indent = paragraph_format.left_indent  # Maintain document indentation
                item_paragraph.paragraph_format.first_line_indent = paragraph_format.first_line_indent  # Keep first-line formatting
                
                # Manually add numbering (bold)
                item_run = item_paragraph.add_run(f"{index}.    ")
                item_run.bold = True  

                # Add the actual content
                content_run = item_paragraph.add_run(item.strip())  
                content_run.bold = False  
                content_run.font.size = Pt(11)

                # **🔥 Preserve Indentation & Margins using Word XML**
                pPr = item_paragraph._element.get_or_add_pPr()
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "645")  # Use document's original left indentation
                ind.set(qn("w:hanging"), "365")  # Hanging indent for text (0.25 inch)
                pPr.append(ind)

            return

def clean_text(value):
    """Ensures the input is a string before processing."""
    return str(value).replace("\xa0", " ").strip() if value else ""

def clean_int(value, default=0):
    """Ensures the input is an integer, defaults to 0 if conversion fails."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def clean_pdf_text(text):
    """Cleans extracted text while recognizing manual 'Enter' presses inside lists."""
    if not text:
        return ""

    # ✅ Trim leading/trailing spaces
    text = text.strip()

    # ✅ Fix multiple spaces and tabs
    text = re.sub(r'\s+', ' ', text)

    # ✅ Ensure correct spacing after list numbers (Fixes "1.Text" → "1. Text")
    text = re.sub(r'(\d+)\.(\S)', r'\1. \2', text)

    # ✅ Ensure proper spacing for bullet points ("-Text" → "- Text" & "•Text" → "• Text")
    text = re.sub(r'(-|•)\s*(\S)', r'\1 \2', text)

    # ✅ Preserve manual line breaks inside list items
    text = re.sub(r'(\d+\..*?)\n(\s+)(\S)', r'\1 \3', text)  # Joins lines within the same numbered item
    text = re.sub(r'(-|•)\s*(.*?)\n(\s+)(\S)', r'\1 \2 \4', text)  # Joins lines within bullet points

    return text



def process_form_data(form):
    """Processes form data and converts it into the required context format."""
    try:
        context = {
            "document_version": [],
            "category_table": [],
            "credits_table": [],
            "total_credits": clean_int(form.get("total_credits", 0)),
            "dept_Code": clean_text(form.get("dept_Code", "")),
            **{key: [] for key in ["BSC", "ESC", "PCC", "ELECTIVE", "OEC", "MC", "EEC", "HSMC"]},
            **{f"course_table{i}": [] for i in range(1, 9)}
        }

        # Process Document Version
        i = 1
        while f"document_version_version_{i}" in form:
            context["document_version"].append({
                "version": clean_text(form.get(f"document_version_version_{i}", "")),
                "date": clean_text(form.get(f"document_version_date_{i}", "")),
                "author": clean_text(form.get(f"document_version_author_{i}", "")),
                "updates": clean_text(form.get(f"document_version_updates_{i}", "")),
                "approved_by": clean_text(form.get(f"document_version_approved_{i}", ""))
            })
            i += 1
        
        context["structure_total_credits"] = sum(item["credits"] for item in context["category_table"]) 
        context["regulation"] = clean_text(form.get("reg", ""))
        context["dept"] = clean_text(form.get(f"dept", ""))
        # Process Category Table (Structure of Program)
        i = 1
        while f"structure_of_program_category_{i}" in form:
            context["category_table"].append({
                "s_no": clean_int(form.get(f"structure_of_program_sno_{i}", i)),
                "category": clean_text(form.get(f"structure_of_program_category_{i}", "")),
                "credits": clean_int(form.get(f"structure_of_program_credits_{i}", "0")),
            })
            i += 1

        # Process Credits Table (Definition of Credit)
        i = 1
        while f"definition_of_credits_l_{i}" in form:
            context["credits_table"].append({
                "l": clean_text(form.get(f"definition_of_credits_l_{i}", "")),
                "t": clean_text(form.get(f"definition_of_credits_t_{i}", "")),
                "p": clean_text(form.get(f"definition_of_credits_p_{i}", "")),
            })
            i += 1

        j = 1
        for key in ["BSC", "ESC", "PCC", "ELECTIVE", "OEC", "MC", "EEC", "HSMC"]:
            
            context[f"{key}_total_credits"] = clean_text(form.get(f"{key}_total_credits", ""))

        # Process Courses (BSC, ESC, PCC, ELECTIVE, etc.)
        for key in ["BSC", "ESC", "PCC", "ELECTIVE", "OEC", "MC", "EEC", "HSMC"]:
            i = 1
            while f"{key}_title_{i}" in form:
                context[key].append({
                    "s_no": clean_int(form.get(f"{key}_sno_{i}", i)),
                    "title": clean_text(form.get(f"{key}_title_{i}", "")),
                    "sem": clean_text(form.get(f"{key}_semester_{i}", "")),
                    "ltpc": clean_text(form.get(f"{key}_ltpc_{i}", ""))
                })
                i += 1


        for table_key in [f"course_table{i}" for i in range(1, 9)]:           
            context[f"{table_key}_total_credits"] = clean_text(form.get(f"{table_key}_total_credits", ""))
           

        # Process Course Tables (course_table1 to course_table8)
        for table_key in [f"course_table{i}" for i in range(1, 9)]:
            i = 1
            while f"{table_key}_course_code_{i}" in form:
                context[table_key].append({
                    "s_no": clean_int(form.get(f"{table_key}_sno_{i}", i)),
                    "type": clean_text(form.get(f"{table_key}_type_{i}", "")),
                    "course_code": clean_text(form.get(f"{table_key}_course_code_{i}", "")),
                    "course_title": clean_text(form.get(f"{table_key}_course_title_{i}", "")),
                    "ltpc": clean_text(form.get(f"{table_key}_ltpc_{i}", "")),
                })
                i += 1

        return context
    except Exception as e:
        logging.error(f"Error in processing form data: {e}")
        raise e  # Raise the error for debugging

def generate_docx(context):
    """Generates the Word document using docxtpl and returns it as an in-memory file."""
    template_path = "curriculum.docx"
    
    if not os.path.exists(template_path):
        logging.error("Template file 'curriculum.docx' not found.")
        raise FileNotFoundError("Template file 'curriculum.docx' not found. Please upload the correct template.")
    
    try:
        doc = DocxTemplate(template_path)
        doc.render(context)
    except Exception as e:
        logging.error(f"Template rendering error: {e}")
        raise e  # Re-raise the error for debugging

    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)

    return doc_io





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create principal account if it doesn't exist
        if not User.query.filter_by(role='principal').first():
            principal = User(
                username='principal',
                password_hash=generate_password_hash('admin123'),
                email='principal@school.com',
                role='principal'
            )
            db.session.add(principal)
            db.session.commit()
    app.run(debug=True)
