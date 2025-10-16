import json
from app.models import db, Task, Attachment, User
from app.services.user_services import get_user_by_email
from app.models import TaskStatus
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

def create_task(title, description, duedate, status, owner_email, collaborator_emails, attachments, notes, priority):
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

        if attachments:
            for file in attachments:
                attachment = Attachment(filename=file.filename, content=file.read(), task=task)
                db.session.add(attachment)

        db.session.add(task)
        db.session.commit()

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
    
def get_all_tasks(owner_id):
    try:
        return Task.query.filter_by(owner_id=owner_id).all()
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving tasks of user {owner_id}: {e}")
    
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
        return task
    
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        db.session.rollback()
        raise RuntimeError(f"Database error while updating task {task_id}: {e}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        db.session.rollback()
        raise