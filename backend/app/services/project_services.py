import json
from app.models import db, Project, Attachment, User, ProjectStatus, Task, TaskStatus, RecurrenceType
from app.services.user_services import get_user_by_email
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func 
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.services.email_services import (
    send_project_creation_email_notification,
    send_project_update_email_notification,
    send_project_collaborator_added_email_notification
)

# ... (create_project, get_all_projects, get_project_by_id, get_project_users, update_project functions remain the same) ...
def create_project(name, description, deadline, status, owner_email, collaborator_emails, attachments, notes):
    try:
        owner = get_user_by_email(owner_email)
        if not owner:
            raise ValueError(f"Owner with email {owner_email} not found")
        
        collaborators = []
        if collaborator_emails:
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
        
        # Send notifications
        send_project_creation_email_notification(project)
        for user in collaborators:
            send_project_collaborator_added_email_notification(user.email, project)
            
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

        old_collaborator_emails = {user.email for user in project.collaborators}
        
        if "name" in data: project.name = data["name"]
        if "description" in data: project.description = data["description"]
        if "notes" in data: project.notes = data["notes"]
        if "status" in data: project.status = ProjectStatus(data["status"])
        if "deadline" in data and data["deadline"]:
            project.deadline = datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")).date()
        if "owner" in data:
            owner = User.query.filter_by(email=data["owner"]).first()
            if owner: project.owner = owner

        new_collaborators = []
        if collaborator_emails is not None:
            project.collaborators.clear()
            for email in collaborator_emails:
                user = User.query.filter_by(email=email).first()
                if user:
                    project.collaborators.append(user)
                    if email not in old_collaborator_emails:
                        new_collaborators.append(user)

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
        
        send_project_update_email_notification(project)
        for user in new_collaborators:
            send_project_collaborator_added_email_notification(user.email, project)
        
        return project
    
    except Exception as e:
        print(f"ERROR in update_project: {e}")
        db.session.rollback()
        raise e

# --- HELPER FUNCTION FOR RECURRING TASKS ---
def get_recurring_task_instances(task, start_date, end_date):
    if not task.isRecurring or task.recurrence_type == RecurrenceType.NONE:
        return []
    
    instances = []
    current_date = task.duedate
    
    if not current_date:
        return []

    while current_date < start_date:
        if task.recurrence_type == RecurrenceType.DAILY:
            current_date += timedelta(days=1)
        elif task.recurrence_type == RecurrenceType.WEEKLY:
            current_date += timedelta(weeks=1)
        elif task.recurrence_type == RecurrenceType.MONTHLY:
            current_date += relativedelta(months=1)
        elif task.recurrence_type == RecurrenceType.CUSTOM and task.recurrence_interval:
            current_date += timedelta(days=task.recurrence_interval)
        else:
            break
    
    max_instances = 50
    while current_date <= end_date and len(instances) < max_instances:
        instances.append({
            "title": f"{task.title} (Projected)",
            "duedate": current_date.isoformat(),
            # --- THIS IS THE FIX 1 ---
            "status": "Projected", 
        })
        
        if task.recurrence_type == RecurrenceType.DAILY:
            current_date += timedelta(days=1)
        elif task.recurrence_type == RecurrenceType.WEEKLY:
            current_date += timedelta(weeks=1)
        elif task.recurrence_type == RecurrenceType.MONTHLY:
            current_date += relativedelta(months=1)
        elif task.recurrence_type == RecurrenceType.CUSTOM and task.recurrence_interval:
            current_date += timedelta(days=task.recurrence_interval)
        else:
            break
    
    return instances

# ------------------------------------
# MODIFIED FUNCTION
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
        
        # --- 1. Task Counts (from existing DB tasks) ---
        status_counts_query = db.session.query(
            Task.status, 
            func.count(Task.id)
        ).filter(
            Task.project_id == project_id
        ).group_by(
            Task.status
        ).all()

        task_counts = {status.value: 0 for status in TaskStatus}
        for status_enum, count in status_counts_query:
            task_counts[status_enum.value] = count
        
        # --- 2. Task Schedule (Existing + Projected) ---
        project_tasks = Task.query.filter_by(project_id=project_id).all()
        
        task_schedule = []
        
        start_date = datetime.utcnow().date()
        end_date = start_date + timedelta(days=90) # Project 90 days out

        projected_task_count = 0 # Initialize counter

        for task in project_tasks:
            if task.status != TaskStatus.COMPLETED:
                task_schedule.append({
                    "title": task.title,
                    "duedate": task.duedate.isoformat() if task.duedate else None,
                    "status": task.status.value,
                })

            if task.isRecurring:
                projected_tasks = get_recurring_task_instances(task, start_date, end_date)
                task_schedule.extend(projected_tasks)
                projected_task_count += len(projected_tasks) # Add to counter

        # --- THIS IS THE FIX 2 ---
        # Add the "Projected" count to the task_counts dictionary
        task_counts["Projected"] = projected_task_count

        # --- 3. Return both ---
        return {
            "task_counts": task_counts,
            "task_schedule": task_schedule
        }

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while generating report data: {e}")