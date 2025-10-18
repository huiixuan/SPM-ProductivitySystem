import json
from app.models import db, Task, Attachment, User, Project # 1. Import Project
from app.services.user_services import get_user_by_email
from app.models import TaskStatus
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.services import notification_service

# 2. Add project_id as an optional argument
def create_task(title, description, duedate, status, owner_email, collaborator_emails, attachments, notes, priority, project_id=None):
    try:
        owner = get_user_by_email(owner_email)
        if not owner:
            raise ValueError(f"Owner with email {owner_email} not found")
        
        collaborators = []
        if collaborator_emails:
            for email in collaborator_emails:
                user = get_user_by_email(email)
                if user:
                    collaborators.append(user)

        task = Task(title=title, description=description, duedate=duedate, status=status, owner=owner, collaborators=collaborators, notes=notes, priority=priority)

        # 3. If a project_id is provided, find the project and link it
        if project_id:
            project = Project.query.get(project_id)
            if project:
                task.project = project

        if attachments:
            for file in attachments:
                attachment = Attachment(filename=file.filename, content=file.read(), task=task)
                db.session.add(attachment)

        db.session.add(task)
        db.session.commit()
        notification_service.create_notifications_for_task(task)

        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while saving task: {e}")

def get_task(task_id):
    try:
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with task ID {task_id} not found")
        
        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving task {task_id}: {e}")
    
def get_user_tasks(owner_id):
    try:
        return Task.query.filter_by(owner_id=owner_id).all()
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving tasks of user {owner_id}: {e}")
    
def get_project_tasks(project_id):
    try:
        return Task.query.filter_by(project_id=project_id).all()
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving tasks of project {project_id}: {e}")

# 4. Add new function to get tasks not assigned to any project
def get_unassigned_tasks():
    try:
        tasks = Task.query.filter(Task.project_id == None).all()
        return tasks
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching unassigned tasks: {e}")

# 5. Add new function to link an existing task to a project
def link_task_to_project(task_id, project_id):
    try:
        task = Task.query.get(task_id)
        project = Project.query.get(project_id)

        if not task:
            raise ValueError(f"Task with ID {task_id} not found.")
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        task.project = project
        db.session.commit()
        return task
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while linking task {task_id} to project {project_id}: {e}")

def update_task(task_id, data, new_files):
    try:
        print(f"Starting update for task {task_id}")
        print(f"Received data: {data}")
        print(f"Received files: {new_files}")
        
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with task ID {task_id} not found")
        
        task.title = data.get("title", task.title)
        task.description = data.get("description", task.description)

        if duedate := data.get("duedate"):
            try:
                task.duedate = datetime.fromisoformat(duedate.replace('Z', '+00:00'))
            except ValueError as e:
                print(f"Date parsing error: {e}")
                raise ValueError(f"Invalid date format: {duedate}")
            
        if status := data.get("status"):
            try:
                task.status = TaskStatus(status)
            except ValueError:
                raise ValueError(f"Invalid status: {status}")
            
        task.priority = int(data.get("priority", task.priority))
        task.notes = data.get("notes", task.notes)

        if owner_email := data.get("owner"):
            owner = User.query.filter_by(email=owner_email).first()
            if not owner:
                raise ValueError(f"Owner with email {owner_email} not found")
            task.owner = owner

        collaborators = data.get("collaborators")
        if collaborators:
            if isinstance(collaborators, str):
                try:
                    collaborators = json.loads(collaborators)
                except json.JSONDecodeError:
                    collaborators = []
            
            task.collaborators.clear()
            if collaborators:  # Only process if not empty
                for email in collaborators:
                    user = User.query.filter_by(email=email).first()
                    if user:
                        task.collaborators.append(user)


        if "existing_attachments" in data:
            existing_attachments = data["existing_attachments"]
            if isinstance(existing_attachments, str):
                try:
                    existing_attachments = json.loads(existing_attachments)
                except json.JSONDecodeError:
                    existing_attachments = []
            
            existing_ids = [att.get("id") for att in existing_attachments if att.get("id")]
            for att in task.attachments[:]:
                if att.id not in existing_ids:
                    db.session.delete(att)

        if new_files:
            for file in new_files:
                attachment = Attachment(
                    filename=file.filename,
                    content=file.read(),
                    task=task
                )
                db.session.add(attachment)

        db.session.commit()

        try:
            db.session.refresh(task)

            if task.status == TaskStatus.COMPLETED:
                notification_service.remove_notifications_for_task(task)
            else:
                if duedata := data.get("duedate"):
                    try:
                        new_duedate = datetime.fromisoformat(duedate.replace('Z', '+00:00')).date()
                    except ValueError:
                        new_duedate = task.duedate

                    if new_duedate != task.duedate:
                        notification_service.update_notifications_for_task(task)
                else:
                    notification_service.update_notifications_for_task(task)
        except Exception as notif_err:
            print(f"Notification update error: {notif_err}")


        return task
    
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        db.session.rollback()
        raise RuntimeError(f"Database error while updating task {task_id}: {e}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        db.session.rollback()
        raise