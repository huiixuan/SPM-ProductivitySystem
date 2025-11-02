import json
from app.models import db, Task, Attachment, User, Project
from app.services.user_services import get_user_by_email, get_users_info
from app.services.project_services import get_project_users
from app.models import TaskStatus
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.services.notification_services import (
    create_notifications_for_task,
    remove_notifications_for_task,
    update_notifications_for_task,
    create_comment_notification,
    create_task_update_notification,
    create_task_assignment_notification,
)
from flask_jwt_extended import get_jwt_identity
from app.services.email_services import send_task_assignment_email_notification
from app.services.email_services import (
    send_task_creation_email_notification,
    send_task_assignment_email_notification
)

class _NotificationFacade:
    def create_notifications_for_task(self, *args, **kwargs):
        return create_notifications_for_task(*args, **kwargs)

    def remove_notifications_for_task(self, *args, **kwargs):
        return remove_notifications_for_task(*args, **kwargs)

    def update_notifications_for_task(self, *args, **kwargs):
        return update_notifications_for_task(*args, **kwargs)

    def create_comment_notification(self, *args, **kwargs):
        return create_comment_notification(*args, **kwargs)

    def create_task_update_notification(self, *args, **kwargs):
        return create_task_update_notification(*args, **kwargs)

    def create_task_assignment_notification(self, *args, **kwargs):
        return create_task_assignment_notification(*args, **kwargs)


notification_service = _NotificationFacade()

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

        notification_service.create_notifications_for_task(task)

        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))

        # Send email notifications to all involved users
        if current_user:
            print(f"DEBUG: Current user: {current_user.email}")
            print(f"DEBUG: Task owner: {owner.email}")
            print(f"DEBUG: Collaborators: {[c.email for c in collaborators]}")
            
            # Send task creation notification to everyone except the creator
            try:
                send_task_creation_email_notification(task, current_user)
            except Exception as e:
                print(f"DEBUG: Error sending task creation email: {e}")
            
            # Also send individual assignment notifications
            if current_user.id != owner.id:
                try:
                    send_task_assignment_email_notification(task, current_user, owner)
                except Exception as e:
                    print(f"DEBUG: Error sending owner assignment email: {e}")
            
            for collaborator in collaborators:
                if collaborator.id != current_user.id:
                    try:
                        send_task_assignment_email_notification(task, current_user, collaborator)
                    except Exception as e:
                        print(f"DEBUG: Error sending collaborator assignment email to {collaborator.email}: {e}")

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
    
def get_project_users_for_tasks(task_id):
    try:
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with task ID {task_id} not found")
        
        project_id = task.project_id
        if not project_id:
            return get_users_info()
        
        return get_project_users(project_id)
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while retrieving users of project {project_id}: {e}")

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
        
        # Track changes for notifications
        updated_fields = []
        
        # Update fields and track changes
        if "title" in data and data["title"] != task.title:
            task.title = data["title"]
            updated_fields.append({
                "field": "title",
                "old_value": task.title,
                "new_value": data["title"]
            })
        
        if "description" in data and data["description"] != task.description:
            task.description = data["description"]
            updated_fields.append({
                "field": "description", 
                "old_value": task.description,
                "new_value": data["description"]
            })
            
        # Due date change - IMPORTANT: This triggers notifications
        if "duedate" in data and data["duedate"]:
            try:
                new_duedate = datetime.fromisoformat(data["duedate"].replace('Z', '+00:00'))
                if task.duedate != new_duedate:
                    updated_fields.append({
                        "field": "due date",
                        "old_value": task.duedate.strftime('%Y-%m-%d') if task.duedate else "Not set",
                        "new_value": new_duedate.strftime('%Y-%m-%d')
                    })
                    task.duedate = new_duedate
            except ValueError as e:
                print(f"Date parsing error: {e}")
                raise ValueError(f"Invalid date format: {data['duedate']}")
        
        # Status change
        if "status" in data and data["status"]:
            try:
                new_status = TaskStatus(data["status"])
                if task.status != new_status:
                    updated_fields.append({
                        "field": "status",
                        "old_value": task.status.value,
                        "new_value": new_status.value
                    })
                    task.status = new_status
            except ValueError:
                raise ValueError(f"Invalid status: {data['status']}")
        
        # Priority change
        if "priority" in data:
            new_priority = int(data["priority"])
            if task.priority != new_priority:
                updated_fields.append({
                    "field": "priority",
                    "old_value": str(task.priority),
                    "new_value": str(new_priority)
                })
                task.priority = new_priority
        
        # Notes change
        if "notes" in data and data["notes"] != task.notes:
            task.notes = data["notes"]
            updated_fields.append({
                "field": "notes",
                "old_value": task.notes,
                "new_value": data["notes"]
            })

        # Owner change
        if "owner" in data:
            owner = User.query.filter_by(email=data["owner"]).first()
            if not owner:
                raise ValueError(f"Owner with email {data['owner']} not found")
            
            if owner.id != task.owner_id:
                updated_fields.append({
                    "field": "assignee",
                    "old_value": task.owner.email,
                    "new_value": owner.email
                })
                
                user_id = get_jwt_identity()  
                current_user = User.query.get(int(user_id))
                create_task_assignment_notification(task, current_user, owner)
                # Add email notification for assignment change
                from app.services.email_services import send_task_assignment_email_notification
                send_task_assignment_email_notification(task, current_user, owner)
                
                task.owner = owner

        # Collaborators change
        collaborators = data.get("collaborators")
        if collaborators is not None:
            if isinstance(collaborators, str):
                try:
                    collaborators = json.loads(collaborators)
                except json.JSONDecodeError:
                    collaborators = []
            
            current_collaborator_emails = [c.email for c in task.collaborators]
            new_collaborators = [c for c in collaborators if c not in current_collaborator_emails]
            removed_collaborators = [c for c in current_collaborator_emails if c not in collaborators]
            
            # Track collaborator changes
            if new_collaborators or removed_collaborators:
                updated_fields.append({
                    "field": "collaborators",
                    "old_value": ", ".join(current_collaborator_emails) if current_collaborator_emails else "None",
                    "new_value": ", ".join(collaborators) if collaborators else "None"
                })
            
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
                            # Add email notification for new collaborator
                            from app.services.email_services import send_task_assignment_email_notification
                            send_task_assignment_email_notification(task, current_user, user)

        # Handle attachments
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
            # Track attachment changes
            updated_fields.append({
                "field": "attachments",
                "old_value": f"{len(task.attachments)} files",
                "new_value": f"{len(task.attachments) + len(new_files)} files"
            })

        db.session.commit()

        # TRIGGER NOTIFICATIONS FOR ALL CHANGES
        user_id = get_jwt_identity()  
        current_user = User.query.get(int(user_id))
        
        # Create in-app notifications for any field changes
        if updated_fields and current_user:
            create_task_update_notification(task, current_user, updated_fields)
            
            # Send email notifications for any field changes (excluding the user who made changes)
            from app.services.email_services import send_task_update_email_notification
            send_task_update_email_notification(task, current_user, updated_fields, current_user.id)

        # Update due date notifications if due date changed
        due_date_changed = any(change.get('field') == 'due date' for change in updated_fields)
        if due_date_changed:
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