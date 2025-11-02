from datetime import date, datetime, timedelta
from app.models import db, Notification, Task, TaskStatus, User, NotificationType
from sqlalchemy.orm.attributes import get_history
from app.services.email_services import (
    email_service,
    get_notification_recipients,
    send_comment_email_notification,
    send_task_update_email_notification,
    send_due_date_reminder_email,
    send_task_assignment_email_notification,
    send_task_creation_email_notification
)

TRIGGER_DAYS = [7, 3, 1]

def create_notifications_for_task(task: Task):
    if not task or not task.duedate:
        return
    
    if task.status == TaskStatus.COMPLETED:
        return

    today = date.today()
    
    # Handle both date and datetime objects
    if isinstance(task.duedate, datetime):
        due_date = task.duedate.date()
    else:
        due_date = task.duedate
        
    remaining_days = (due_date - today).days
    
    print(f"DEBUG: Creating notifications for task: {task.title}")
    print(f"DEBUG: Due date: {due_date}, Today: {today}, Remaining days: {remaining_days}")
    
    # Only create notifications for future dates
    if remaining_days < 0:
        print(f"DEBUG: Task is overdue, no future notifications created")
        # Send overdue notification instead
        if remaining_days == -1:  # Only send one overdue notification
            send_due_date_reminder_email(task, remaining_days)
        return

    users_to_notify = {task.owner} | set(task.collaborators or [])
    
    # Remove old due date notifications for this task
    Notification.query.filter_by(
        task_id=task.id,
        type=NotificationType.DUE_DATE_REMINDER
    ).delete()
    
    notification_created = False
    
    for user in users_to_notify:
        # Create notifications for 7, 3, and 1 days before due date
        for days_before in [7, 3, 1]:
            if remaining_days == days_before:
                payload = {
                    "project_name": task.project.name if task.project else "No Project",
                    "task_title": task.title,
                    "duedate": due_date.isoformat(),
                    "days_until_due": remaining_days
                }
                
                notif = Notification(
                    user_id=user.id,
                    task_id=task.id,
                    trigger_days_before=remaining_days,
                    payload=payload,
                    type=NotificationType.DUE_DATE_REMINDER
                )
                db.session.add(notif)
                notification_created = True
                print(f"DEBUG: Created {remaining_days}-day notification for user: {user.email}")

    if notification_created:
        db.session.commit()
        print(f"DEBUG: Created due date notifications for task {task.title}")
        
        # Send email only for the exact remaining days
        if remaining_days in [7, 3, 1]:
            send_due_date_reminder_email(task, remaining_days)


def create_comment_notification(comment):
    task = comment.task
    if not task:
        return

    users_to_notify = {task.owner} | set(task.collaborators or [])

    users_to_notify = {user for user in users_to_notify if user.id != comment.user_id}

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "comment_author": comment.user.email,
        "comment_excerpt": comment.content[:50] + "..." if len(comment.content) > 50 else comment.content,
        "comment_id": comment.id
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            comment_id=comment.id,
            type=NotificationType.NEW_COMMENT  
        )
        db.session.add(notif)
    
    db.session.commit()
    
    # Always send email notification for comments, not just when @mentioning
    send_comment_email_notification(comment, task, comment.user_id)


def create_task_update_notification(task: Task, updated_by: User, updated_fields: list):
    """Create in-app notifications for task updates with debugging"""
    users_to_notify = {task.owner} | set(task.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != updated_by.id}

    print(f"DEBUG: Creating task update notification for task: {task.title}")
    print(f"DEBUG: Updated by: {updated_by.email}")
    print(f"DEBUG: Fields changed: {[f['field'] for f in updated_fields]}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "updated_fields": updated_fields,
        "updated_by": updated_by.email
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            type=NotificationType.TASK_UPDATED 
        )
        db.session.add(notif)
        print(f"DEBUG: Added in-app notification for user: {user.email}")
    
    db.session.commit()
    print(f"DEBUG: Committed {len(users_to_notify)} in-app notifications")

def create_task_creation_notification(task: Task, created_by: User):
    """Create in-app notifications for task creation"""
    users_to_notify = {task.owner} | set(task.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != created_by.id}

    print(f"DEBUG: Creating task creation notification for task: {task.title}")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "description": task.description,
        "duedate": task.duedate.isoformat() if task.duedate else None,
        "created_by": created_by.email
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            type=NotificationType.TASK_CREATED
        )
        db.session.add(notif)
        print(f"DEBUG: Added task creation notification for user: {user.email}")
    
    try:
        db.session.commit()
        print(f"DEBUG: Committed {len(users_to_notify)} task creation notifications")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Failed to create task creation notifications: {e}")

def create_task_assignment_notification(task: Task, assigned_by: User, assignee: User):
    """Create notification when task is assigned to someone"""
    if task.owner_id == assignee.id:
        return 

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "assigned_by": assigned_by.email,
        "previous_owner": task.owner.email if task.owner else "Unknown"
    }

    notif = Notification(
        user_id=assignee.id,
        task_id=task.id,
        payload=payload,
        type=NotificationType.TASK_UPDATED
    )
    db.session.add(notif)
    
    db.session.commit()

def remove_notifications_for_task(task: Task):
    """Deletes all notifications for a given task."""
    if not task:
        return
    Notification.query.filter_by(task_id=task.id).delete()
    db.session.commit()

def update_notifications_for_task(task: Task):
    """Recreates notifications when task due date changes"""
    if not task:
        return
    
    print(f"DEBUG: Updating notifications for task: {task.title}")
    print(f"DEBUG: Current due date: {task.duedate}")
    
    # Remove all old due date notifications
    deleted_count = Notification.query.filter_by(
        task_id=task.id, 
        type=NotificationType.DUE_DATE_REMINDER
    ).delete()
    print(f"DEBUG: Deleted {deleted_count} old due date notifications")
    
    db.session.commit()

    # Create new notifications based on current due date
    create_notifications_for_task(task)
    print(f"DEBUG: Created new due date notifications for task")

def create_project_creation_notification(project, created_by):
    """Create in-app notifications for project creation"""
    users_to_notify = {project.owner} | set(project.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != created_by.id}

    print(f"DEBUG: Creating project creation notification for project: {project.name}")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": project.name,
        "description": project.description,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "status": project.status.value,
        "created_by": created_by.email
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=None, 
            payload=payload,
            type=NotificationType.PROJECT_CREATED  
        )
        db.session.add(notif)
        print(f"DEBUG: Added project notification for user: {user.email}")
    
    try:
        db.session.commit()
        print(f"DEBUG: Committed {len(users_to_notify)} project notifications")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Failed to create project notifications: {e}")

def create_project_update_notification(project, updated_by, updated_fields):
    """Create in-app notifications for project updates"""
    users_to_notify = {project.owner} | set(project.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != updated_by.id}

    print(f"DEBUG: Creating project update notification for project: {project.name}")
    print(f"DEBUG: Updated by: {updated_by.email}")
    print(f"DEBUG: Updated fields: {updated_fields}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": project.name,
        "updated_fields": updated_fields,
        "updated_by": updated_by.email
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=None,
            payload=payload,
            type=NotificationType.PROJECT_UPDATED
        )
        db.session.add(notif)
        print(f"DEBUG: Added project update notification for user: {user.email}")
    
    try:
        db.session.commit()
        print(f"DEBUG: Committed {len(users_to_notify)} project update notifications")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Failed to create project update notifications: {e}")

def get_notifications_for_user(user_id: int):
    """Returns notifications for a user, sorted by recency"""
    return (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )

def mark_notification_as_read(notification_id: int):
    """Marks a single notification as read"""
    notif = Notification.query.get(notification_id)
    if notif:
        notif.is_read = True
        db.session.commit()
    return notif

def mark_all_notifications_as_read(user_id: int):
    """Marks all notifications for a user as read"""
    Notification.query.filter_by(user_id=user_id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()

def create_notification_payload(notification_type: NotificationType, **kwargs):
    """Standardized payload creation for all notification types"""
    base_payload = {
        "notification_type": notification_type.value,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if notification_type == NotificationType.DUE_DATE_REMINDER:
        base_payload.update({
            "project_name": kwargs.get("project_name", "No Project"),
            "task_title": kwargs.get("task_title", "Untitled Task"),
            "duedate": kwargs.get("duedate").isoformat() if kwargs.get("duedate") else None,
            "days_until_due": kwargs.get("days_until_due")
        })
    elif notification_type == NotificationType.NEW_COMMENT:
        base_payload.update({
            "project_name": kwargs.get("project_name", "No Project"),
            "task_title": kwargs.get("task_title", "Untitled Task"),
            "comment_author": kwargs.get("comment_author"),
            "comment_excerpt": kwargs.get("comment_excerpt"),
            "comment_id": kwargs.get("comment_id")
        })
    elif notification_type == NotificationType.TASK_UPDATED:
        base_payload.update({
            "project_name": kwargs.get("project_name", "No Project"),
            "task_title": kwargs.get("task_title", "Untitled Task"),
            "updated_fields": kwargs.get("updated_fields", []),
            "updated_by": kwargs.get("updated_by")
        })
    elif notification_type == NotificationType.TASK_CREATED:  # Added
        base_payload.update({
            "project_name": kwargs.get("project_name", "No Project"),
            "task_title": kwargs.get("task_title", "Untitled Task"),
            "created_by": kwargs.get("created_by"),
            "description": kwargs.get("description"),
            "duedate": kwargs.get("duedate").isoformat() if kwargs.get("duedate") else None,
        })
    
    return base_payload