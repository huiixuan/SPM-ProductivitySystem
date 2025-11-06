from datetime import date, datetime, timedelta
from app.models import db, Notification, Task, TaskStatus, User, NotificationType, Project
from sqlalchemy.orm.attributes import get_history
from app.services.email_services import (
    email_service,
    get_notification_recipients,
    send_comment_email_notification,
    send_task_update_email_notification,
    send_due_date_reminder_email,
    send_task_assignment_email_notification,
    send_task_creation_email_notification,
    send_project_creation_email_notification,
    send_project_update_email_notification,
    send_project_collaborator_added_email_notification,
    send_project_assignment_email_notification,
    send_task_attachment_email_notification,
    send_project_attachment_email_notification,
    send_task_attachment_removal_email_notification
)

TRIGGER_DAYS = [7, 3, 1]

def create_notifications_for_task(task: Task):
    """Create due date reminder notifications for a task - ENHANCED with immediate in-app notifications"""
    if not task or not task.duedate:
        print(f"DEBUG: No task or due date for notifications")
        return
    
    if task.status == TaskStatus.COMPLETED:
        print(f"DEBUG: Task {task.id} is completed, skipping due date notifications")
        return

    today = date.today()
    remaining_days = (task.duedate - today).days
    
    print(f"DEBUG: Creating DUE DATE notifications for task '{task.title}', due in {remaining_days} days on {task.duedate}")
    
    if remaining_days <= 7 and remaining_days >= 0:
        create_due_date_reminder_notification(task, remaining_days)
    
    # Only create future due date notifications for future due dates
    if remaining_days < 0:
        print(f"DEBUG: Task is overdue, skipping future due date notification creation")
        # But create an overdue notification
        create_due_date_reminder_notification(task, remaining_days)
        return
    
    users_to_notify = {task.owner} | set(task.collaborators or [])
    print(f"DEBUG: Users to notify for due dates: {[user.email for user in users_to_notify]}")

    notifications_created = 0

    for user in users_to_notify:
        for days_before in TRIGGER_DAYS:
            # Only create due date notification if it's relevant
            should_create = (
                (days_before == 7 and remaining_days >= 7) or
                (days_before == 3 and 3 <= remaining_days < 7) or
                (days_before == 1 and 1 <= remaining_days < 3) or
                (remaining_days == 0 and days_before == 1)  # Due today
            )
            
            if not should_create:
                print(f"DEBUG: Skipping {days_before}-day due date notification - task due in {remaining_days} days")
                continue
            
            # Create due date reminder notification
            payload = {
                "project_name": task.project.name if task.project else "No Project",
                "task_title": task.title,
                "duedate": task.duedate.isoformat() if task.duedate else None,
                "days_until_due": days_before,
                "actual_days_until_due": remaining_days,
                "is_recurring": task.isRecurring,
                "recurrence_type": task.recurrence_type.value if task.recurrence_type else None,
                "notification_type": "due_date_reminder"
            }

            # Check if notification already exists
            existing = Notification.query.filter_by(
                user_id=user.id,
                task_id=task.id,
                trigger_days_before=days_before,
                type=NotificationType.DUE_DATE_REMINDER
            ).first()

            if not existing:
                try:
                    notif = Notification(
                        user_id=user.id,
                        task_id=task.id,
                        trigger_days_before=days_before,
                        payload=payload,
                        type=NotificationType.DUE_DATE_REMINDER,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notif)
                    notifications_created += 1
                    print(f"DEBUG: ✅ Created {days_before}-day DUE DATE notification for user {user.email}")
                except Exception as e:
                    print(f"ERROR: Failed to create due date notification: {e}")
    
    try:
        if notifications_created > 0:
            db.session.commit()
            print(f"DEBUG: Successfully committed {notifications_created} due date notifications")
        else:
            print(f"DEBUG: No due date notifications created for task '{task.title}'")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to commit due date notifications: {e}")

def create_due_date_reminder_notification(task: Task, days_until_due: int):
    """Create in-app notification for due date reminders"""
    users_to_notify = {task.owner} | set(task.collaborators or [])
    
    print(f"DEBUG: Creating due date reminder notification for '{task.title}'")
    print(f"DEBUG: Days until due: {days_until_due}")
    print(f"DEBUG: Users to notify: {[user.email for user in users_to_notify]}")

    status = "overdue" if days_until_due < 0 else "due soon"
    days_text = f"{-days_until_due} days ago" if days_until_due < 0 else f"in {days_until_due} days"

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "duedate": task.duedate.isoformat() if task.duedate else None,
        "days_until_due": days_until_due,
        "status": status,
        "days_text": days_text,
        "notification_type": "due_date_reminder",
        "priority": task.priority,
        "current_status": task.status.value
    }

    for user in users_to_notify:
        # Check if notification already exists to avoid duplicates
        existing = Notification.query.filter_by(
            user_id=user.id,
            task_id=task.id,
            type=NotificationType.DUE_DATE_REMINDER
        ).filter(Notification.payload['days_until_due'].astext == str(days_until_due)).first()

        if not existing:
            notif = Notification(
                user_id=user.id,
                task_id=task.id,
                payload=payload,
                type=NotificationType.DUE_DATE_REMINDER
            )
            db.session.add(notif)
            print(f"DEBUG: Created due date reminder notification for user {user.email}")

    try:
        db.session.commit()
        print(f"DEBUG: Successfully committed due date reminder notifications")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to commit due date reminder notifications: {e}")

def create_recurring_task_creation_notification(next_task: Task, original_task: Task):
    """Create in-app notification for recurring task creation"""
    users_to_notify = {next_task.owner} | set(next_task.collaborators or [])
    
    print(f"DEBUG: Creating recurring task creation notification for '{next_task.title}'")
    print(f"DEBUG: Original task: {original_task.title}")
    print(f"DEBUG: Users to notify: {[user.email for user in users_to_notify]}")

    payload = {
        "project_name": next_task.project.name if next_task.project else "No Project",
        "task_title": next_task.title,
        "duedate": next_task.duedate.isoformat() if next_task.duedate else None,
        "created_by": "System",  # Since it's system-generated
        "task_description": next_task.description or "No description",
        "priority": next_task.priority,
        "status": next_task.status.value,
        "notification_type": "recurring_task_created",
        "original_task_id": original_task.id,
        "original_task_title": original_task.title,
        "recurrence_type": next_task.recurrence_type.value if next_task.recurrence_type else None
    }

    notifications_created = 0
    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=next_task.id,
            payload=payload,
            type=NotificationType.TASK_UPDATED
        )
        db.session.add(notif)
        notifications_created += 1
        print(f"DEBUG: Created recurring task creation notification for user {user.email}")

    if notifications_created > 0:
        try:
            db.session.commit()
            print(f"DEBUG: Successfully committed {notifications_created} recurring task creation notifications")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to commit recurring task creation notifications: {e}")

def create_task_creation_notification(task: Task, created_by: User):
    """Create in-app notification for task creation"""
    users_to_notify = {task.owner} | set(task.collaborators or [])
    # Exclude the user who created the task
    users_to_notify = {user for user in users_to_notify if user.id != created_by.id}
    
    print(f"DEBUG: Creating task creation notifications for '{task.title}'")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Users to notify: {[user.email for user in users_to_notify]}")

    notifications_created = 0

    for user in users_to_notify:
        payload = {
            "project_name": task.project.name if task.project else "No Project",
            "task_title": task.title,
            "duedate": task.duedate.isoformat() if task.duedate else None,
            "created_by": created_by.email,
            "task_description": task.description or "No description",
            "priority": task.priority,
            "status": task.status.value,
            "notification_type": "task_creation"
        }

        # Check if notification already exists
        existing = Notification.query.filter_by(
            user_id=user.id,
            task_id=task.id,
            type=NotificationType.TASK_UPDATED
        ).first()

        if not existing:
            try:
                notif = Notification(
                    user_id=user.id,
                    task_id=task.id,
                    payload=payload,
                    type=NotificationType.TASK_UPDATED,  # Use TASK_UPDATED for creation too
                    created_at=datetime.utcnow()
                )
                db.session.add(notif)
                notifications_created += 1
                print(f"DEBUG: ✅ Created task creation notification for user {user.email}")
            except Exception as e:
                print(f"ERROR: Failed to create task creation notification: {e}")

    if notifications_created > 0:
        try:
            db.session.commit()
            print(f"DEBUG: Successfully committed {notifications_created} task creation notifications")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to commit task creation notifications: {e}")

def check_and_create_future_notifications():
    """This function should be called daily to create notifications that are due"""
    today = date.today()
    print(f"DEBUG: Checking for future notifications due today: {today}")
    
    # Find all tasks with due dates in the future that need notifications
    future_tasks = Task.query.filter(
        Task.duedate > today,
        Task.status != TaskStatus.COMPLETED
    ).all()
    
    notifications_created = 0
    
    for task in future_tasks:
        users_to_notify = {task.owner} | set(task.collaborators or [])
        
        for user in users_to_notify:
            for days_before in TRIGGER_DAYS:
                notif_trigger_date = task.duedate - timedelta(days=days_before)
                days_until_notification = (notif_trigger_date - today).days
                
                # Create notification if it should appear today
                if days_until_notification == 0:
                    existing = Notification.query.filter_by(
                        user_id=user.id,
                        task_id=task.id,
                        trigger_days_before=days_before,
                        type=NotificationType.DUE_DATE_REMINDER
                    ).first()
                    
                    if not existing:
                        payload = {
                            "project_name": task.project.name if task.project else "No Project",
                            "task_title": task.title,
                            "duedate": task.duedate.isoformat(),
                            "days_until_due": days_before,
                            "actual_days_until_due": (task.duedate - today).days,
                            "is_recurring": task.isRecurring,
                            "recurrence_type": task.recurrence_type.value if task.recurrence_type else None
                        }
                        
                        notif = Notification(
                            user_id=user.id,
                            task_id=task.id,
                            trigger_days_before=days_before,
                            payload=payload,
                            type=NotificationType.DUE_DATE_REMINDER,
                            created_at=datetime.utcnow()
                        )
                        db.session.add(notif)
                        notifications_created += 1
                        print(f"DEBUG: 🔔 Created future {days_before}-day notification for task '{task.title}'")
    
    if notifications_created > 0:
        db.session.commit()
        print(f"DEBUG: Created {notifications_created} future notifications")
    
    return notifications_created

def get_notifications_for_user(user_id: int):
    """Returns notifications for a user, sorted by recency"""
    try:
        notifications = (
            Notification.query
            .filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
        print(f"DEBUG: Found {len(notifications)} notifications for user {user_id}")
        return notifications
    except Exception as e:
        print(f"ERROR: Failed to get notifications for user {user_id}: {e}")
        return []

def create_notifications_for_recurring_task(next_task: Task, original_task: Task):
    """Create notifications for a newly generated recurring task"""
    if not next_task or not next_task.duedate:
        return
    
    today = date.today()
    remaining_days = (next_task.duedate - today).days
    
    # Only create notifications for future due dates
    if remaining_days < 0:
        return
    
    users_to_notify = {next_task.owner} | set(next_task.collaborators or [])

    for user in users_to_notify:
        for days_before in TRIGGER_DAYS:
            # Calculate when this notification should trigger
            notif_trigger_date = next_task.duedate - timedelta(days=days_before)
            
            # Only create notification if trigger date is in the future or today
            if notif_trigger_date < today:
                continue
            
            payload = {
                "project_name": next_task.project.name if next_task.project else "No Project",
                "task_title": f"{next_task.title} (Recurring)",
                "duedate": next_task.duedate.isoformat() if next_task.duedate else None,
                "days_until_due": days_before,
                "is_recurring": True,
                "recurrence_type": next_task.recurrence_type.value if next_task.recurrence_type else None,
                "parent_task_id": original_task.id,
                "notification_trigger_date": notif_trigger_date.isoformat()
            }

            notif = Notification(
                user_id=user.id,
                task_id=next_task.id,
                trigger_days_before=days_before,
                payload=payload,
                type=NotificationType.DUE_DATE_REMINDER,
                created_at=datetime.combine(notif_trigger_date, datetime.min.time())
            )
            db.session.add(notif)
            print(f"DEBUG: Created recurring task notification for '{next_task.title}' - {days_before} days before due date")
    
    db.session.commit()
    

    create_recurring_task_creation_notification(next_task, original_task)
    

    if remaining_days <= 7 and remaining_days >= 0:
        create_due_date_reminder_notification(next_task, remaining_days)

def create_comment_notification(comment):
    task = comment.task
    if not task:
        return

    users_to_notify = {task.owner} | set(task.collaborators or [])
    # Exclude the user who made the comment
    users_to_notify = {user for user in users_to_notify if user.id != comment.user_id}

    print(f"DEBUG: Creating comment notification for task: {task.title}")
    print(f"DEBUG: Comment by: {comment.user.email}")
    print(f"DEBUG: Users to notify: {[user.email for user in users_to_notify]}")

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "comment_author": comment.user.email,
        "comment_excerpt": comment.content[:100] + "..." if len(comment.content) > 100 else comment.content,
        "comment_id": comment.id,
        "notification_type": "new_comment"
    }

    notifications_created = 0
    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            comment_id=comment.id,
            type=NotificationType.NEW_COMMENT
        )
        db.session.add(notif)
        notifications_created += 1
        print(f"DEBUG: Created comment notification for user: {user.email}")
    
    db.session.commit()
    print(f"DEBUG: Committed {notifications_created} comment notifications")
    
    print(f"DEBUG: Sending email notifications for comment")
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
        "updated_by": updated_by.email,
        "notification_type": "task_updated"
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            type=NotificationType.TASK_UPDATED 
        )
        db.session.add(notif)
        print(f"DEBUG: Added task update notification for user: {user.email}")
    
    db.session.commit()
    print(f"DEBUG: Committed {len(users_to_notify)} task update notifications")

def send_task_update_notification(task: Task, updated_by: User, updated_fields: list):
    """Send both in-app and email notifications for task updates"""
    # Create in-app notifications
    create_task_update_notification(task, updated_by, updated_fields)
    
    # Send email notifications
    send_task_update_email_notification(task, updated_by, updated_fields, updated_by.id)

def create_task_assignment_notification(task: Task, assigned_by: User, assignee: User, role="collaborator"):
    """Create in-app notification when someone is assigned to a task"""
    # Don't notify if the assignee is the same as the person assigning
    if assigned_by.id == assignee.id:
        return
    
    print(f"DEBUG: Creating task assignment notification for {assignee.email}")
    print(f"DEBUG: Task: {task.title}, Role: {role}, Assigned by: {assigned_by.email}")

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "assigned_by": assigned_by.email,
        "role": role,
        "notification_type": "task_assignment"
    }

    notif = Notification(
        user_id=assignee.id,
        task_id=task.id,
        payload=payload,
        type=NotificationType.TASK_ASSIGNMENT
    )
    db.session.add(notif)
    
    try:
        db.session.commit()
        print(f"DEBUG: Successfully created task assignment notification for {assignee.email}")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to create task assignment notification: {e}")

def create_project_assignment_notification(project: Project, assigned_by: User, assignee: User, role="collaborator"):
    """Create in-app notification when someone is assigned to a project"""
    # Don't notify if the assignee is the same as the person assigning
    if assigned_by.id == assignee.id:
        return
    
    print(f"DEBUG: Creating project assignment notification for {assignee.email}")
    print(f"DEBUG: Project: {project.name}, Role: {role}, Assigned by: {assigned_by.email}")

    payload = {
        "project_name": project.name,
        "assigned_by": assigned_by.email,
        "role": role,
        "notification_type": "project_assignment"
    }

    notif = Notification(
        user_id=assignee.id,
        project_id=project.id,
        payload=payload,
        type=NotificationType.PROJECT_ASSIGNMENT
    )
    db.session.add(notif)
    
    try:
        db.session.commit()
        print(f"DEBUG: Successfully created project assignment notification for {assignee.email}")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to create project assignment notification: {e}")

def send_task_assignment_notification(task: Task, assigned_by: User, assignee: User, role="collaborator"):
    """Send both in-app and email notifications for task assignment"""
    # Create in-app notification
    create_task_assignment_notification(task, assigned_by, assignee, role)
    
    # Send email notification
    send_task_assignment_email_notification(task, assigned_by, assignee)

def send_project_assignment_notification(project: Project, assigned_by: User, assignee: User, role="collaborator"):
    """Send both in-app and email notifications for project assignment"""
    # Create in-app notification
    create_project_assignment_notification(project, assigned_by, assignee, role)
    
    # Send email notification
    send_project_assignment_email_notification(project, assigned_by, assignee, role)

def send_task_creation_notification(task: Task, created_by: User):
    """Send both in-app and email notifications for task creation"""
    # Create in-app notification
    create_task_creation_notification(task, created_by)
    
    # Send email notification
    send_task_creation_email_notification(task, created_by)

def send_project_creation_notification(project: Project, created_by: User):
    """Send both in-app and email notifications for project creation"""
    # Create in-app notification
    create_project_creation_notification(project, created_by)
    
    # Send email notification
    send_project_creation_email_notification(project, created_by)

def send_project_update_notification(project: Project, updated_by: User, updated_fields: list):
    """Send both in-app and email notifications for project updates"""
    # Create in-app notification
    create_project_update_notification(project, updated_by, updated_fields)
    
    # Send email notification
    send_project_update_email_notification(project, updated_by, updated_fields)

def send_project_collaborator_notification(project: Project, added_by: User, new_collaborators: list):
    """Send both in-app and email notifications for new project collaborators"""
    # Create in-app notification
    create_project_collaborator_added_notification(project, added_by, new_collaborators)
    
    # Send email notification
    send_project_collaborator_added_email_notification(project, added_by, new_collaborators)

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

def send_recurring_task_created_email_notification(next_task: Task, original_task: Task):
    """Send email notification when a new recurring task is automatically created"""
    recipients = get_notification_recipients(next_task, None) 
    
    if not recipients:
        return
    
    subject = f"🔄 New recurring task created: {next_task.title}"
    
    message = f"""
    <strong>A new recurring task has been automatically created:</strong>
    
    <div class="task-info">
        <p><strong>Task:</strong> {next_task.title}</p>
        <p><strong>Description:</strong> {next_task.description or 'No description provided'}</p>
        <p><strong>Due Date:</strong> {next_task.duedate.strftime('%Y-%m-%d') if next_task.duedate else 'Not set'}</p>
        <p><strong>Priority:</strong> {next_task.priority}</p>
        <p><strong>Status:</strong> {next_task.status.value}</p>
        <p><strong>Recurrence:</strong> {next_task.recurrence_type.value if next_task.recurrence_type else 'None'}</p>
        <p><strong>Project:</strong> {next_task.project.name if next_task.project else 'No Project'}</p>
    </div>
    
    <strong>Team:</strong>
    <ul>
        <li>{next_task.owner.email} (Owner)</li>
        {"".join([f"<li>{collab.email} (Collaborator)</li>" for collab in next_task.collaborators])}
    </ul>
    
    <em>This recurring task was automatically generated from the completed task "{original_task.title}".</em>
    """
    
    email_service.send_notification_email(
        recipients,
        subject,
        message,
        next_task.title,
        next_task.id,
        "recurring_task_created"
    )

def create_project_creation_notification(project, created_by):
    """Create in-app notifications for project creation"""
    users_to_notify = {project.owner} | set(project.collaborators or [])
    # Exclude the user who created the project
    users_to_notify = {user for user in users_to_notify if user.id != created_by.id}
    
    print(f"DEBUG: Creating project creation notifications for '{project.name}'")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Users to notify: {[user.email for user in users_to_notify]}")

    payload = {
        "project_name": project.name,
        "created_by": created_by.email,
        "project_description": project.description or "No description",
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "status": project.status.value,
        "notification_type": "project_creation"
    }

    notifications_created = 0
    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            project_id=project.id, 
            task_id=None,
            payload=payload,
            type=NotificationType.PROJECT_UPDATED 
        )
        db.session.add(notif)
        notifications_created += 1
        print(f"DEBUG: Created project creation notification for user {user.email}")

    if notifications_created > 0:
        try:
            db.session.commit()
            print(f"DEBUG: Successfully committed {notifications_created} project creation notifications")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to commit project creation notifications: {e}")

def create_project_update_notification(project, updated_by, updated_fields):
    """Create in-app notifications for project updates"""
    users_to_notify = {project.owner} | set(project.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != updated_by.id}

    print(f"DEBUG: Creating project update notifications for: {project.name}")
    print(f"DEBUG: Updated by: {updated_by.email}")
    print(f"DEBUG: Updated fields: {[f['field'] for f in updated_fields]}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": project.name,
        "updated_fields": updated_fields,
        "updated_by": updated_by.email,
        "notification_type": "project_updated"
    }

    notifications_created = 0
    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            project_id=project.id, 
            task_id=None,
            payload=payload,
            type=NotificationType.PROJECT_UPDATED 
        )
        db.session.add(notif)
        notifications_created += 1
        print(f"DEBUG: Created project update notification for user: {user.email}")

    if notifications_created > 0:
        try:
            db.session.commit()
            print(f"DEBUG: Successfully committed {notifications_created} project update notifications")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to commit project update notifications: {e}")

def create_project_collaborator_added_notification(project, added_by, new_collaborators):
    """Create in-app notifications for new project collaborators"""
    if not new_collaborators:
        return

    print(f"DEBUG: Creating project collaborator added notifications for: {project.name}")
    print(f"DEBUG: Added by: {added_by.email}")
    print(f"DEBUG: New collaborators: {[c.email for c in new_collaborators]}")

    for collaborator in new_collaborators:
        if collaborator.id == added_by.id:
            continue
            
        payload = {
            "project_name": project.name,
            "added_by": added_by.email,
            "project_owner": project.owner.email,
            "notification_type": "project_collaborator_added"
        }

        notif = Notification(
            user_id=collaborator.id,
            project_id=project.id,  
            task_id=None,
            payload=payload,
            type=NotificationType.PROJECT_UPDATED 
        )
        db.session.add(notif)
        print(f"DEBUG: Created project collaborator notification for: {collaborator.email}")

    try:
        db.session.commit()
        print(f"DEBUG: Successfully committed project collaborator notifications")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to commit project collaborator notifications: {e}")

def create_task_attachment_notification(task: Task, added_by: User, attachment_filename: str):
    """Create in-app notification for task attachment addition"""
    users_to_notify = {task.owner} | set(task.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != added_by.id}

    print(f"DEBUG: Creating task attachment notification for task: {task.title}")
    print(f"DEBUG: Added by: {added_by.email}")
    print(f"DEBUG: Attachment: {attachment_filename}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "attachment_filename": attachment_filename,
        "added_by": added_by.email,
        "notification_type": "task_attachment_added"
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            type=NotificationType.TASK_UPDATED
        )
        db.session.add(notif)
        print(f"DEBUG: Added task attachment notification for user: {user.email}")
    
    db.session.commit()

def create_project_attachment_notification(project: Project, added_by: User, attachment_filename: str):
    """Create in-app notification for project attachment addition"""
    users_to_notify = {project.owner} | set(project.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != added_by.id}

    print(f"DEBUG: Creating project attachment notification for project: {project.name}")
    print(f"DEBUG: Added by: {added_by.email}")
    print(f"DEBUG: Attachment: {attachment_filename}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": project.name,
        "attachment_filename": attachment_filename,
        "added_by": added_by.email,
        "notification_type": "project_attachment_added"
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            project_id=project.id,
            payload=payload,
            type=NotificationType.PROJECT_UPDATED
        )
        db.session.add(notif)
        print(f"DEBUG: Added project attachment notification for user: {user.email}")
    
    db.session.commit()

def send_task_attachment_notification(task: Task, added_by: User, attachment_filename: str):
    """Send both in-app and email notifications for task attachment"""
    # Create in-app notification
    create_task_attachment_notification(task, added_by, attachment_filename)
    
    # Send email notification
    send_task_attachment_email_notification(task, added_by, attachment_filename)

def send_project_attachment_notification(project: Project, added_by: User, attachment_filename: str):
    """Send both in-app and email notifications for project attachment"""
    # Create in-app notification
    create_project_attachment_notification(project, added_by, attachment_filename)
    
    # Send email notification
    send_project_attachment_email_notification(project, added_by, attachment_filename)

def create_task_attachment_removal_notification(task: Task, removed_by: User, attachment_filename: str):
    """Create in-app notification for task attachment removal"""
    users_to_notify = {task.owner} | set(task.collaborators or [])
    users_to_notify = {user for user in users_to_notify if user.id != removed_by.id}

    print(f"DEBUG: Creating task attachment REMOVAL notification for task: {task.title}")
    print(f"DEBUG: Removed by: {removed_by.email}")
    print(f"DEBUG: Attachment: {attachment_filename}")
    print(f"DEBUG: Users to notify: {[u.email for u in users_to_notify]}")

    payload = {
        "project_name": task.project.name if task.project else "No Project",
        "task_title": task.title,
        "attachment_filename": attachment_filename,
        "removed_by": removed_by.email,
        "notification_type": "task_attachment_removed"
    }

    for user in users_to_notify:
        notif = Notification(
            user_id=user.id,
            task_id=task.id,
            payload=payload,
            type=NotificationType.TASK_UPDATED
        )
        db.session.add(notif)
        print(f"DEBUG: Added task attachment REMOVAL notification for user: {user.email}")
    
    db.session.commit()
    print(f"DEBUG: Successfully committed task attachment removal notifications")

def send_task_attachment_removal_notification(task: Task, removed_by: User, attachment_filename: str):
    """Send both in-app and email notifications for task attachment removal"""
    # Create in-app notification
    create_task_attachment_removal_notification(task, removed_by, attachment_filename)
    
    # Send email notification
    send_task_attachment_removal_email_notification(task, removed_by, attachment_filename)