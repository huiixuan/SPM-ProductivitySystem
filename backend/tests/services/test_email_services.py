import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import time
from app import create_app, db
from app.models import User, Task, Project, TaskStatus, ProjectStatus, Comment
from app.services.email_services import (
    EmailService,
    get_notification_recipients,
    send_comment_email_notification,
    send_task_update_email_notification,
    send_task_creation_email_notification,
    get_project_notification_recipients,
    send_due_date_reminder_email,
    send_task_assignment_email_notification,
    send_project_creation_email_notification,
    send_project_update_email_notification,
    send_project_collaborator_added_email_notification,
    send_project_assignment_email_notification,
    send_task_attachment_email_notification,
    send_project_attachment_email_notification,
    send_task_attachment_removal_email_notification
)

@pytest.fixture
def app():
    """Create a temporary Flask app and in-memory database for tests."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_SECRET_KEY": "test-key",
        "POWER_AUTOMATE_WEBHOOK_URL": "https://test-webhook.com"
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
def sample_user2(app):
    user = User(email="user2@example.com", password_hash="dummy", name="User 2")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def sample_project(app, sample_user):
    project = Project(
        name="Test Project", 
        description="Test project", 
        owner_id=sample_user.id,
        status=ProjectStatus.IN_PROGRESS
    )
    db.session.add(project)
    db.session.commit()
    return project

@pytest.fixture
def sample_task(app, sample_user, sample_project):
    task = Task(
        title="Test Task",
        description="Test Description",
        duedate=datetime.now(timezone.utc).date() + timedelta(days=7),
        status=TaskStatus.ONGOING,
        owner_id=sample_user.id,
        project_id=sample_project.id,
        priority=1
    )
    db.session.add(task)
    db.session.commit()
    return task

@pytest.fixture
def sample_comment(app, sample_user, sample_task):
    comment = Comment(
        task_id=sample_task.id,
        user_id=sample_user.id,
        content="Test comment content"
    )
    db.session.add(comment)
    db.session.commit()
    return comment

def test_email_service_initialization():
    """Test EmailService initialization"""
    service = EmailService()
    assert service.cooldown == 60
    assert service.last_sent == {}
    
def test_can_send_email_immediate_for_comments():
    """Test that comments can be sent immediately (no cooldown)"""
    service = EmailService()
    assert service.can_send_email(1, "test@example.com", "new_comment") == True
    assert service.can_send_email(1, "test@example.com", "task_updated") == True
    assert service.can_send_email(1, "test@example.com", "task_creation") == True
    
def test_can_send_email_cooldown_respected():
    """Test cooldown is respected for non-comment notifications"""
    service = EmailService()
    key = "1_test@example.com_due_date_reminder"
    
    # First attempt should work
    assert service.can_send_email(1, "test@example.com", "due_date_reminder") == True
    
    # Second attempt immediately should be blocked by cooldown
    assert service.can_send_email(1, "test@example.com", "due_date_reminder") == False
    
@patch('app.services.email_services.requests.post')
def test_send_notification_email_success(mock_post):
    """Test successful email sending"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    service = EmailService()
    service.power_automate_webhook_url = "https://test-webhook.com"
    service.enabled = True
    
    result = service.send_notification_email(
        ["test@example.com"],
        "Test Subject",
        "Test Message",
        "Test Task",
        1,
        "test_notification"
    )
    
    assert result == True
    mock_post.assert_called_once()
    
@patch('app.services.email_services.requests.post')
def test_send_notification_email_disabled(mock_post):
    """Test email sending when service is disabled"""
    service = EmailService()
    service.enabled = False
    
    result = service.send_notification_email(
        ["test@example.com"],
        "Test Subject",
        "Test Message",
        "Test Task",
        1,
        "test_notification"
    )
    
    assert result == False
    mock_post.assert_not_called()
    
@patch('app.services.email_services.requests.post')
def test_send_notification_email_no_recipients(mock_post):
    """Test email sending with no recipients"""
    service = EmailService()
    service.enabled = True
    
    result = service.send_notification_email(
        [],
        "Test Subject",
        "Test Message",
        "Test Task",
        1,
        "test_notification"
    )
    
    assert result == False
    mock_post.assert_not_called()

@patch('app.services.email_services.requests.post')
def test_send_notification_email_cooldown_filtered(mock_post):
    """Test email sending when recipients are filtered due to cooldown"""
    service = EmailService()
    service.enabled = True
    
    # First send to trigger cooldown
    service.send_notification_email(
        ["test@example.com"],
        "Test Subject",
        "Test Message",
        "Test Task",
        1,
        "due_date_reminder"
    )
    
    # Second send immediately - should be filtered out
    result = service.send_notification_email(
        ["test@example.com"],
        "Test Subject",
        "Test Message",
        "Test Task",
        1,
        "due_date_reminder"
    )
    
    assert result == False
    mock_post.assert_called_once()  # Only first call should happen

@patch('app.services.email_services.requests.post')
def test_send_notification_email_request_failure(mock_post):
    """Test email service handles request failures gracefully"""
    mock_post.side_effect = Exception("Network error")
    
    service = EmailService()
    service.power_automate_webhook_url = "https://test-webhook.com"
    service.enabled = True
    
    result = service.send_notification_email(
        ["test@example.com"],
        "Test Subject",
        "Test Message",
        "Test Task",
        1,
        "test_notification"
    )
    
    assert result == False

def test_email_service_cooldown_expiry():
    """Test that cooldown expires after time"""
    service = EmailService()
    service.cooldown = 0.1  # Very short cooldown for testing
    
    # First attempt
    assert service.can_send_email(1, "test@example.com", "due_date_reminder") == True
    
    # Second attempt immediately should be blocked
    assert service.can_send_email(1, "test@example.com", "due_date_reminder") == False
    
    # Wait for cooldown to expire
    time.sleep(0.2)
    
    # Should work again
    assert service.can_send_email(1, "test@example.com", "due_date_reminder") == True

def test_get_notification_recipients_excludes_trigger_user(app, sample_user, sample_user2, sample_task):
    """Test that notification recipients exclude the user who triggered the event"""
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    recipients = get_notification_recipients(sample_task, sample_user.id)
    
    # Should include user2 but not user1 (who triggered the event)
    assert sample_user2.email in recipients
    assert sample_user.email not in recipients
    assert len(recipients) == 1

def test_get_notification_recipients_only_owner(app, sample_user, sample_task):
    """Test notification recipients when only owner exists"""
    recipients = get_notification_recipients(sample_task, None)
    
    assert sample_user.email in recipients
    assert len(recipients) == 1

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_comment_email_notification(mock_send_email, app, sample_user, sample_user2, sample_task, sample_comment):
    """Test comment email notification"""
    mock_send_email.return_value = True
    
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    send_comment_email_notification(sample_comment, sample_task, sample_user.id)
    
    # Should send email to user2 but not user1
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "comment" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_task_update_email_notification(mock_send_email, app, sample_user, sample_user2, sample_task):
    """Test task update email notification"""
    mock_send_email.return_value = True
    
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    updated_fields = [
        {
            "field": "status",
            "old_value": "Ongoing",
            "new_value": "Completed"
        }
    ]
    
    send_task_update_email_notification(sample_task, sample_user, updated_fields, sample_user.id)
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "updated" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_task_creation_email_notification(mock_send_email, app, sample_user, sample_user2, sample_task):
    """Test task creation email notification"""
    mock_send_email.return_value = True
    
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    send_task_creation_email_notification(sample_task, sample_user)
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "created" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_due_date_reminder_email(mock_send_email, app, sample_user, sample_user2, sample_task):
    """Test due date reminder email"""
    mock_send_email.return_value = True
    
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    send_due_date_reminder_email(sample_task, 3)
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user.email in call_args[0]  # recipients
    assert "due" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_task_assignment_email_notification(mock_send_email, app, sample_user, sample_user2, sample_task):
    """Test task assignment email notification"""
    mock_send_email.return_value = True
    
    send_task_assignment_email_notification(sample_task, sample_user, sample_user2)
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "assignment" in call_args[1].lower()  # subject

def test_get_project_notification_recipients(app, sample_user, sample_user2, sample_project):
    """Test project notification recipients"""
    sample_project.collaborators.append(sample_user2)
    db.session.commit()
    
    recipients = get_project_notification_recipients(sample_project, sample_user.id)
    
    # Should include user2 but not user1 (who triggered the event)
    assert sample_user2.email in recipients
    assert sample_user.email not in recipients
    assert len(recipients) == 1

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_project_creation_email_notification(mock_send_email, app, sample_user, sample_user2, sample_project):
    """Test project creation email notification"""
    mock_send_email.return_value = True
    
    sample_project.collaborators.append(sample_user2)
    db.session.commit()
    
    send_project_creation_email_notification(sample_project, sample_user)
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "created" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_project_update_email_notification(mock_send_email, app, sample_user, sample_user2, sample_project):
    """Test project update email notification"""
    mock_send_email.return_value = True
    
    sample_project.collaborators.append(sample_user2)
    db.session.commit()
    
    updated_fields = [
        {
            "field": "status",
            "old_value": "In Progress",
            "new_value": "Completed"
        }
    ]
    
    send_project_update_email_notification(sample_project, sample_user, updated_fields)
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "updated" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_project_collaborator_added_email_notification(mock_send_email, app, sample_user, sample_user2, sample_project):
    """Test project collaborator added email notification"""
    mock_send_email.return_value = True
    
    send_project_collaborator_added_email_notification(sample_project, sample_user, [sample_user2])
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "added" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_project_assignment_email_notification(mock_send_email, app, sample_user, sample_user2, sample_project):
    """Test project assignment email notification"""
    mock_send_email.return_value = True
    
    send_project_assignment_email_notification(sample_project, sample_user, sample_user2, "collaborator")
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "assigned" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_task_attachment_email_notification(mock_send_email, app, sample_user, sample_user2, sample_task):
    """Test task attachment email notification"""
    mock_send_email.return_value = True
    
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    send_task_attachment_email_notification(sample_task, sample_user, "test_file.pdf")
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "attachment" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_project_attachment_email_notification(mock_send_email, app, sample_user, sample_user2, sample_project):
    """Test project attachment email notification"""
    mock_send_email.return_value = True
    
    sample_project.collaborators.append(sample_user2)
    db.session.commit()
    
    send_project_attachment_email_notification(sample_project, sample_user, "test_file.pdf")
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "attachment" in call_args[1].lower()  # subject

@patch('app.services.email_services.email_service.send_notification_email')
def test_send_task_attachment_removal_email_notification(mock_send_email, app, sample_user, sample_user2, sample_task):
    """Test task attachment removal email notification"""
    mock_send_email.return_value = True
    
    sample_task.collaborators.append(sample_user2)
    db.session.commit()
    
    send_task_attachment_removal_email_notification(sample_task, sample_user, "test_file.pdf")
    
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args[0]
    assert sample_user2.email in call_args[0]  # recipients
    assert "removed" in call_args[1].lower()  # subject