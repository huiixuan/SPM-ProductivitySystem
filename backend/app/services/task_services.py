import json
from datetime import timedelta
from flask import request
from dateutil.relativedelta import relativedelta
from app.models import db, Task, Attachment, User, Project, RecurrenceType, TaskStatus
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
    create_notifications_for_recurring_task,
    send_recurring_task_created_email_notification
)
from flask_jwt_extended import get_jwt_identity
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

def create_next_recurring_task(completed_task: Task):
    """Create the next instance of a recurring task and set up notifications"""
    if not completed_task.isRecurring:
        return None

    if not completed_task.recurrence_type or completed_task.recurrence_type == RecurrenceType.NONE:
        return None

    old_due = completed_task.duedate
    new_due = old_due

    if completed_task.recurrence_type == RecurrenceType.DAILY:
        new_due = old_due + timedelta(days=1)
    elif completed_task.recurrence_type == RecurrenceType.WEEKLY:
        new_due = old_due + timedelta(weeks=1)
    elif completed_task.recurrence_type == RecurrenceType.MONTHLY:
        new_due = old_due + relativedelta(months=1)
    elif completed_task.recurrence_type == RecurrenceType.CUSTOM:
        if completed_task.recurrence_interval:
            new_due = old_due + timedelta(days=completed_task.recurrence_interval)
        else:
            raise ValueError("Custom interval is missing for recurring task")

    # Create the next task instance
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

    # Copy collaborators
    for collaborator in completed_task.collaborators:
        next_task.collaborators.append(collaborator)

    # Copy attachments
    for attachment in completed_task.attachments:
        new_attachment = Attachment(
            filename=attachment.filename,
            content=attachment.content,
            task=next_task
        )
        db.session.add(new_attachment)

    db.session.add(next_task)
    db.session.commit()

    # Create notifications for the new recurring task
    create_notifications_for_recurring_task(next_task, completed_task)
    
    # Send email notification about the new recurring task
    send_recurring_task_created_email_notification(next_task, completed_task)

    print(f"DEBUG: Created next recurring task: {next_task.title} due {next_task.duedate}")
    
    return next_task

def create_task(title, description, duedate, status, owner_email, collaborator_emails, attachments, notes, priority, project_id=None, recurrence="none", customInterval=None):
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
        recurrence_type = RecurrenceType(recurrence) if is_recurring else None
        recurrence_interval = customInterval if recurrence == "custom" else None

        task = Task(title=title, description=description, duedate=duedate, status=status, owner=owner, collaborators=collaborators, notes=notes, priority=priority, isRecurring=is_recurring, recurrence_type=recurrence_type, recurrence_interval=recurrence_interval)

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

        # Get current user for notifications
        current_user_id = get_jwt_identity()
        current_user = User.query.get(int(current_user_id))

        if current_user:
            print(f"=== TASK CREATION NOTIFICATION FLOW ===")
            print(f"DEBUG: Current user: {current_user.email}")
            print(f"DEBUG: Task owner: {owner.email}")
            print(f"DEBUG: Collaborators: {[c.email for c in collaborators]}")
            
            # 1. FIRST: Create task creation notification (this should appear immediately)
            from app.services.notification_services import create_task_creation_notification
            print(f"DEBUG: Calling create_task_creation_notification...")
            create_task_creation_notification(task, current_user)
            
            # 2. SECOND: Create due date reminder notifications
            print(f"DEBUG: Calling create_notifications_for_task (due date reminders)...")
            notification_service.create_notifications_for_task(task)
            
            # 3. THIRD: Send email notifications
            print(f"DEBUG: Sending email notifications...")
            try:
                send_task_creation_email_notification(task, current_user)
                print(f"DEBUG: Task creation email sent successfully")
            except Exception as e:
                print(f"DEBUG: Error sending task creation email: {e}")
            
            # Send assignment emails
            if current_user.id != owner.id:
                try:
                    send_task_assignment_email_notification(task, current_user, owner)
                    print(f"DEBUG: Owner assignment email sent")
                except Exception as e:
                    print(f"DEBUG: Error sending owner assignment email: {e}")
            
            for collaborator in collaborators:
                if collaborator.id != current_user.id:
                    try:
                        send_task_assignment_email_notification(task, current_user, collaborator)
                        print(f"DEBUG: Collaborator assignment email sent to {collaborator.email}")
                    except Exception as e:
                        print(f"DEBUG: Error sending collaborator assignment email: {e}")
            
            print(f"=== END TASK CREATION NOTIFICATION FLOW ===")

        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError("Database error while creating task")

def create_next_recurring_task(completed_task: Task, current_user: User):
    if not completed_task.isRecurring:
        return None

    if not completed_task.recurrence_type:
        return None

    old_due = completed_task.duedate
    new_due = old_due

    if completed_task.recurrence_type == "daily":
        new_due = old_due + timedelta(days=1)
    elif completed_task.recurrence_type == "weekly":
        new_due = old_due + timedelta(weeks=1)
    elif completed_task.recurrence_type == "monthly":
        new_due = old_due + relativedelta(months=1)
    elif completed_task.recurrence_type == "custom":
        if completed_task.recurrence_interval:
            new_due = old_due + timedelta(days=completed_task.recurrence_interval)
        else:
            raise ValueError("Custom interval is missing for recurring task")

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

    for collaborator in completed_task.collaborators:
        next_task.collaborators.append(collaborator)

    for attachment in completed_task.attachments:
        new_attachment = Attachment(
            filename=attachment.filename,
            content=attachment.content,
            task=next_task
        )
        db.session.add(new_attachment)

    db.session.add(next_task)
    db.session.commit()

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
        
        # Track changes for each field
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
                        current_user = User.query.get(int(get_jwt_identity()))
                        create_next_recurring_task(task, current_user)
                        
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
            custom_interval = data.get("customInterval")

            task.isRecurring = recurrence != "none"
            task.recurrence_type = RecurrenceType(recurrence) if task.isRecurring else None
            task.recurrence_interval = custom_interval if recurrence == "custom" else None
        
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
                create_task_assignment_notification(task, current_user, owner)

                from app.services.email_services import send_task_assignment_email_notification
                send_task_assignment_email_notification(task, current_user, owner)
                
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
                            create_task_assignment_notification(task, current_user, user)
                            from app.services.email_services import send_task_assignment_email_notification
                            send_task_assignment_email_notification(task, current_user, user)

        # Handle attachments removal and addition
        removed_attachments = []
        
        if "existing_attachments" in data:
            existing_attachments = data["existing_attachments"]
            print(f"DEBUG: Existing attachments from form: {existing_attachments}")
            
            if isinstance(existing_attachments, str):
                try:
                    existing_attachments = json.loads(existing_attachments)
                except json.JSONDecodeError:
                    existing_attachments = []
            
            existing_ids = [att.get("id") for att in existing_attachments if att.get("id")]
            print(f"DEBUG: Attachment IDs to keep: {existing_ids}")
            
            # Find removed attachments
            for att in task.attachments[:]:
                if att.id not in existing_ids:
                    removed_attachments.append(att.filename)
                    db.session.delete(att)
                    print(f"DEBUG: Marked attachment for deletion: {att.filename}")

        # Add new files
        if new_files:
            for file in new_files:
                if file.filename:  # Only process if filename is not empty
                    attachment = Attachment(
                        filename=file.filename,
                        content=file.read(),
                        task=task
                    )
                    db.session.add(attachment)
                    print(f"DEBUG: Added new attachment: {file.filename}")

        # Track attachment changes in updated_fields
        if removed_attachments:
            for filename in removed_attachments:
                updated_fields.append({
                    "field": "attachment",
                    "old_value": filename,
                    "new_value": "Removed"
                })
                print(f"DEBUG: Added removal notification for: {filename}")

        if new_files:
            for file in new_files:
                if file.filename:
                    updated_fields.append({
                        "field": "attachment", 
                        "old_value": "None",
                        "new_value": file.filename
                    })
                    print(f"DEBUG: Added addition notification for: {file.filename}")




        db.session.commit()

        user_id = get_jwt_identity()  
        current_user = User.query.get(int(user_id))
        
        if updated_fields and current_user:
            print(f"DEBUG: Sending task update notifications for {len(updated_fields)} changes")
            print(f"DEBUG: Changes: {updated_fields}")
            
            from app.services.notification_services import send_task_update_notification
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