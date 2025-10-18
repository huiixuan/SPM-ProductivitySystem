# backend/tests/test_notifications.py

import pytest
from datetime import date, timedelta
from app import create_app, db
from app.models import db, User, Task, Project, Notification, TaskStatus
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

def test_notifications_only_1_3_7_days(app, sample_user, sample_project):
    # Due in 4 days
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
    assert len(notifs) == 2 # Only 3 and 1 day notifications
    days_before = sorted([n.trigger_days_before for n in notifs])
    assert days_before == [1, 3]

    # Due in 7 days — should create 3 notifications
    task2 = Task(
        title="Task 7 Days",
        duedate=date.today() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task2)
    db.session.commit()

    notification_service.create_notifications_for_task(task2)

    notifs = Notification.query.filter_by(task_id=task2.id).all()
    days_before = sorted([n.trigger_days_before for n in notifs])
    assert days_before == [1, 3, 7]

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
    assert len(recipients) == 2  # only owner + collaborator

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
    assert len(notifs) == 0  # completed tasks skipped

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
    old_count = Notification.query.filter_by(task_id=task.id).count()
    assert old_count == 3

    # Change due date to 3 days from now
    task.duedate = date.today() + timedelta(days=3)
    db.session.commit()
    notification_service.update_notifications_for_task(task)

    new_notifs = Notification.query.filter_by(task_id=task.id).all()
    new_days = sorted([n.trigger_days_before for n in new_notifs])
    assert new_days == [1, 3]  # updated schedule reflects new due date

def test_notifications_removed_when_task_deleted(app, sample_user, sample_project):
    # Create a task due in 7 days → should have 3 notifications
    task = Task(
        title="Task for Deletion",
        duedate=date.today() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
    )
    db.session.add(task)
    db.session.commit()

    # Create notifications
    notification_service.create_notifications_for_task(task)
    notif_count = Notification.query.filter_by(task_id=task.id).count()
    assert notif_count == 3  # confirm created

    # Delete task
    db.session.delete(task)
    db.session.commit()

    # Check that notifications were removed automatically
    remaining_notifs = Notification.query.filter_by(task_id=task.id).count()
    assert remaining_notifs == 0  # no notifications remain

