import json
from app.models import db, Project, Attachment, User, ProjectStatus
from app.services.user_services import get_user_by_email
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

def create_project(name, description, deadline, status, owner_email, collaborator_emails, attachments, notes):
    try:
        owner = get_user_by_email(owner_email)
        if not owner:
            raise ValueError(f"Owner with email {owner_email} not found")
        
        collaborators = []
        if collaborator_emails:
            # Handle the case where collaborators might be sent as a single string '[]'
            if isinstance(collaborator_emails, list) and len(collaborator_emails) == 1 and collaborator_emails[0] == '[]':
                collaborator_emails = []

            for email in collaborator_emails:
                user = get_user_by_email(email)
                if user:
                    collaborators.append(user)

        project = Project(
            name=name,
            description=description,
            deadline=deadline,
            status=status,
            owner=owner,
            collaborators=collaborators,
            notes=notes
        )

        if attachments:
            for file in attachments:
                attachment = Attachment(filename=file.filename, content=file.read(), project=project)
                db.session.add(attachment)

        db.session.add(project)
        db.session.commit()
        return project
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while creating project: {e}")

def get_all_projects():
    try:
        projects = Project.query.all()
        return projects
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching projects: {e}")

# --- THIS IS THE MISSING FUNCTION ---
def get_project_by_id(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")
        return project
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project {project_id}: {e}")
# ------------------------------------

def update_project(project_id, data, new_files):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # Update simple fields
        if "name" in data: project.name = data["name"]
        if "description" in data: project.description = data["description"]
        if "notes" in data: project.notes = data["notes"]
        if "status" in data: project.status = ProjectStatus(data["status"])
        if "deadline" in data and data["deadline"]:
            project.deadline = datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")).date()

        # Update owner
        if "owner" in data:
            owner = User.query.filter_by(email=data["owner"]).first()
            if owner: project.owner = owner

        # Update collaborators
        if "collaborators" in data:
            collaborators_emails = data.getlist("collaborators")
            project.collaborators.clear()
            for email in collaborators_emails:
                user = User.query.filter_by(email=email).first()
                if user: project.collaborators.append(user)

        # Update attachments
        if "existing_attachments" in data:
            existing_attachments = json.loads(data["existing_attachments"])
            existing_ids = [att.get("id") for att in existing_attachments]
            
            for att in project.attachments[:]:
                if att.id not in existing_ids:
                    db.session.delete(att)

        if new_files:
            for file in new_files:
                attachment = Attachment(
                    filename=file.filename,
                    content=file.read(),
                    project=project
                )
                db.session.add(attachment)

        db.session.commit()
        return project
    
    except Exception as e:
        db.session.rollback()
        raise e