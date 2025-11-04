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
                # FIX: Only set project_id, task_id remains NULL for project attachments
                attachment = Attachment(
                    filename=file.filename, 
                    content=file.read(), 
                    project=project  # This sets project_id automatically
                )
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
        changes = []
        old_collaborators = set(project.collaborators)
        
        print(f"DEBUG: Starting project update for: {project.name}")
        print(f"DEBUG: Received data: {data}")
        print(f"DEBUG: New files: {[f.filename for f in new_files]}")

        # Update simple fields and track changes
        if "name" in data and data["name"] != project.name:
            changes.append({
                "field": "name",
                "old_value": project.name,
                "new_value": data["name"]
            })
            project.name = data["name"]
            print(f"DEBUG: Name changed: {project.name}")
            
        if "description" in data and data["description"] != project.description:
            changes.append({
                "field": "description",
                "old_value": project.description,
                "new_value": data["description"]
            })
            project.description = data["description"]
            print(f"DEBUG: Description changed")
            
        if "notes" in data and data["notes"] != project.notes:
            changes.append({
                "field": "notes", 
                "old_value": project.notes,
                "new_value": data["notes"]
            })
            project.notes = data["notes"]
            print(f"DEBUG: Notes changed")
            
        if "status" in data and data["status"] != project.status.value:
            changes.append({
                "field": "status",
                "old_value": project.status.value,
                "new_value": data["status"]
            })
            project.status = ProjectStatus(data["status"])
            print(f"DEBUG: Status changed: {data['status']}")
            
        if "deadline" in data and data["deadline"]:
            new_deadline = datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")).date()
            old_deadline_str = project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set'
            new_deadline_str = new_deadline.strftime('%Y-%m-%d')
            
            if project.deadline != new_deadline:
                changes.append({
                    "field": "deadline",
                    "old_value": old_deadline_str,
                    "new_value": new_deadline_str
                })
                project.deadline = new_deadline
                print(f"DEBUG: Deadline changed: {old_deadline_str} -> {new_deadline_str}")

        # Update owner
        new_owner = None
        if "owner" in data:
            owner = User.query.filter_by(email=data["owner"]).first()
            if owner and owner.id != project.owner_id:
                changes.append({
                    "field": "owner",
                    "old_value": project.owner.email,
                    "new_value": owner.email
                })
                project.owner = owner
                new_owner = owner
                print(f"DEBUG: Owner changed: {owner.email}")

        # Track attachment changes
        removed_attachments = []
        
        # Handle existing attachments removal
        if "existing_attachments" in data:
            existing_attachments = data["existing_attachments"]
            if isinstance(existing_attachments, str):
                try:
                    existing_attachments = json.loads(existing_attachments)
                except json.JSONDecodeError:
                    existing_attachments = []
            
            existing_ids = [att.get("id") for att in existing_attachments if att.get("id")]
            print(f"DEBUG: Keeping attachment IDs: {existing_ids}")
            
            # Find removed attachments
            for att in project.attachments[:]:
                if att.id not in existing_ids:
                    removed_attachments.append(att.filename)
                    db.session.delete(att)
                    print(f"DEBUG: Removing attachment: {att.filename}")

        # Add new files
        added_attachments = []
        if new_files:
            for file in new_files:
                if file.filename:  # Only process if filename is not empty
                    # FIX: Only set project_id, task_id remains NULL for project attachments
                    attachment = Attachment(
                        filename=file.filename,
                        content=file.read(),
                        project_id=project.id  # Only set project_id
                    )
                    db.session.add(attachment)
                    added_attachments.append(file.filename)
                    print(f"DEBUG: Adding new attachment: {file.filename}")

        # Add attachment changes to the changes list
        for filename in removed_attachments:
            changes.append({
                "field": "attachment",
                "old_value": filename,
                "new_value": "Removed"
            })
            
        for filename in added_attachments:
            changes.append({
                "field": "attachment",
                "old_value": "None", 
                "new_value": filename
            })

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
            if current_emails != new_emails:
                changes.append({
                    "field": "collaborators",
                    "old_value": ", ".join(current_emails) if current_emails else "None",
                    "new_value": ", ".join(new_emails) if new_emails else "None"
                })
            
            project.collaborators.clear()
            for email in collaborator_emails:
                user = User.query.filter_by(email=email).first()
                if user:
                    project.collaborators.append(user)

        # Update existing attachments (this was causing the error)
        if "existing_attachments" in data:
            existing_attachments = json.loads(data["existing_attachments"])
            existing_ids = [att.get("id") for att in existing_attachments if att.get("id")]
            
            for att in project.attachments[:]:
                if att.id not in existing_ids:
                    db.session.delete(att)

        print(f"DEBUG: Total changes detected: {len(changes)}")
        print(f"DEBUG: Changes: {changes}")

        db.session.commit()
        
        # Get current user for email notification
        from flask_jwt_extended import get_jwt_identity
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        # Send email notifications only if there are changes
        if changes and current_user:
            print(f"DEBUG: Sending project update notifications for {len(changes)} changes")
    
            # Send email notifications
            send_project_update_email_notification(project, current_user, changes)
    
            if new_collaborators:
                send_project_collaborator_added_email_notification(project, current_user, new_collaborators)
        
        return project
    
    except Exception as e:
        print(f"ERROR in update_project: {e}")
        db.session.rollback()
        raise e

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