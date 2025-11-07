import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from dateutil.relativedelta import relativedelta
import io

from app.models import db, Task, Attachment, User, Project, RecurrenceType, TaskStatus
from flask import Flask, Request
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import create_access_token


class TestTaskServices:
    
    @pytest.fixture
    def app(self):
        """Create Flask application for testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.app_context():
            yield app

    @pytest.fixture
    def mock_request(self, app):
        """Mock request context"""
        with app.test_request_context() as ctx:
            mock_request = Mock(spec=Request)
            mock_request.files = {}
            with patch('app.services.task_services.request', mock_request):
                yield mock_request
    
    @pytest.fixture
    def mock_db(self, app):
        with app.app_context(), patch('app.services.task_services.db') as mock:
            mock.session.add = Mock()
            mock.session.commit = Mock()
            mock.session.rollback = Mock()
            mock.session.delete = Mock()
            yield mock
    
    @pytest.fixture
    def mock_get_user_by_email(self):
        with patch('app.services.task_services.get_user_by_email') as mock:
            yield mock
    
    @pytest.fixture
    def mock_get_jwt_identity(self):
        with patch('app.services.task_services.get_jwt_identity') as mock:
            yield mock
    
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user._sa_instance_state = Mock()  # Add SQLAlchemy internal attribute
        return user
    
    @pytest.fixture
    def mock_task(self):
        task = Mock(spec=Task)
        task.id = 1
        task.title = "Test Task"
        task.description = "Test Description"
        task.duedate = datetime.now() + timedelta(days=7)
        task.status = TaskStatus.UNASSIGNED
        task.owner_id = 1
        task.owner = Mock(spec=User)
        task.owner.id = 1
        task.owner.email = "owner@example.com"
        task.collaborators = []
        task.attachments = []
        task.notes = ""
        task.priority = 1
        task.isRecurring = False
        task.recurrence_type = RecurrenceType.NONE
        task.recurrence_interval = None
        task.parent_id = None
        task.project_id = None
        task.project = None
        task._sa_instance_state = Mock()  # Add SQLAlchemy internal attribute
        return task
    
    @pytest.fixture
    def mock_project(self):
        project = Mock(spec=Project)
        project.id = 1
        project.name = "Test Project"
        project._sa_instance_state = Mock()  # Add SQLAlchemy internal attribute
        return project
    
    @pytest.fixture
    def mock_attachment(self):
        attachment = Mock(spec=Attachment)
        attachment.id = 1
        attachment.filename = "test.txt"
        attachment.content = b"test content"
        attachment._sa_instance_state = Mock()  # Add SQLAlchemy internal attribute
        return attachment

    # Test _NotificationFacade class
    def test_notification_facade_methods(self, app):
        with app.app_context():
            from app.services.task_services import _NotificationFacade
            
            facade = _NotificationFacade()
            
            # Test that all methods call their respective functions
            test_cases = [
                ('create_notifications_for_task', ['task']),
                ('remove_notifications_for_task', ['task']),
                ('update_notifications_for_task', ['task']),
                ('create_comment_notification', ['task', 'user', 'comment']),
                ('create_task_update_notification', ['task', 'user', 'changes']),
                ('create_task_assignment_notification', ['task', 'user', 'assignee', 'role'])
            ]
            
            for method_name, args in test_cases:
                with patch(f'app.services.task_services.{method_name}') as mock_method:
                    getattr(facade, method_name)(*args)
                    mock_method.assert_called_once_with(*args)

    # Test create_task function
    def test_create_task_success(self, app):
        with app.app_context():
            from app.services.task_services import create_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            mock_owner.email = "owner@example.com"
            
            mock_collaborator = Mock(spec=User)
            mock_collaborator.id = 2
            mock_collaborator.email = "collab@example.com"
            
            with patch('app.services.task_services.get_user_by_email') as mock_get_user:
                mock_get_user.side_effect = lambda email: {
                    "owner@example.com": mock_owner,
                    "collab@example.com": mock_collaborator
                }.get(email)
                
                with patch('app.services.task_services.get_jwt_identity') as mock_jwt:
                    mock_jwt.return_value = 1
                    
                    with patch('app.services.task_services.User.query') as mock_user_query:
                        mock_current_user = Mock(spec=User)
                        mock_current_user.id = 1
                        mock_current_user.email = "current@example.com"
                        mock_user_query.get.return_value = mock_current_user
                        
                        with patch('app.services.task_services.Task') as mock_task_class:
                            mock_task_instance = Mock()
                            mock_task_instance.owner = mock_owner
                            mock_task_instance.collaborators = [mock_collaborator]
                            mock_task_instance.attachments = []
                            mock_task_class.return_value = mock_task_instance
                            
                            with patch('app.services.task_services.db') as mock_db, \
                                patch('app.services.task_services.create_notifications_for_task') as mock_create_notifs:
                                
                                # Mock notification functions from notification_services
                                with patch('app.services.notification_services.send_task_creation_notification') as mock_send_creation, \
                                     patch('app.services.notification_services.send_task_assignment_notification') as mock_send_assign:
                                    
                                    # Test data
                                    result = create_task(
                                        title="Test Task",
                                        description="Test Description",
                                        duedate=datetime.now() + timedelta(days=7),
                                        status=TaskStatus.UNASSIGNED,
                                        owner_email="owner@example.com",
                                        collaborator_emails=["collab@example.com"],
                                        attachments=[],
                                        notes="Test notes",
                                        priority=1
                                    )
                                    
                                    # Assertions
                                    assert result == mock_task_instance
                                    mock_task_class.assert_called_once()
                                    mock_db.session.add.assert_any_call(mock_task_instance)
                                    mock_db.session.commit.assert_called_once()

    def test_create_task_with_attachments(self, app):
        with app.app_context():
            from app.services.task_services import create_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            mock_owner.email = "owner@example.com"
            
            with patch('app.services.task_services.get_user_by_email') as mock_get_user:
                mock_get_user.return_value = mock_owner
                
                with patch('app.services.task_services.get_jwt_identity') as mock_jwt:
                    mock_jwt.return_value = 1
                    
                    with patch('app.services.task_services.User.query') as mock_user_query:
                        mock_current_user = Mock(spec=User)
                        mock_current_user.id = 1
                        mock_user_query.get.return_value = mock_current_user
                        
                        # Mock file attachment
                        mock_file = Mock()
                        mock_file.filename = "test.txt"
                        mock_file.read.return_value = b"test content"
                        
                        with patch('app.services.task_services.Task') as mock_task_class, \
                             patch('app.services.task_services.Attachment') as mock_attachment_class, \
                             patch('app.services.task_services.db') as mock_db:
                            
                            # Mock ALL notification functions
                            with patch('app.services.task_services.create_notifications_for_task'), \
                                 patch('app.services.notification_services.send_task_creation_notification'), \
                                 patch('app.services.notification_services.send_task_assignment_notification'), \
                                 patch('app.services.notification_services.send_task_attachment_notification') as mock_send_attach:
                                
                                mock_task_instance = Mock()
                                mock_task_instance.owner = mock_owner
                                mock_task_instance.collaborators = []
                                mock_task_instance.attachments = []
                                mock_task_class.return_value = mock_task_instance
                                
                                mock_attachment_instance = Mock()
                                mock_attachment_class.return_value = mock_attachment_instance
                                
                                # Call function with attachments
                                result = create_task(
                                    title="Test Task",
                                    description="Test Description",
                                    duedate=datetime.now(),
                                    status=TaskStatus.UNASSIGNED,
                                    owner_email="owner@example.com",
                                    collaborator_emails=[],
                                    attachments=[mock_file],
                                    notes="",
                                    priority=1
                                )
                                
                                # Assertions
                                mock_attachment_class.assert_called_once_with(
                                    filename="test.txt",
                                    content=b"test content",
                                    task=mock_task_instance
                                )
                                mock_db.session.add.assert_any_call(mock_attachment_instance)

    def test_create_task_owner_not_found(self, app):
        with app.app_context():
            from app.services.task_services import create_task
            
            with patch('app.services.task_services.get_user_by_email') as mock_get_user:
                mock_get_user.return_value = None
                
                with pytest.raises(ValueError, match="Owner with email owner@example.com not found"):
                    create_task(
                        title="Test Task",
                        description="Test Description",
                        duedate=datetime.now(),
                        status=TaskStatus.UNASSIGNED,
                        owner_email="owner@example.com",
                        collaborator_emails=[],
                        attachments=[],
                        notes="",
                        priority=1
                    )

    def test_create_task_with_project(self, app):
        with app.app_context():
            from app.services.task_services import create_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            mock_owner.email = "owner@example.com"
            
            mock_project = Mock(spec=Project)
            mock_project.id = 1
            
            with patch('app.services.task_services.get_user_by_email') as mock_get_user:
                mock_get_user.return_value = mock_owner
                
                with patch('app.services.task_services.get_jwt_identity') as mock_jwt:
                    mock_jwt.return_value = 1
                    
                    with patch('app.services.task_services.User.query') as mock_user_query:
                        mock_user_query.get.return_value = Mock(spec=User)
                        
                        with patch('app.services.task_services.Task') as mock_task_class, \
                             patch('app.services.task_services.Project.query') as mock_project_query, \
                             patch('app.services.task_services.db') as mock_db:
                            
                            # Mock ALL notification functions to avoid real DB calls
                            with patch('app.services.task_services.create_notifications_for_task'), \
                                 patch('app.services.notification_services.send_task_creation_notification'), \
                                 patch('app.services.notification_services.send_task_assignment_notification'), \
                                 patch('app.services.notification_services.send_task_attachment_notification'):
                                
                                mock_project_query.get.return_value = mock_project
                                
                                mock_task_instance = Mock()
                                mock_task_instance.owner = mock_owner
                                mock_task_instance.collaborators = []
                                mock_task_instance.attachments = []
                                mock_task_class.return_value = mock_task_instance
                                
                                # Call function with project_id
                                result = create_task(
                                    title="Test Task",
                                    description="Test Description",
                                    duedate=datetime.now(),
                                    status=TaskStatus.UNASSIGNED,
                                    owner_email="owner@example.com",
                                    collaborator_emails=[],
                                    attachments=[],
                                    notes="",
                                    priority=1,
                                    project_id=1
                                )
                                
                                # Assertions - Project.query.get should be called
                                mock_project_query.get.assert_called_once_with(1)
                                # The task should have the project assigned
                                assert mock_task_instance.project == mock_project

    def test_create_task_database_error(self, app):
        with app.app_context():
            from app.services.task_services import create_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            mock_owner.email = "owner@example.com"
            
            with patch('app.services.task_services.get_user_by_email') as mock_get_user:
                mock_get_user.return_value = mock_owner
                
                with patch('app.services.task_services.get_jwt_identity') as mock_jwt:
                    mock_jwt.return_value = 1
                    
                    with patch('app.services.task_services.User.query') as mock_user_query:
                        mock_user_query.get.return_value = Mock(spec=User)
                        
                        with patch('app.services.task_services.Task') as mock_task_class, \
                            patch('app.services.task_services.db') as mock_db:
                            
                            mock_task_instance = Mock()
                            mock_task_instance.owner = mock_owner
                            mock_task_instance.collaborators = []
                            mock_task_instance.attachments = []
                            mock_task_class.return_value = mock_task_instance
                            
                            mock_db.session.commit.side_effect = SQLAlchemyError("DB Error")
                            
                            with pytest.raises(RuntimeError, match="Database error while creating task"):
                                create_task(
                                    title="Test Task",
                                    description="Test Description",
                                    duedate=datetime.now(),
                                    status=TaskStatus.UNASSIGNED,
                                    owner_email="owner@example.com",
                                    collaborator_emails=[],
                                    attachments=[],
                                    notes="",
                                    priority=1
                                )
                            
                            mock_db.session.rollback.assert_called_once()

    def test_create_next_recurring_task_daily(self, app):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            
            mock_task = Mock(spec=Task)
            mock_task.title = "Test Task"
            mock_task.description = "Test Description"
            mock_task.duedate = datetime(2023, 1, 1)
            mock_task.status = TaskStatus.UNASSIGNED
            mock_task.priority = 1
            mock_task.owner = mock_owner
            mock_task.notes = "Test notes"
            mock_task.project = None
            mock_task.isRecurring = True
            mock_task.recurrence_type = RecurrenceType.DAILY
            mock_task.recurrence_interval = None
            mock_task.collaborators = []
            mock_task.attachments = []
            
            with patch('app.services.task_services.Task') as mock_task_class, \
                patch('app.services.task_services.db.session.add') as mock_add, \
                patch('app.services.task_services.db.session.commit') as mock_commit, \
                patch('app.services.task_services.create_recurring_task_creation_notification') as mock_recur_notif, \
                patch('app.services.notification_services.create_notifications_for_task') as mock_create_notifs:  # Patch in notification_services!
                
                mock_next_task = Mock()
                mock_next_task.collaborators = []
                mock_next_task.duedate = datetime(2023, 1, 2)  # Set duedate
                mock_next_task.status = TaskStatus.UNASSIGNED  # Set status
                mock_next_task.id = 2  # Set id
                mock_task_class.return_value = mock_next_task
                
                result = create_next_recurring_task(mock_task)
                
                assert result == mock_next_task
                
                # Verify Task was called with correct due date
                call_kwargs = mock_task_class.call_args[1]
                expected_due = datetime(2023, 1, 1) + timedelta(days=1)
                assert call_kwargs['duedate'] == expected_due
                assert call_kwargs['title'] == "Test Task"
                
                mock_add.assert_called_with(mock_next_task)
                mock_commit.assert_called_once()
                mock_create_notifs.assert_called_once_with(mock_next_task)  # Verify it was called

    def test_create_next_recurring_task_weekly(self, app):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            
            mock_task = Mock(spec=Task)
            mock_task.title = "Test Task"
            mock_task.description = "Test Description"
            mock_task.duedate = datetime(2023, 1, 1)
            mock_task.status = TaskStatus.UNASSIGNED
            mock_task.priority = 1
            mock_task.owner = mock_owner
            mock_task.notes = "Test notes"
            mock_task.project = None
            mock_task.isRecurring = True
            mock_task.recurrence_type = RecurrenceType.WEEKLY
            mock_task.recurrence_interval = None
            mock_task.collaborators = []
            mock_task.attachments = []
            
            with patch('app.services.task_services.Task') as mock_task_class, \
                patch('app.services.task_services.db.session.add') as mock_add, \
                patch('app.services.task_services.db.session.commit') as mock_commit, \
                patch('app.services.task_services.create_recurring_task_creation_notification') as mock_recur_notif, \
                patch('app.services.notification_services.create_notifications_for_task') as mock_create_notifs:
                
                mock_next_task = Mock()
                mock_next_task.collaborators = []
                mock_next_task.duedate = datetime(2023, 1, 2)  # Set duedate
                mock_next_task.status = TaskStatus.UNASSIGNED  # Set status
                mock_next_task.id = 2  # Set id
                mock_task_class.return_value = mock_next_task
                
                result = create_next_recurring_task(mock_task)
                
                assert result == mock_next_task
                
                # Verify Task was called with correct due date
                call_kwargs = mock_task_class.call_args[1]
                expected_due = datetime(2023, 1, 1) + timedelta(weeks=1)
                assert call_kwargs['duedate'] == expected_due
                assert call_kwargs['title'] == "Test Task"
                
                mock_add.assert_called_with(mock_next_task)
                mock_commit.assert_called_once()
                mock_create_notifs.assert_called_once_with(mock_next_task)

    def test_create_next_recurring_task_monthly(self, app):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            
            mock_task = Mock(spec=Task)
            mock_task.title = "Test Task"
            mock_task.description = "Test Description"
            mock_task.duedate = datetime(2023, 1, 1)
            mock_task.status = TaskStatus.UNASSIGNED
            mock_task.priority = 1
            mock_task.owner = mock_owner
            mock_task.notes = "Test notes"
            mock_task.project = None
            mock_task.isRecurring = True
            mock_task.recurrence_type = RecurrenceType.MONTHLY
            mock_task.recurrence_interval = None
            mock_task.collaborators = []
            mock_task.attachments = []
            
            with patch('app.services.task_services.Task') as mock_task_class, \
                patch('app.services.task_services.db.session.add') as mock_add, \
                patch('app.services.task_services.db.session.commit') as mock_commit, \
                patch('app.services.task_services.create_recurring_task_creation_notification') as mock_recur_notif, \
                patch('app.services.notification_services.create_notifications_for_task') as mock_create_notifs:
                
                mock_next_task = Mock()
                mock_next_task.collaborators = []
                mock_next_task.duedate = datetime(2023, 1, 2)  # Set duedate
                mock_next_task.status = TaskStatus.UNASSIGNED  # Set status
                mock_next_task.id = 2  # Set id
                mock_task_class.return_value = mock_next_task
                
                result = create_next_recurring_task(mock_task)
                
                assert result == mock_next_task
                
                call_kwargs = mock_task_class.call_args[1]
                expected_due = datetime(2023, 1, 1) + relativedelta(months=1)
                assert call_kwargs['duedate'] == expected_due
                assert call_kwargs['title'] == "Test Task"
                
                mock_add.assert_called_with(mock_next_task)
                mock_commit.assert_called_once()
                mock_create_notifs.assert_called_once_with(mock_next_task)

    def test_create_next_recurring_task_custom(self, app):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            mock_owner = Mock(spec=User)
            mock_owner.id = 1
            
            mock_task = Mock(spec=Task)
            mock_task.title = "Test Task"
            mock_task.description = "Test Description"
            mock_task.duedate = datetime(2023, 1, 1)
            mock_task.status = TaskStatus.UNASSIGNED
            mock_task.priority = 1
            mock_task.owner = mock_owner
            mock_task.notes = "Test notes"
            mock_task.project = None
            mock_task.isRecurring = True
            mock_task.recurrence_type = RecurrenceType.CUSTOM
            mock_task.recurrence_interval = 5
            mock_task.collaborators = []
            mock_task.attachments = []
            
            with patch('app.services.task_services.Task') as mock_task_class, \
                patch('app.services.task_services.db.session.add') as mock_add, \
                patch('app.services.task_services.db.session.commit') as mock_commit, \
                patch('app.services.task_services.create_recurring_task_creation_notification') as mock_recur_notif, \
                patch('app.services.notification_services.create_notifications_for_task') as mock_create_notifs:
                
                mock_next_task = Mock()
                mock_next_task.collaborators = []
                mock_next_task.duedate = datetime(2023, 1, 2)  # Set duedate
                mock_next_task.status = TaskStatus.UNASSIGNED  # Set status
                mock_next_task.id = 2  # Set id
                mock_task_class.return_value = mock_next_task
                
                result = create_next_recurring_task(mock_task)
                
                assert result == mock_next_task
                
                # Verify Task was called with correct due date
                call_kwargs = mock_task_class.call_args[1]
                expected_due = datetime(2023, 1, 1) + timedelta(days=mock_task.recurrence_interval)
                assert call_kwargs['duedate'] == expected_due
                assert call_kwargs['title'] == "Test Task"
                
                mock_add.assert_called_with(mock_next_task)
                mock_commit.assert_called_once()
                mock_create_notifs.assert_called_once_with(mock_next_task)

    def test_create_next_recurring_task_custom_missing_interval(self, app):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            mock_task = Mock(spec=Task)
            mock_task.isRecurring = True
            mock_task.recurrence_type = RecurrenceType.CUSTOM
            mock_task.recurrence_interval = None
            mock_task.duedate = datetime(2023, 1, 1)
            
            with pytest.raises(ValueError, match="Custom interval is missing or invalid for recurring task"):
                create_next_recurring_task(mock_task)

    def test_create_next_recurring_task_not_recurring(self, app):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            mock_task = Mock(spec=Task)
            mock_task.isRecurring = False
            
            result = create_next_recurring_task(mock_task)
            
            assert result is None

    def test_create_next_recurring_task_with_attachments_and_collaborators(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import create_next_recurring_task
            
            # --- Setup mock task (the "completed" task) ---
        mock_task = Mock(spec=Task)
        mock_task.isRecurring = True
        mock_task.recurrence_type = RecurrenceType.DAILY
        mock_task.recurrence_interval = None
        mock_task.duedate = datetime(2023, 1, 1)
        mock_task.title = "Daily Report"
        mock_task.description = "Submit daily report"
        mock_task.priority = "High"
        mock_task.owner = Mock()
        mock_task.notes = "Be thorough"
        mock_task.project = Mock()

        # Mock collaborators
        mock_collaborator = Mock(spec=User)
        mock_task.collaborators = [mock_collaborator]

        # Mock attachments
        mock_attachment = Mock(spec=Attachment)
        mock_attachment.filename = "test.txt"
        mock_attachment.content = b"filecontent"
        mock_task.attachments = [mock_attachment]

        # --- Patch dependencies inside the service ---
        with patch('app.services.task_services.Task') as mock_task_class, \
             patch('app.services.task_services.Attachment') as mock_attach_class, \
             patch('app.services.task_services.db.session.add') as mock_add, \
             patch('app.services.task_services.db.session.commit') as mock_commit, \
             patch('app.services.task_services.create_recurring_task_creation_notification') as mock_recur_notif, \
             patch('app.services.notification_services.create_notifications_for_task') as mock_create_notifs:

            # Mock Task() creation return
            mock_next_task = Mock(spec=Task)
            mock_next_task.collaborators = []
            mock_task_class.return_value = mock_next_task

            # Mock Attachment() creation return
            mock_new_attachment = Mock(spec=Attachment)
            mock_attach_class.return_value = mock_new_attachment

            # --- Run function under test ---
            result = create_next_recurring_task(mock_task)

            # --- Assertions ---

            # 1. Task() called once with correct arguments
            mock_task_class.assert_called_once_with(
                title=mock_task.title,
                description=mock_task.description,
                duedate=mock_task.duedate + timedelta(days=1),
                status=TaskStatus.UNASSIGNED,
                priority=mock_task.priority,
                owner=mock_task.owner,
                notes=mock_task.notes,
                project=mock_task.project,
                isRecurring=True,
                recurrence_type=RecurrenceType.DAILY,
                recurrence_interval=None,
            )

            # 2. Collaborators copied correctly
            assert mock_collaborator in mock_next_task.collaborators

            # 3. Attachment cloned correctly
            mock_attach_class.assert_called_once_with(
                filename=mock_attachment.filename,
                content=mock_attachment.content,
                task=mock_next_task
            )
            mock_add.assert_any_call(mock_new_attachment)

            # 4. DB commit and add were called
            mock_add.assert_any_call(mock_next_task)
            mock_commit.assert_called_once()

            # 5. Notifications triggered
            mock_recur_notif.assert_called_once_with(mock_next_task, mock_task)
            mock_create_notifs.assert_called_once_with(mock_next_task)

            # 6. Return value is the new task
            assert result == mock_next_task

    # Test get_task function
    def test_get_task_success(self, app):
        with app.app_context():
            from app.services.task_services import get_task
            
            mock_task = Mock(spec=Task)
            
            with patch('app.services.task_services.Task.query') as mock_query, \
                patch('app.services.task_services.db') as mock_db:
                
                mock_query.get.return_value = mock_task
                
                result = get_task(1)
                
                assert result == mock_task
                mock_query.get.assert_called_once_with(1)

    def test_get_task_not_found(self, app):
        with app.app_context():
            from app.services.task_services import get_task
            
            with patch('app.services.task_services.Task.query') as mock_query, \
                patch('app.services.task_services.db') as mock_db:
                
                mock_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Task with task ID 1 not found"):
                    get_task(1)


    def test_get_task_database_error(self, app):
        with app.app_context():
            from app.services.task_services import get_task
            
            with patch('app.services.task_services.Task.query') as mock_query, \
                patch('app.services.task_services.db') as mock_db:
                
                mock_query.get.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while retrieving task 1:"):
                    get_task(1)
                
                mock_db.session.rollback.assert_called_once()

    # Test get_user_tasks function
    def test_get_user_tasks_success(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_user_tasks
            
            mock_user = Mock(spec=User)
            mock_user.id = 1
            mock_user._sa_instance_state = Mock()
            
            mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
            
            with patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.Task.query') as mock_task_query:
                
                mock_user_query.get.return_value = mock_user
                
                mock_filtered_query = Mock()
                mock_filtered_query.all.return_value = mock_tasks
                mock_task_query.filter.return_value = mock_filtered_query
                
                result = get_user_tasks(1)
                
                assert result == mock_tasks
                mock_user_query.get.assert_called_once_with(1)

    def test_get_user_tasks_user_not_found(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_user_tasks
            
            with patch('app.services.task_services.User.query') as mock_user_query:
                mock_user_query.get.return_value = None
                
                result = get_user_tasks(1)
                
                assert result == []

    def test_get_user_tasks_database_error(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_user_tasks
            
            with patch('app.services.task_services.User.query') as mock_user_query:
                mock_user_query.get.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while retrieving tasks of user 1:"):
                    get_user_tasks(1)
                
                mock_db.session.rollback.assert_called_once()

    # Test get_project_tasks function
    def test_get_project_tasks_success(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_project_tasks
            
            mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
            
            with patch('app.services.task_services.Task.query') as mock_query:
                mock_filtered_query = Mock()
                mock_filtered_query.all.return_value = mock_tasks
                mock_query.filter_by.return_value = mock_filtered_query
                
                result = get_project_tasks(1)
                
                assert result == mock_tasks
                mock_query.filter_by.assert_called_once_with(project_id=1)

    def test_get_project_tasks_database_error(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_project_tasks
            
            with patch('app.services.task_services.Task.query') as mock_query:
                mock_query.filter_by.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while retrieving tasks of project 1:"):
                    get_project_tasks(1)
                
                mock_db.session.rollback.assert_called_once()

    # Test get_project_users_for_tasks function
    def test_get_project_users_for_tasks_with_project(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_project_users_for_tasks
            
            mock_task = Mock(spec=Task)
            mock_task.project_id = 1
            mock_task._sa_instance_state = Mock()
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_project_users') as mock_get_proj_users:
                
                mock_task_query.get.return_value = mock_task
                mock_get_proj_users.return_value = ["user1", "user2"]
                
                result = get_project_users_for_tasks(1)
                
                assert result == ["user1", "user2"]
                mock_get_proj_users.assert_called_once_with(1)

    def test_get_project_users_for_tasks_no_project(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_project_users_for_tasks
            
            mock_task = Mock(spec=Task)
            mock_task.project_id = None
            mock_task._sa_instance_state = Mock()
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_users_info') as mock_get_users:
                
                mock_task_query.get.return_value = mock_task
                mock_get_users.return_value = ["all_users"]
                
                result = get_project_users_for_tasks(1)
                
                assert result == ["all_users"]
                mock_get_users.assert_called_once()

    def test_get_project_users_for_tasks_task_not_found(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_project_users_for_tasks
            
            with patch('app.services.task_services.Task.query') as mock_task_query:
                mock_task_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Task with task ID 1 not found"):
                    get_project_users_for_tasks(1)

    def test_get_project_users_for_tasks_database_error(self, app):
        with app.app_context():
            from app.services.task_services import get_project_users_for_tasks
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                patch('app.services.task_services.db') as mock_db:
                
                mock_task_query.get.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error"):
                    get_project_users_for_tasks(1)
                
                mock_db.session.rollback.assert_called_once()

    # Test get_unassigned_tasks function
    def test_get_unassigned_tasks_success(self, app):
        with app.app_context():
            from app.services.task_services import get_unassigned_tasks
            
            mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
            
            with patch('app.services.task_services.Task.query') as mock_query:
                mock_filtered_query = Mock()
                mock_filtered_query.all.return_value = mock_tasks
                mock_query.filter.return_value = mock_filtered_query
                
                result = get_unassigned_tasks()
                
                assert result == mock_tasks

    def test_get_unassigned_tasks_database_error(self, app):
        with app.app_context():
            from app.services.task_services import get_unassigned_tasks
            
            with patch('app.services.task_services.Task.query') as mock_query:
                mock_query.filter.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while fetching unassigned tasks:"):
                    get_unassigned_tasks()

    # Test link_task_to_project function
    def test_link_task_to_project_success(self, app):
        with app.app_context():
            from app.services.task_services import link_task_to_project

            mock_task = Mock(spec=Task)
            mock_task.project_id = None
            mock_task.project = None
            mock_task.collaborators = []
            mock_task.owner = Mock(spec=User)

            mock_project = Mock(spec=Project)
            mock_project.name = "New Project"

            mock_user = Mock(spec=User)
            mock_user.id = 123
            mock_user.name = "test_user"

            with patch('app.services.task_services.Task.query') as mock_task_query, \
                patch('app.services.task_services.Project.query') as mock_project_query, \
                patch('app.services.task_services.db') as mock_db_task, \
                patch('app.services.notification_services.db') as mock_db_notify, \
                patch('app.services.task_services.send_task_update_notification', return_value=None) as mock_send_update_task, \
                patch('app.services.notification_services.send_task_update_notification', return_value=None) as mock_send_update_notify, \
                patch('app.services.notification_services.create_task_update_notification') as mock_create_notify:

                # Mock queries
                mock_task_query.get.return_value = mock_task
                mock_project_query.get.return_value = mock_project

                result = link_task_to_project(1, 2, mock_user)

                assert result == mock_task
                assert mock_task.project == mock_project

                mock_db_task.session.commit.assert_called_once()

                assert mock_send_update_task.called or mock_send_update_notify.called

    def test_link_task_to_project_task_not_found(self, app):
        with app.app_context():
            from app.services.task_services import link_task_to_project

            with patch('app.services.task_services.Task.query') as mock_task_query, \
                patch('app.services.task_services.Project.query') as mock_project_query, \
                patch('app.services.task_services.db') as mock_db:

                mock_task_query.get.return_value = None
                mock_project_query.get.return_value = None  # 👈 important

                with pytest.raises(ValueError, match="Task with ID 1 not found."):
                    link_task_to_project(1, 2)

    def test_link_task_to_project_project_not_found(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import link_task_to_project
            
            mock_task = Mock(spec=Task)
            mock_task._sa_instance_state = Mock()
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.Project.query') as mock_project_query:
                
                mock_task_query.get.return_value = mock_task
                mock_project_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Project with ID 2 not found."):
                    link_task_to_project(1, 2)

    def test_link_task_to_project_database_error(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import link_task_to_project
            
            mock_task = Mock(spec=Task)
            mock_task._sa_instance_state = Mock()
            
            mock_project = Mock(spec=Project)
            mock_project._sa_instance_state = Mock()
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.Project.query') as mock_project_query:
                
                mock_task_query.get.return_value = mock_task
                mock_project_query.get.return_value = mock_project
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while linking task 1 to project 2:"):
                    link_task_to_project(1, 2)
                
                mock_db.session.rollback.assert_called_once()

    def test_update_task_success(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.id = 1
            mock_task.title = "Old Title"
            mock_task.description = "Old Description"
            mock_task.duedate = datetime(2023, 1, 1)
            mock_task.status = TaskStatus.UNASSIGNED
            mock_task.priority = 1
            mock_task.owner_id = 1
            mock_task.owner = Mock(spec=User)
            mock_task.owner.email = "old@example.com"
            mock_task.collaborators = []
            mock_task.attachments = []
            mock_task.notes = "Old notes"
            mock_task.isRecurring = False
            mock_task.recurrence_type = RecurrenceType.NONE
            mock_task.recurrence_interval = None
            
            data = {
                "title": "New Title",
                "description": "New Description",
                "duedate": "2023-12-31T00:00:00+00:00",
                "status": "Ongoing", 
                "priority": "2",
                "notes": "New notes"
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db, \
                 patch('app.services.task_services.send_task_update_notification') as mock_send_update, \
                 patch('app.services.task_services.update_notifications_for_task') as mock_update_notifs:
                
                mock_task_query.get.return_value = mock_task
                mock_jwt.return_value = 1
                mock_current_user = Mock(spec=User)
                mock_current_user.id = 1
                mock_user_query.get.return_value = mock_current_user
                
                result = update_task(1, data, [])
                
                assert result == mock_task
                mock_db.session.commit.assert_called_once()
                assert mock_task.title == "New Title"
                assert mock_task.description == "New Description"
                assert mock_task.notes == "New notes"
                assert mock_task.priority == 2

    def test_update_task_with_valid_owner_change(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.owner_id = 1
            mock_task.owner = Mock(spec=User)
            mock_task.owner.email = "old@example.com"
            mock_task.collaborators = []
            mock_task.attachments = []
            mock_task.status = TaskStatus.UNASSIGNED
            
            mock_new_owner = Mock(spec=User)
            mock_new_owner.id = 2
            mock_new_owner.email = "new@example.com"
            
            data = {
                "owner": "new@example.com"
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db, \
                 patch('app.services.task_services.send_task_assignment_notification') as mock_send_assign, \
                 patch('app.services.task_services.send_task_update_notification') as mock_send_update:  # Mock this to avoid real DB calls
                
                mock_task_query.get.return_value = mock_task
                mock_jwt.return_value = 1
                mock_current_user = Mock(spec=User)
                mock_user_query.get.return_value = mock_current_user
                
                mock_filtered_query = Mock()
                mock_filtered_query.first.return_value = mock_new_owner
                mock_user_query.filter_by.return_value = mock_filtered_query
                
                result = update_task(1, data, [])
                
                # Check that owner was changed and notification sent
                assert mock_task.owner == mock_new_owner
                mock_send_assign.assert_called_once_with(mock_task, mock_current_user, mock_new_owner, "owner")
    
    def test_update_task_with_invalid_owner_change(self, mock_db, mock_task, mock_user, mock_get_jwt_identity, mock_request):
        """Test updating owner with invalid email raises error"""
        # Setup
        data = {
            "owner": "nonexistent@example.com"
        }
        
        mock_get_jwt_identity.return_value = 1
        
        with patch('app.services.task_services.Task.query') as mock_task_query, \
             patch('app.services.task_services.User.query') as mock_user_query:
            
            mock_task_query.get.return_value = mock_task
            mock_user_query.get.return_value = mock_user
            mock_user_query.filter_by.return_value.first.return_value = None
            
            # Execute & Assert
            from app.services.task_services import update_task
            with pytest.raises(ValueError, match="Owner with email nonexistent@example.com not found"):
                update_task(1, data, [])

    def test_update_task_with_valid_collaborators_change(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.collaborators = []
            mock_task.attachments = []
            mock_task.status = TaskStatus.UNASSIGNED
            
            mock_collaborator = Mock(spec=User)
            mock_collaborator.id = 2
            mock_collaborator.email = "collab@example.com"
            
            data = {
                "collaborators": ["collab@example.com"]
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db, \
                 patch('app.services.task_services.send_task_assignment_notification') as mock_send_assign, \
                 patch('app.services.task_services.send_task_update_notification') as mock_send_update:  # Mock this to avoid real DB calls
                
                mock_task_query.get.return_value = mock_task
                mock_jwt.return_value = 1
                mock_current_user = Mock(spec=User)
                mock_user_query.get.return_value = mock_current_user
                
                mock_filtered_query = Mock()
                mock_filtered_query.first.return_value = mock_collaborator
                mock_user_query.filter_by.return_value = mock_filtered_query
                
                result = update_task(1, data, [])
                
                # Check that collaborator was added and notification sent
                assert len(mock_task.collaborators) == 1
                mock_send_assign.assert_called_once_with(mock_task, mock_current_user, mock_collaborator, "collaborator")

    def test_update_task_collaborators_with_string_json(self, mock_db, mock_task, mock_user, mock_get_jwt_identity, mock_request):
        """Test updating collaborators with JSON string"""
        # Setup
        collaborator = Mock(spec=User)
        collaborator.email = "collab@example.com"
        
        # Create a proper mock for collaborators list
        mock_collaborators = Mock()
        mock_collaborators.__iter__ = Mock(return_value=iter([]))  # Empty list
        mock_collaborators.clear = Mock()
        mock_collaborators.append = Mock()
        mock_task.collaborators = mock_collaborators
        
        data = {
            "collaborators": '["collab@example.com"]'  # JSON string
        }
        
        mock_get_jwt_identity.return_value = 1
        
        with patch('app.services.task_services.Task.query') as mock_task_query, \
             patch('app.services.task_services.User.query') as mock_user_query, \
             patch('app.services.task_services.send_task_assignment_notification') as mock_notification, \
             patch('app.services.task_services.send_task_update_notification') as mock_update_notification, \
             patch('app.services.task_services.update_notifications_for_task') as mock_update_task_notifications:
            
            mock_task_query.get.return_value = mock_task
            mock_user_query.get.return_value = mock_user
            mock_user_query.filter_by.return_value.first.return_value = collaborator
            
            # Execute
            from app.services.task_services import update_task
            result = update_task(1, data, [])
            
            # Assert - should parse JSON string correctly
            mock_task.collaborators.append.assert_called_once_with(collaborator)
            mock_notification.assert_called_once()
            mock_db.session.commit.assert_called_once()

    def test_update_task_collaborators_with_invalid_json_string(self, mock_db, mock_task, mock_user, mock_get_jwt_identity, mock_request):
        """Test updating collaborators with invalid JSON string"""
        # Setup
        # Create a proper mock for collaborators list
        mock_collaborators = Mock()
        mock_collaborators.__iter__ = Mock(return_value=iter([]))  # Empty list
        mock_collaborators.clear = Mock()
        mock_collaborators.append = Mock()
        mock_task.collaborators = mock_collaborators
        
        data = {
            "collaborators": 'invalid json string'  # Invalid JSON
        }
        
        mock_get_jwt_identity.return_value = 1
        
        with patch('app.services.task_services.Task.query') as mock_task_query, \
             patch('app.services.task_services.User.query') as mock_user_query, \
             patch('app.services.task_services.send_task_assignment_notification') as mock_notification, \
             patch('app.services.task_services.send_task_update_notification') as mock_update_notification, \
             patch('app.services.task_services.update_notifications_for_task') as mock_update_task_notifications:
            
            mock_task_query.get.return_value = mock_task
            mock_user_query.get.return_value = mock_user
            
            # Execute
            from app.services.task_services import update_task
            result = update_task(1, data, [])
            
            # Assert - should handle JSON decode error and use empty list
            mock_task.collaborators.clear.assert_called_once()
            mock_task.collaborators.append.assert_not_called()  # No valid collaborators
            mock_notification.assert_not_called()
            mock_db.session.commit.assert_called_once()

    def test_update_task_with_attachments(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.attachments = []
            mock_task.status = TaskStatus.UNASSIGNED
            
            mock_file = Mock()
            mock_file.filename = "new_file.txt"
            mock_file.read.return_value = b"new content"
            
            data = {
                "existing_attachments": []
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db, \
                 patch('app.services.task_services.Attachment') as mock_attachment_class, \
                 patch('app.services.task_services.send_task_update_notification') as mock_send_update:  # Mock notification to avoid DB calls
                
                # Mock the notification function that's actually in notification_services
                with patch('app.services.notification_services.send_task_attachment_notification') as mock_send_attach:
                    
                    mock_task_query.get.return_value = mock_task
                    mock_jwt.return_value = 1
                    mock_current_user = Mock(spec=User)
                    mock_user_query.get.return_value = mock_current_user
                    
                    mock_attachment_instance = Mock()
                    mock_attachment_class.return_value = mock_attachment_instance
                    
                    result = update_task(1, data, [mock_file])
                    
                    # Check that new attachment was added
                    mock_attachment_class.assert_called_once_with(
                        filename="new_file.txt",
                        content=b"new content",
                        task=mock_task
                    )
                    mock_db.session.add.assert_called_with(mock_attachment_instance)

    def test_update_task_attachment_removal(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_attachment = Mock(spec=Attachment)
            mock_attachment.id = 1
            mock_attachment.filename = "old_file.txt"
            
            mock_task = Mock(spec=Task)
            mock_task.attachments = [mock_attachment]
            mock_task.status = TaskStatus.UNASSIGNED
            
            data = {
                "existing_attachments": []  # No attachments to keep, so all should be removed
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db, \
                 patch('app.services.task_services.send_task_update_notification') as mock_send_update:  # Mock notification
                
                # Mock the notification function that's actually in notification_services
                with patch('app.services.notification_services.create_task_attachment_removal_notification') as mock_remove_notif:
                    
                    mock_task_query.get.return_value = mock_task
                    mock_jwt.return_value = 1
                    mock_current_user = Mock(spec=User)
                    mock_user_query.get.return_value = mock_current_user
                    
                    result = update_task(1, data, [])
                    
                    # Check that attachment was marked for deletion
                    mock_db.session.delete.assert_called_with(mock_attachment)

    def test_update_task_completed_status_triggers_recurring(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.status = TaskStatus.UNASSIGNED
            mock_task.attachments = []
            
            # Use actual TaskStatus enum value
            data = {
                "status": TaskStatus.COMPLETED.value
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db, \
                 patch('app.services.task_services.create_next_recurring_task') as mock_create_recurring, \
                 patch('app.services.task_services.send_task_update_notification') as mock_send_update:  # Mock notification
                
                mock_task_query.get.return_value = mock_task
                mock_jwt.return_value = 1
                mock_current_user = Mock(spec=User)
                mock_user_query.get.return_value = mock_current_user
                
                result = update_task(1, data, [])
                
                # Check that create_next_recurring_task was called for completed task
                mock_create_recurring.assert_called_once_with(mock_task)

    def test_update_recurrence_from_none_to_daily(self, mock_db, mock_task, mock_user, mock_get_jwt_identity, mock_request):
        """Test updating recurrence from none to daily"""
        # Setup
        mock_task.isRecurring = False
        mock_task.recurrence_type = RecurrenceType.NONE
        mock_task.recurrence_interval = None
        
        data = {
            "recurrence": "daily"
        }
        
        mock_get_jwt_identity.return_value = 1
        
        with patch('app.services.task_services.Task.query') as mock_task_query, \
             patch('app.services.task_services.User.query') as mock_user_query:
            
            mock_task_query.get.return_value = mock_task
            mock_user_query.get.return_value = mock_user
            
            # Execute
            from app.services.task_services import update_task
            result = update_task(1, data, [])
            
            # Assert
            assert mock_task.isRecurring == True
            assert mock_task.recurrence_type == RecurrenceType.DAILY
            assert mock_task.recurrence_interval is None
            mock_db.session.commit.assert_called_once()

    def test_update_task_not_found(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            with patch('app.services.task_services.Task.query') as mock_task_query:
                mock_task_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Task with task ID 1 not found"):
                    update_task(1, {}, [])

    def test_update_task_invalid_date_format(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.attachments = []
            mock_task.status = TaskStatus.UNASSIGNED
            
            data = {
                "duedate": "invalid-date-format"
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query:
                mock_task_query.get.return_value = mock_task
                
                with pytest.raises(ValueError, match="Invalid date format: invalid-date-format"):
                    update_task(1, data, [])

    def test_update_task_invalid_status(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.attachments = []
            mock_task.status = TaskStatus.UNASSIGNED
            
            data = {
                "status": "invalid_status"
            }
            
            with patch('app.services.task_services.Task.query') as mock_task_query:
                mock_task_query.get.return_value = mock_task
                
                with pytest.raises(ValueError, match="Invalid status: invalid_status"):
                    update_task(1, data, [])

    # Test update_task function with proper request context
    def test_update_task_database_error(self, app, mock_request):
        with app.app_context():
            from app.services.task_services import update_task
            
            mock_task = Mock(spec=Task)
            mock_task.attachments = []
            # Mock the status properly
            mock_task.status = TaskStatus.UNASSIGNED
            
            with patch('app.services.task_services.Task.query') as mock_task_query, \
                 patch('app.services.task_services.get_jwt_identity') as mock_jwt, \
                 patch('app.services.task_services.User.query') as mock_user_query, \
                 patch('app.services.task_services.db') as mock_db:
                
                mock_task_query.get.return_value = mock_task
                mock_jwt.return_value = 1
                mock_current_user = Mock(spec=User)
                mock_user_query.get.return_value = mock_current_user
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while updating task 1:"):
                    update_task(1, {}, [])

    # Test get_subtasks function
    def test_get_subtasks_success(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_subtasks
            
            mock_subtasks = [Mock(spec=Task), Mock(spec=Task)]
            
            with patch('app.services.task_services.Task.query') as mock_query:
                mock_filtered_query = Mock()
                mock_filtered_query.all.return_value = mock_subtasks
                mock_query.filter_by.return_value = mock_filtered_query
                
                result = get_subtasks(1)
                
                assert result == mock_subtasks
                mock_query.filter_by.assert_called_once_with(parent_id=1)

    def test_get_subtasks_database_error(self, app, mock_db):
        with app.app_context():
            from app.services.task_services import get_subtasks
            
            with patch('app.services.task_services.Task.query') as mock_query:
                mock_query.filter_by.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(RuntimeError, match="Database error while getting subtasks of task 1"):
                    get_subtasks(1)
                
                mock_db.session.rollback.assert_called_once()