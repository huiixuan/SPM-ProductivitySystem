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
    remaining_days = (task.duedate - today).days
    
    if remaining_days >= 7:
        valid_triggers = [7, 3, 1]
    elif remaining_days >= 3:
        valid_triggers = [3, 1]
    elif remaining_days >= 1:
        valid_triggers = [1]
    else:
        valid_triggers = []

    users_to_notify = {task.owner} | set(task.collaborators or [])

    for user in users_to_notify:
        for days_before in valid_triggers:
            notif_date = task.duedate - timedelta(days=days_before)
            if remaining_days < days_before:
                continue
            if notif_date < today:
                continue
            
            payload = {
                "project_name": task.project.name if task.project else "No Project",
                "task_title": task.title,
                "duedate": task.duedate.isoformat() if task.duedate else None,
                "days_until_due": remaining_days
            }

            existing = Notification.query.filter_by(
                user_id=user.id,
                task_id=task.id,
                trigger_days_before=days_before
            ).first()

            if not existing:
                notif = Notification(
                    user_id=user.id,
                    task_id=task.id,
                    trigger_days_before=days_before,
                    payload=payload,
                    type=NotificationType.DUE_DATE_REMINDER  
                )
                db.session.add(notif)
    
    db.session.commit()

    if remaining_days <= 3:  # Only send emails for tasks due in 3 days or less/overdue
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

def send_task_assignment_email_notification(task, assigned_by, assignee):
    """Send email when a user is assigned to a task (as owner or collaborator)"""
    
    # Don't send email if the assignee is the same as the person assigning
    if assigned_by.id == assignee.id:
        return
    
    role = "owner" if task.owner_id == assignee.id else "collaborator"
    
    subject = f"📋 New task assignment: {task.title}"
    
    message = f"""
    <strong>You have been assigned as {role} to a new task:</strong>
    
    <div class="task-info">
        <p><strong>Task:</strong> {task.title}</p>
        <p><strong>Description:</strong> {task.description or 'No description provided'}</p>
        <p><strong>Due Date:</strong> {task.duedate.strftime('%Y-%m-%d') if task.duedate else 'Not set'}</p>
        <p><strong>Priority:</strong> {task.priority}</p>
        <p><strong>Status:</strong> {task.status.value}</p>
        <p><strong>Assigned by:</strong> {assigned_by.email}</p>
        <p><strong>Project:</strong> {task.project.name if task.project else 'No Project'}</p>
    </div>
    
    <strong>Collaborators:</strong>
    <ul>
        <li>{task.owner.email} (Owner)</li>
        {"".join([f"<li>{collab.email}</li>" for collab in task.collaborators])}
    </ul>
    
    <em>Please review the task and update your progress accordingly.</em>
    """
    
    email_service.send_notification_email(
        [assignee.email],
        subject,
        message,
        task.title,
        task.id,
        "task_assignment"
    )

def send_task_creation_email_notification(task, created_by):
    """Send email to all involved users when a task is created"""
    recipients = get_notification_recipients(task, created_by.id)
    if not recipients:
        return
    
    subject = f"🆕 New task created: {task.title}"
    
    message = f"""
    <strong>A new task has been created:</strong>
    
    <div class="task-info">
        <p><strong>Task:</strong> {task.title}</p>
        <p><strong>Description:</strong> {task.description or 'No description provided'}</p>
        <p><strong>Due Date:</strong> {task.duedate.strftime('%Y-%m-%d') if task.duedate else 'Not set'}</p>
        <p><strong>Priority:</strong> {task.priority}</p>
        <p><strong>Status:</strong> {task.status.value}</p>
        <p><strong>Created by:</strong> {created_by.email}</p>
        <p><strong>Project:</strong> {task.project.name if task.project else 'No Project'}</p>
    </div>
    
    <strong>Team:</strong>
    <ul>
        <li>{task.owner.email} (Owner)</li>
        {"".join([f"<li>{collab.email} (Collaborator)</li>" for collab in task.collaborators])}
    </ul>
    
    <em>This task has been added to your schedule.</em>
    """
    
    email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "task_creation"
    )

def remove_notifications_for_task(task: Task):
    """Deletes all notifications for a given task."""
    if not task:
        return
    Notification.query.filter_by(task_id=task.id).delete()
    db.session.commit()

def update_notifications_for_task(task: Task):
    """Recreates notifications when task due date changes with debugging"""
    if not task:
        return
    
    print(f"DEBUG: Updating notifications for task: {task.title}")
    print(f"DEBUG: Current due date: {task.duedate}")
    
    # Remove old notifications
    deleted_count = Notification.query.filter_by(task_id=task.id).delete()
    print(f"DEBUG: Deleted {deleted_count} old notifications")
    
    db.session.commit()

    # Create new notifications
    create_notifications_for_task(task)
    print(f"DEBUG: Created new due date notifications for task")

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
    
    return base_payload