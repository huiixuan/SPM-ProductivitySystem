import json
from app.models import db, Task, Attachment, User, Project
from app.services.user_services import get_user_by_email
from app.models import TaskStatus
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.services.notification_services import (
    create_notifications_for_task, 
    remove_notifications_for_task, 
    update_notifications_for_task,
    create_comment_notification,
    create_task_update_notification,
    create_task_assignment_notification
)
from flask_jwt_extended import get_jwt_identity

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
        
        create_notifications_for_task(task)
        
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))
        
        if current_user and current_user.id != owner.id:
            create_task_assignment_notification(task, current_user, owner)

        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError("Database error while creating task")

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
        user = User.query.get(owner_id)
        if not user:
            return []
            
        tasks = Task.query.filter(
            (Task.owner_id == owner_id) | 
            (Task.collaborators.any(id=owner_id))
        ).all()
        
        return tasks
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving tasks of user {owner_id}: {e}")
    
def get_project_tasks(project_id):
    try:
        return Task.query.filter_by(project_id=project_id).all()
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving tasks of project {project_id}: {e}")

def get_unassigned_tasks():
    try:
        tasks = Task.query.filter(Task.project_id == None).all()
        return tasks
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching unassigned tasks: {e}")

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
        
        old_values = {
            'status': task.status,
            'duedate': task.duedate,
            'priority': task.priority,
            'owner_id': task.owner_id
        }
        
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
            
            if owner.id != task.owner_id:
                user_id = get_jwt_identity()  
                current_user = User.query.get(int(user_id))
                create_task_assignment_notification(task, current_user, owner)
            
            task.owner = owner

        collaborators = data.get("collaborators")
        if collaborators:
            if isinstance(collaborators, str):
                try:
                    collaborators = json.loads(collaborators)
                except json.JSONDecodeError:
                    collaborators = []
            
            current_collaborator_emails = [c.email for c in task.collaborators]
            new_collaborators = [c for c in collaborators if c not in current_collaborator_emails]
            
            task.collaborators.clear()
            if collaborators:
                for email in collaborators:
                    user = User.query.filter_by(email=email).first()
                    if user:
                        task.collaborators.append(user)
                        
                        if email in new_collaborators:
                            user_id = get_jwt_identity()  
                            current_user = User.query.get(int(user_id))
                            create_task_assignment_notification(task, current_user, user)

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

        from sqlalchemy.orm.attributes import get_history
        
        updated_fields = []
        user_id = get_jwt_identity()  
        current_user = User.query.get(int(user_id))
        updated_by = current_user
        
        field_mapping = {
            'status': ('status', lambda x: x.value if x else None),
            'duedate': ('duedate', lambda x: x.isoformat() if x else None),
            'priority': ('priority', lambda x: x),
            'owner_id': ('assignee', lambda x: User.query.get(x).email if User.query.get(x) else None)
        }
        
        for field, (display_name, formatter) in field_mapping.items():
            history = get_history(task, field)
            if history.has_changes():
                old_value = formatter(history.deleted[0]) if history.deleted else None
                new_value = formatter(history.added[0]) if history.added else None
                
                if old_value != new_value:
                    updated_fields.append({
                        "field": display_name,
                        "old_value": str(old_value) if old_value is not None else "None",
                        "new_value": str(new_value) if new_value is not None else "None"
                    })
        
        if updated_fields and updated_by:
            create_task_update_notification(task, updated_by, updated_fields)

        if 'duedate' in [change.get('field') for change in updated_fields]:
            update_notifications_for_task(task)

        return task
    
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        db.session.rollback()
        raise RuntimeError(f"Database error while updating task {task_id}: {e}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        db.session.rollback()
        raise