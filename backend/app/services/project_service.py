# backend/app/services/project_service.py (Revised)
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import current_app
from .. import db
from ..models import Project, Attachment, User

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_project_and_handle_upload(project_data: dict, file: FileStorage, manager_id: int):
    """
    Creates a new Project record and saves the associated PDF attachment.
    """
    
    # 1. Prepare Data
    deadline = datetime.strptime(project_data['deadline'], '%Y-%m-%d').date()
    
    # 2. Create Project
    new_project = Project(
        name=project_data['name'],
        description=project_data.get('description'),
        deadline=deadline,
        status=project_data['status'],
        manager_id=manager_id,
    )

    # 3. Handle Collaborators
    if project_data.get('collaborators'):
        collab_names = [c.strip() for c in project_data['collaborators'].split(',') if c.strip()]
        collaborators = db.session.execute(
            db.select(User).filter(User.username.in_(collab_names))
        ).scalars().all()
        new_project.collaborators.extend(collaborators)

    db.session.add(new_project)
    db.session.flush()

    # 4. Handle File Upload (if file exists and is valid PDF)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        project_folder_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, str(new_project.id))
        if not os.path.exists(project_folder_path):
            os.makedirs(project_folder_path)
            
        storage_path = os.path.join(project_folder_path, filename)
        file.save(storage_path)
        
        # Save attachment record
        attachment_record = Attachment(
            original_filename=file.filename,
            storage_path=storage_path,
            project_id=new_project.id,
            file_type='application/pdf'
        )
        db.session.add(attachment_record)
        
    elif file:
        db.session.rollback()
        raise ValueError("Invalid file type. Only PDF files are allowed.")
        
    db.session.commit()
    
    return new_project

def get_projects_list():
    """Retrieves a list of all projects."""
    
    projects = db.session.execute(
        db.select(Project)
        .order_by(Project.created_at.desc())
    ).scalars().all()

    return [{
        "id": p.id,
        "name": p.name,
        "status": p.status,
        "deadline": p.deadline.isoformat() if p.deadline else None,
    } for p in projects]