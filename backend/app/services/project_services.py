import json
# --- Imports are correct ---
from app.models import db, Project, Attachment, User, ProjectStatus, Task, TaskStatus
from app.services.user_services import get_user_by_email
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func 
from datetime import datetime
from app.services.email_services import (
    send_project_creation_email_notification,
    send_project_update_email_notification,
    send_project_collaborator_added_email_notification
)

# ... (all other functions: create_project, get_all_projects, etc. stay the same) ...
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
        
        # Get current user for email notification
        from flask_jwt_extended import get_jwt_identity
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        # Send project creation email notification
        if current_user:
            send_project_creation_email_notification(project, current_user)
        
        return project
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while creating project: {e}")

def get_all_projects(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return []
        projects = Project.query.filter(
            (Project.owner_id == user.id) | (Project.collaborators.contains(user))
        ).distinct().all()
        return projects
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching projects: {e}")


def get_project_by_id(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")
        return project
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project {project_id}: {e}")

def get_project_users(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")
        users = [project.owner] + project.collaborators
        users_data = [
            {"id": user.id, "role": user.role.value, "name": user.name, "email": user.email}
            for user in users
        ]
        return users_data
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project {project_id}: {e}")

def update_project(project_id, data, new_files, collaborator_emails=None):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # Track changes for notification
        changes = {}
        old_collaborators = set(project.collaborators)
        
        # Update simple fields
        if "name" in data and data["name"] != project.name:
            changes["Name"] = (project.name, data["name"])
            project.name = data["name"]
            
        if "description" in data and data["description"] != project.description:
            changes["Description"] = (project.description, data["description"])
            project.description = data["description"]
            
        if "notes" in data and data["notes"] != project.notes:
            changes["Notes"] = (project.notes, data["notes"])
            project.notes = data["notes"]
            
        if "status" in data and data["status"] != project.status.value:
            changes["Status"] = (project.status.value, data["status"])
            project.status = ProjectStatus(data["status"])
            
        if "deadline" in data and data["deadline"]:
            new_deadline = datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")).date()
            if project.deadline != new_deadline:
                changes["Deadline"] = (
                    project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set',
                    new_deadline.strftime('%Y-%m-%d')
                )
                project.deadline = new_deadline

        # Update owner
        new_owner = None
        if "owner" in data:
            owner = User.query.filter_by(email=data["owner"]).first()
            if owner and owner.id != project.owner_id:
                changes["Owner"] = (project.owner.email, owner.email)
                project.owner = owner
                new_owner = owner

        # Track new collaborators
        new_collaborators = []
        if collaborator_emails is not None:
            current_emails = {user.email for user in project.collaborators}
            new_emails = set(collaborator_emails)
            
            # Find added collaborators
            added_emails = new_emails - current_emails
            for email in added_emails:
                user = User.query.filter_by(email=email).first()
                if user:
                    new_collaborators.append(user)
            
            # Update collaborators
            project.collaborators.clear()
            for email in collaborator_emails:
                user = User.query.filter_by(email=email).first()
                if user:
                    project.collaborators.append(user)

        # Update attachments
        if "existing_attachments" in data:
            existing_attachments = json.loads(data["existing_attachments"])
            existing_ids = [att.get("id") for att in existing_attachments]
            
            for att in project.attachments[:]:
                if att.id not in existing_ids:
                    db.session.delete(att)

        if new_files:
            for file in new_files:
                attachment = Attachment(filename=file.filename, content=file.read(), project=project)
                db.session.add(attachment)

        db.session.commit()
        
        # Get current user for email notification
        from flask_jwt_extended import get_jwt_identity
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        # Send email notifications
        if current_user:
            # Send general project update notification if there were changes
            if changes:
                send_project_update_email_notification(project, current_user, changes)
            
            # Send specific notification for new collaborators
            if new_collaborators:
                send_project_collaborator_added_email_notification(project, current_user, new_collaborators)
        
        return project
    
    except Exception as e:
        db.session.rollback()
        raise e

# ------------------------------------
# THIS IS THE FUNCTION THE SERVER CAN'T FIND
# ------------------------------------
def get_project_report_data(project_id, user_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        user = User.query.get(user_id)
        if not user:
            raise PermissionError("User not found.")
        
        if user.id != project.owner_id and user not in project.collaborators:
            raise PermissionError("You do not have access to generate reports for this project.")
        
        # --- Task Counting ---
        status_counts_query = db.session.query(
            Task.status, 
            func.count(Task.id)
        ).filter(
            Task.project_id == project_id
        ).group_by(
            Task.status
        ).all()

        # 1. Initialize a dictionary with ALL possible statuses from your enum
        report_data = {status.value: 0 for status in TaskStatus}

        # 2. Overwrite the 0s with the actual counts from the query
        for status_enum, count in status_counts_query:
            report_data[status_enum.value] = count
        
        # 3. Return the dictionary as-is.
        return report_data

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while generating report data: {e}")