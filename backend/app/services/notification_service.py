from datetime import date, datetime, timedelta
from app.models import db, Notification, Task, TaskStatus

TRIGGER_DAYS = [7, 3, 1]


def create_notifications_for_task(task: Task):
    """
    Creates notification records for all relevant users (owner + collaborators)
    at 7, 3, and 1 days before task's due date.
    Skips if task is completed or has no due date.
    """
    if not task or not task.duedate:
        return
    
    # Skip if completed
    if task.status == TaskStatus.COMPLETED:
        return

    users_to_notify = {task.owner} | set(task.collaborators or [])

    for user in users_to_notify:
        for days_before in TRIGGER_DAYS:
            # Build payload
            payload = Notification.build_payload(
                project_name=task.project.name if task.project else "No Project",
                task_title=task.title,
                duedate=task.duedate
            )

            # Check for existing notification (prevent duplicates)
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
                    payload=payload
                )
                db.session.add(notif)
    
    db.session.commit()

    print(f"✅ Created notifications for task '{task.title}':")
    for n in Notification.query.filter_by(task_id=task.id).all():
        print(f"  - User {n.user_id} | {n.payload}")



def remove_notifications_for_task(task: Task):
    """
    Deletes all notifications for a given task.
    Useful when a task is deleted or completed.
    """
    if not task:
        return
    Notification.query.filter_by(task_id=task.id).delete()
    db.session.commit()



def update_notifications_for_task(task: Task):
    """
    Recreates notifications when the task's due date changes.
    """
    if not task:
        return
    
    # Remove old ones first
    Notification.query.filter_by(task_id=task.id).delete()
    db.session.commit()

    # Recreate if still relevant
    create_notifications_for_task(task)



def get_notifications_for_user(user_id: int):
    """
    Returns unread + read notifications for a user, sorted by recency.
    """
    return (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )



def mark_notification_as_read(notification_id: int):
    """
    Marks a single notification as read.
    """
    notif = Notification.query.get(notification_id)
    if notif:
        notif.is_read = True
        db.session.commit()
    return notif
