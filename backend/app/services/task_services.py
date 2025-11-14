import json
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from app.models import db, Task, Attachment, User, Project, RecurrenceType, TaskStatus
from flask import request
from app.services.user_services import get_user_by_email, get_users_info
from app.services.project_services import get_project_users
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.services.notification_services import (
    create_notifications_for_task,
    remove_notifications_for_task,
    update_notifications_for_task,
    create_comment_notification,
    create_task_update_notification,
    create_task_assignment_notification,
    send_task_update_notification,
    send_task_assignment_notification, 
    create_recurring_task_creation_notification  
)
from flask_jwt_extended import get_jwt_identity

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

def create_task(title, description, duedate, status, owner_email, collaborator_emails, attachments, notes, priority, project_id=None, recurrence="none", customInterval=None, parent_task_id=None):
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

        is_recurring = recurrence != "none"
        recurrence_type = RecurrenceType(recurrence) if is_recurring else RecurrenceType("none")
        recurrence_interval = customInterval if recurrence == "custom" else None

        task = Task(
            title=title, 
            description=description, 
            duedate=duedate, 
            status=status, 
            owner=owner, 
            collaborators=collaborators, 
            notes=notes, 
            priority=priority, 
            isRecurring=is_recurring, 
            recurrence_type=recurrence_type, 
            recurrence_interval=recurrence_interval, 
            parent_id=parent_task_id  
        )

        if project_id:
            project = Project.query.get(project_id)
            if project:
                task.project = project

        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id)) if current_user_id else None

        if attachments:
            for file in attachments:
                attachment = Attachment(filename=file.filename, content=file.read(), task=task)
                db.session.add(attachment)
                print(f"DEBUG: Added initial attachment: {file.filename}")
        
                if current_user:
                    from app.services.notification_services import send_task_attachment_notification
                    send_task_attachment_notification(task, current_user, file.filename)

        db.session.add(task)
        db.session.commit()

        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))

        if current_user:
            print(f"=== TASK CREATION NOTIFICATION FLOW ===")
            print(f"DEBUG: Current user: {current_user.email}")
            print(f"DEBUG: Task owner: {owner.email}")
            print(f"DEBUG: Collaborators: {[c.email for c in collaborators]}")
            print(f"DEBUG: Is subtask: {bool(parent_task_id)}")
    
            from app.services.notification_services import send_task_creation_notification
            send_task_creation_notification(task, current_user)
    
            if current_user.id != owner.id:
                send_task_assignment_notification(task, current_user, owner, "owner")
    
            for collaborator in collaborators:
                if collaborator.id != current_user.id:
                    send_task_assignment_notification(task, current_user, collaborator, "collaborator")
    
            print(f"DEBUG: Calling create_notifications_for_task (due date reminders)...")
            create_notifications_for_task(task)
    
            print(f"=== END TASK CREATION NOTIFICATION FLOW ===")

        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError("Database error while creating task")

def create_next_recurring_task(completed_task: Task):
    if not completed_task.isRecurring or not completed_task.recurrence_type:
        return None

    old_due = completed_task.duedate

    recurrence_type = completed_task.recurrence_type
    
    if recurrence_type == RecurrenceType.DAILY:
        new_due = old_due + timedelta(days=1)

    elif recurrence_type == RecurrenceType.WEEKLY:
        new_due = old_due + timedelta(weeks=1)

    elif recurrence_type == RecurrenceType.MONTHLY:
        new_due = old_due + relativedelta(months=1)

    elif recurrence_type == RecurrenceType.CUSTOM:
        if completed_task.recurrence_interval and completed_task.recurrence_interval > 0:
            new_due = old_due + timedelta(days=completed_task.recurrence_interval)

        else:
            raise ValueError("Custom interval is missing or invalid for recurring task")

    print(f"[DEBUG] Creating next recurring task due on: {new_due}")

    next_task = Task(
        title=completed_task.title,
        description=completed_task.description,
        duedate=new_due,
        status=TaskStatus.UNASSIGNED,
        priority=completed_task.priority,
        owner=completed_task.owner,
        notes=completed_task.notes,
        project=completed_task.project,
        isRecurring=completed_task.isRecurring,
        recurrence_type=completed_task.recurrence_type,
        recurrence_interval=completed_task.recurrence_interval,
    )

    db.session.add(next_task)

    next_task.collaborators = completed_task.collaborators[:] if completed_task.collaborators else []

    if completed_task.attachments:
        for attachment in completed_task.attachments:
            new_attachment = Attachment(
                filename=attachment.filename,
                content=attachment.content,
                task=next_task
            )
            db.session.add(new_attachment)

    db.session.commit()

    create_recurring_task_creation_notification(next_task, completed_task)

    # Create due date notifications for the new recurring task
    from app.services.notification_services import create_notifications_for_task
    create_notifications_for_task(next_task)

    return next_task

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
    project_id = None
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
        raise RuntimeError(f"Database error while retrieving users of project {project_id or ''}: {e}")

def get_unassigned_tasks():
    try:
        tasks = Task.query.filter(Task.project_id == None).all()
        return tasks
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching unassigned tasks: {e}")

def link_task_to_project(task_id, project_id, linked_by=None):
    """Link task to project with notifications"""
    try:
        task = Task.query.get(task_id)
        project = Project.query.get(project_id)

        if not task:
            raise ValueError(f"Task with ID {task_id} not found.")
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        old_project = task.project
        task.project = project
        db.session.commit()

        if linked_by:
            updated_fields = [{
                'field': 'project',
                'old_value': old_project.name if old_project else 'No Project',
                'new_value': project.name
            }]
            
            # Send both in-app and email notifications
            from app.services.notification_services import send_task_update_notification
            send_task_update_notification(task, linked_by, updated_fields)
            
            print(f"DEBUG: Sent notifications for linking task {task_id} to project {project_id}")

        return task
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while linking task {task_id} to project {project_id}: {e}")

def update_task(task_id, data, new_files):
    try:
        print(f"Starting update for task {task_id}")
        print(f"Received data: {data}")
        print(f"Received files: {request.files}")
        
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with task ID {task_id} not found")
        
        original_attachments = [{"id": att.id, "filename": att.filename} for att in task.attachments]
        print(f"DEBUG: Original attachments: {[att['filename'] for att in original_attachments]}")
        
        old_values = {
            'status': task.status,
            'duedate': task.duedate,
            'priority': task.priority,
            'owner_id': task.owner_id,
            'attachments': original_attachments
        }
        
        updated_fields = []
        
        if "title" in data and data["title"] != task.title:
            updated_fields.append({
                "field": "title",
                "old_value": task.title,
                "new_value": data["title"]
            })
            task.title = data["title"]
        
        if "description" in data and data["description"] != task.description:
            updated_fields.append({
                "field": "description", 
                "old_value": task.description,
                "new_value": data["description"]
            })
            task.description = data["description"]
            
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

                    if new_status == TaskStatus.COMPLETED:
                        create_next_recurring_task(task)
                        
            except ValueError:
                raise ValueError(f"Invalid status: {data['status']}")
        
        if "priority" in data:
            new_priority = int(data["priority"])
            if task.priority != new_priority:
                updated_fields.append({
                    "field": "priority",
                    "old_value": str(task.priority),
                    "new_value": str(new_priority)
                })
                task.priority = new_priority

        if "recurrence" in data:
            recurrence = data.get("recurrence")
            custom_interval = data.get("custom_interval")

            task.isRecurring = recurrence != "none"
            task.recurrence_type = RecurrenceType(recurrence) if task.isRecurring else RecurrenceType("none")
            task.recurrence_interval = int(custom_interval) if recurrence == "custom" else None
        
        if "notes" in data and data["notes"] != task.notes:
            updated_fields.append({
                "field": "notes",
                "old_value": task.notes,
                "new_value": data["notes"]
            })
            task.notes = data["notes"]

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
                
                send_task_assignment_notification(task, current_user, owner, "owner")
                
                task.owner = owner

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
                            
                            send_task_assignment_notification(task, current_user, user, "collaborator")

        removed_attachments = []
        
        if "existing_attachments" in data:
            existing_attachments = data["existing_attachments"]
            print(f"DEBUG: Existing attachments from form: {existing_attachments}")
            
            existing_ids = [att.get("id") for att in existing_attachments if att.get("id")]
            print(f"DEBUG: Attachment IDs to keep: {existing_ids}")
            
            for att in task.attachments[:]:
                if att.id not in existing_ids:
                    # Store removed attachment info
                    removed_attachments.append({
                        "filename": att.filename,
                        "id": att.id
                    })
                    db.session.delete(att)
                    print(f"DEBUG: Marked attachment for deletion: {att.filename}")


        new_attachments = []
        if new_files:
            for file in new_files:
                if file.filename:  
                    attachment = Attachment(
                        filename=file.filename,
                        content=file.read(),
                        task=task
                    )
                    db.session.add(attachment)
                    new_attachments.append(file.filename)
                    print(f"DEBUG: Added new attachment: {file.filename}")
                    
                    # Send attachment notification
                    user_id = get_jwt_identity()  
                    current_user = User.query.get(int(user_id))
                    if current_user:
                        from app.services.notification_services import send_task_attachment_notification
                        send_task_attachment_notification(task, current_user, file.filename)
        
        db.session.commit()


        user_id = get_jwt_identity()  
        current_user = User.query.get(int(user_id))
        
        # Create notifications for removed attachments
        for removed_att in removed_attachments:
            from app.services.notification_services import create_task_attachment_removal_notification
            create_task_attachment_removal_notification(task, current_user, removed_att["filename"])
            print(f"DEBUG: Created removal notification for: {removed_att['filename']}")

   
        for removed_att in removed_attachments:
            updated_fields.append({
                "field": "attachment",
                "old_value": removed_att["filename"],
                "new_value": "Removed"
            })

        for new_att in new_attachments:
            updated_fields.append({
                "field": "attachment", 
                "old_value": "None",
                "new_value": new_att
            })
        
        if updated_fields and current_user:
            print(f"DEBUG: Sending task update notifications for {len(updated_fields)} changes")
            print(f"DEBUG: Changes: {updated_fields}")
            
            send_task_update_notification(task, current_user, updated_fields)

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

def get_subtasks(parent_task_id):
    try:
        return Task.query.filter_by(parent_id=parent_task_id).all()
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while getting subtasks of task {parent_task_id}: {e}")
    
def link_task(task_id, user_id):
    """Stub for testing — simulate linking a task to a user."""
    print(f"Linking task {task_id} to user {user_id}")
    return True

#Comment