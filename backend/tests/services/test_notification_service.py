import pytest
from datetime import date, timedelta, datetime, timezone
from app import create_app, db
from app.models import User, Task, Project, Notification, TaskStatus, Comment, NotificationType
from app.services import notification_service

@pytest.fixture
def app():
    """Create a temporary Flask app and in-memory database for tests."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_SECRET_KEY": "test-key",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def sample_user(app):
    user = User(email="user1@example.com", password_hash="dummy", name="User 1")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def sample_project(app, sample_user):
    project = Project(name="Project Alpha", description="Test project", owner_id=sample_user.id)
    db.session.add(project)
    db.session.commit()
    return project

@pytest.fixture
def sample_task(app, sample_user, sample_project):
    task = Task(
        title="Test Task",
        duedate=date.today() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()
    return task

def test_notifications_only_1_3_7_days(app, sample_user, sample_project):
    task = Task(
        title="Task 4 Days",
        duedate=date.today() + timedelta(days=4),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()

    notification_service.create_notifications_for_task(task)

    notifs = Notification.query.filter_by(task_id=task.id).all()
    days_before = sorted([n.trigger_days_before for n in notifs if n.trigger_days_before is not None])
    # Should only create notification for 3 days before (not 1 or 7)
    assert days_before == [3]

def test_notifications_only_for_involved_users(app, sample_user, sample_project):
    other_user = User(email="other@example.com", password_hash="dummy", name="Other")
    db.session.add(other_user)
    db.session.commit()

    task = Task(
        title="Shared Task",
        duedate=date.today() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    task.collaborators.append(other_user)
    db.session.add(task)
    db.session.commit()

    notification_service.create_notifications_for_task(task)

    recipients = {n.user_id for n in Notification.query.filter_by(task_id=task.id).all()}
    assert sample_user.id in recipients
    assert other_user.id in recipients
    assert len(recipients) == 2

def test_no_notifications_for_completed_tasks(app, sample_user, sample_project):
    task = Task(
        title="Completed Task",
        duedate=date.today() + timedelta(days=3),
        status=TaskStatus.COMPLETED,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()

    notification_service.create_notifications_for_task(task)
    notifs = Notification.query.filter_by(task_id=task.id).all()
    assert len(notifs) == 0

def test_notifications_update_on_due_date_change(app, sample_user, sample_project):
    task = Task(
        title="Task Update Due Date",
        duedate=date.today() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()

    notification_service.create_notifications_for_task(task)

    task.duedate = date.today() + timedelta(days=3)
    db.session.commit()
    notification_service.update_notifications_for_task(task)

    new_notifs = Notification.query.filter_by(task_id=task.id).all()
    new_days = sorted([n.trigger_days_before for n in new_notifs if n.trigger_days_before is not None])
    assert new_days == [3]

def test_notifications_removed_when_task_deleted(app, sample_user, sample_project):
    task = Task(
        title="Task for Deletion",
        duedate=date.today() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()

    notification_service.create_notifications_for_task(task)
    notif_count = Notification.query.filter_by(task_id=task.id).count()
    assert notif_count > 0

    db.session.delete(task)
    db.session.commit()

    remaining_notifs = Notification.query.filter_by(task_id=task.id).count()
    assert remaining_notifs == 0

def test_create_comment_notification_excludes_author(app, sample_user, sample_project):
    other_user = User(email="collab@example.com", password_hash="pwd", name="Collab")
    db.session.add(other_user)
    db.session.commit()

    task = Task(
        title="Commented",
        duedate=date.today() + timedelta(days=3),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    task.collaborators.append(other_user)
    db.session.add(task)
    db.session.commit()

    comment = Comment(task_id=task.id, user_id=sample_user.id, content="A" * 120)
    db.session.add(comment)
    db.session.commit()

    notification_service.create_comment_notification(comment)

    notifs = Notification.query.filter_by(task_id=task.id).all()
    assert len(notifs) == 1
    assert notifs[0].user_id == other_user.id
    assert notifs[0].payload["comment_excerpt"].endswith("...")

def test_create_task_update_notification_skips_updater(app, sample_user, sample_project):
    other_user = User(email="collab2@example.com", password_hash="pwd", name="Collab2")
    db.session.add(other_user)
    db.session.commit()

    task = Task(
        title="Updated Task",
        duedate=date.today() + timedelta(days=4),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    task.collaborators.append(other_user)
    db.session.add(task)
    db.session.commit()

    notification_service.create_task_update_notification(
        task,
        updated_by=sample_user,
        updated_fields=[{"field": "status", "old_value": "old", "new_value": "new"}],
    )

    notif = Notification.query.filter_by(task_id=task.id).first()
    assert notif.user_id == other_user.id
    assert notif.payload["updated_by"] == sample_user.email

def test_create_task_assignment_notification_skips_same_owner(app, sample_user, sample_project):
    task = Task(
        title="Assignment",
        duedate=date.today() + timedelta(days=4),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()

    notification_service.create_task_assignment_notification(task, assigned_by=sample_user, assignee=sample_user)
    assert Notification.query.filter_by(task_id=task.id).count() == 0

    other = User(email="assignee@example.com", password_hash="pwd", name="Assignee")
    db.session.add(other)
    db.session.commit()

    notification_service.create_task_assignment_notification(task, assigned_by=sample_user, assignee=other)
    notif = Notification.query.filter_by(task_id=task.id).first()
    assert notif.user_id == other.id
    assert notif.payload["assigned_by"] == sample_user.email

def test_mark_notification_as_read(app, sample_user, sample_task):
    # Create a notification first
    notification = Notification(
        user_id=sample_user.id,
        task_id=sample_task.id,
        type=NotificationType.DUE_DATE_REMINDER,
        payload={"test": "data"}
    )
    db.session.add(notification)
    db.session.commit()

    # Mark as read using db.session.get() instead of Query.get()
    notif = db.session.get(Notification, notification.id)
    notif.is_read = True
    db.session.commit()
    
    # Verify it's marked as read
    updated_notif = db.session.get(Notification, notification.id)
    assert updated_notif.is_read == True

def test_mark_all_notifications_as_read(app, sample_user, sample_task):
    # Create multiple notifications
    for i in range(3):
        notification = Notification(
            user_id=sample_user.id,
            task_id=sample_task.id,
            type=NotificationType.DUE_DATE_REMINDER,
            payload={"test": f"data{i}"}
        )
        db.session.add(notification)
    db.session.commit()

    # Mark all as read
    Notification.query.filter_by(user_id=sample_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    
    unread_count = Notification.query.filter_by(user_id=sample_user.id, is_read=False).count()
    assert unread_count == 0

def test_get_notifications_for_user(app, sample_user, sample_task):
    # Create notifications
    for i in range(2):
        notification = Notification(
            user_id=sample_user.id,
            task_id=sample_task.id,
            type=NotificationType.DUE_DATE_REMINDER,
            payload={"test": f"data{i}"}
        )
        db.session.add(notification)
    db.session.commit()

    notifications = notification_service.get_notifications_for_user(sample_user.id)
    assert len(notifications) == 2