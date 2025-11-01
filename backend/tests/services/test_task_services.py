import pytest
from datetime import datetime, date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.services.task_services import (
    create_task,
    get_task,
    get_user_tasks,
    get_project_tasks,
    get_unassigned_tasks,
    link_task_to_project,
    update_task
)
from app.models import Task, User, Project, Attachment, TaskStatus


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    with patch('app.services.task_services.db.session') as mock_session:
        yield mock_session


@pytest.fixture
def mock_user():
    """Create a mock user"""
    user = Mock(spec=User)
    user.id = 1
    user.email = "owner@example.com"
    user.name = "Test Owner"
    return user


@pytest.fixture
def mock_collaborator():
    """Create a mock collaborator"""
    collab = Mock(spec=User)
    collab.id = 2
    collab.email = "collaborator@example.com"
    collab.name = "Test Collaborator"
    return collab


@pytest.fixture
def mock_project():
    """Create a mock project"""
    project = Mock(spec=Project)
    project.id = 1
    project.name = "Test Project"
    return project


@pytest.fixture
def mock_task():
    """Create a mock task"""
    task = Mock(spec=Task)
    task.id = 1
    task.title = "Test Task"
    task.description = "Test Description"
    task.duedate = date.today() + timedelta(days=7)
    task.status = TaskStatus.UNASSIGNED
    task.priority = 1
    task.notes = "Test notes"
    task.owner_id = 1
    task.project_id = None
    task.attachments = []
    task.collaborators = []
    return task


@pytest.fixture
def default_task_status():
    """Get the default TaskStatus value"""
    return TaskStatus.UNASSIGNED


@pytest.fixture(autouse=True)
def mock_jwt_identity(monkeypatch):
    monkeypatch.setattr('app.services.task_services.get_jwt_identity', lambda: 1)


@pytest.fixture(autouse=True)
def mock_user_query(monkeypatch, mock_user):
    query_mock = MagicMock()
    query_mock.get.return_value = mock_user
    query_mock.filter_by.return_value.first.return_value = mock_user
    user_stub = SimpleNamespace(query=query_mock)
    monkeypatch.setattr('app.services.task_services.User', user_stub)
    return query_mock


@pytest.fixture(autouse=True)
def stub_get_history(monkeypatch):
    class _History:
        deleted = []
        added = []

        def has_changes(self):
            return False

    monkeypatch.setattr('sqlalchemy.orm.attributes.get_history', lambda *args, **kwargs: _History())


class TestCreateTask:
    """Tests for create_task function"""

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.get_user_by_email')
    @patch('app.services.task_services.Task')
    def test_create_task_success(self, mock_task_class, mock_get_user, mock_notif, 
                                 mock_db_session, mock_user, default_task_status):
        """Test successful task creation"""
        mock_get_user.return_value = mock_user
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance

        result = create_task(
            title="New Task",
            description="Task Description",
            duedate=date.today(),
            status=default_task_status,
            owner_email="owner@example.com",
            collaborator_emails=None,
            attachments=None,
            notes="Some notes",
            priority=1,
            project_id=None
        )

        assert result == mock_task_instance
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()
        mock_notif.create_notifications_for_task.assert_called_once_with(mock_task_instance)

    @patch('app.services.task_services.get_user_by_email')
    def test_create_task_owner_not_found(self, mock_get_user, mock_db_session, default_task_status):
        """Test task creation with non-existent owner"""
        mock_get_user.return_value = None

        with pytest.raises(ValueError, match="Owner with email .* not found"):
            create_task(
                title="New Task",
                description="Task Description",
                duedate=date.today(),
                status=default_task_status,
                owner_email="nonexistent@example.com",
                collaborator_emails=None,
                attachments=None,
                notes="Some notes",
                priority=1
            )

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.get_user_by_email')
    @patch('app.services.task_services.Task')
    def test_create_task_with_collaborators(self, mock_task_class, mock_get_user, mock_notif, 
                                           mock_db_session, mock_user, mock_collaborator, default_task_status):
        """Test task creation with collaborators"""
        mock_get_user.side_effect = [mock_user, mock_collaborator]
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance

        result = create_task(
            title="New Task",
            description="Task Description",
            duedate=date.today(),
            status=default_task_status,
            owner_email="owner@example.com",
            collaborator_emails=["collaborator@example.com"],
            attachments=None,
            notes="Some notes",
            priority=1
        )

        assert result == mock_task_instance
        assert mock_get_user.call_count == 2

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Project')
    @patch('app.services.task_services.get_user_by_email')
    @patch('app.services.task_services.Task')
    def test_create_task_with_project(self, mock_task_class, mock_get_user, mock_project_class,
                                     mock_notif, mock_db_session, mock_user, mock_project, default_task_status):
        """Test task creation with project assignment"""
        mock_get_user.return_value = mock_user
        mock_project_class.query.get.return_value = mock_project
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance

        result = create_task(
            title="New Task",
            description="Task Description",
            duedate=date.today(),
            status=default_task_status,
            owner_email="owner@example.com",
            collaborator_emails=None,
            attachments=None,
            notes="Some notes",
            priority=1,
            project_id=1
        )

        assert result == mock_task_instance
        mock_project_class.query.get.assert_called_once_with(1)

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Attachment')
    @patch('app.services.task_services.get_user_by_email')
    @patch('app.services.task_services.Task')
    def test_create_task_with_attachments(self, mock_task_class, mock_get_user, mock_attachment_class,
                                         mock_notif, mock_db_session, mock_user, default_task_status):
        """Test task creation with file attachments"""
        mock_get_user.return_value = mock_user
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance

        mock_file = Mock()
        mock_file.filename = "test.txt"
        mock_file.read.return_value = b"file content"

        result = create_task(
            title="New Task",
            description="Task Description",
            duedate=date.today(),
            status=default_task_status,
            owner_email="owner@example.com",
            collaborator_emails=None,
            attachments=[mock_file],
            notes="Some notes",
            priority=1
        )

        assert result == mock_task_instance
        mock_attachment_class.assert_called_once()

    @patch('app.services.task_services.get_user_by_email')
    @patch('app.services.task_services.Task')
    def test_create_task_database_error(self, mock_task_class, mock_get_user, 
                                       mock_db_session, mock_user, default_task_status):
        """Test task creation with database error"""
        mock_get_user.return_value = mock_user
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance
        mock_db_session.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while creating task"):
            create_task(
                title="New Task",
                description="Task Description",
                duedate=date.today(),
                status=default_task_status,
                owner_email="owner@example.com",
                collaborator_emails=None,
                attachments=None,
                notes="Some notes",
                priority=1
            )

        mock_db_session.rollback.assert_called_once()


class TestGetTask:
    """Tests for get_task function"""

    @patch('app.services.task_services.Task')
    def test_get_task_success(self, mock_task_class, mock_task):
        """Test successful task retrieval"""
        mock_task_class.query.get.return_value = mock_task

        result = get_task(1)

        assert result == mock_task
        mock_task_class.query.get.assert_called_once_with(1)

    @patch('app.services.task_services.Task')
    def test_get_task_not_found(self, mock_task_class, mock_db_session):
        """Test task retrieval when task doesn't exist"""
        mock_task_class.query.get.return_value = None

        with pytest.raises(ValueError, match="Task with task ID .* not found"):
            get_task(999)

    @patch('app.services.task_services.Task')
    def test_get_task_database_error(self, mock_task_class, mock_db_session):
        """Test task retrieval with database error"""
        mock_task_class.query.get.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while retrieving task"):
            get_task(1)

        mock_db_session.rollback.assert_called_once()


class TestGetUserTasks:
    """Tests for get_user_tasks function"""

    @patch('app.services.task_services.User')
    @patch('app.services.task_services.Task')
    def test_get_user_tasks_success(self, mock_task_class, mock_user_class, mock_task):
        """Test successful retrieval of user tasks"""
        mock_user_class.query.get.return_value = True
        mock_task_class.query.filter.return_value.all.return_value = [mock_task]

        result = get_user_tasks(1)

        assert len(result) == 1
        assert result[0] == mock_task
        mock_task_class.query.filter.assert_called_once()

    @patch('app.services.task_services.User')
    @patch('app.services.task_services.Task')
    def test_get_user_tasks_empty(self, mock_task_class, mock_user_class):
        """Test retrieval when user has no tasks"""
        mock_user_class.query.get.return_value = True
        mock_task_class.query.filter.return_value.all.return_value = []

        result = get_user_tasks(1)

        assert result == []

    @patch('app.services.task_services.User')
    @patch('app.services.task_services.Task')
    def test_get_user_tasks_database_error(self, mock_task_class, mock_user_class, mock_db_session):
        """Test user tasks retrieval with database error"""
        mock_user_class.query.get.return_value = True
        mock_task_class.query.filter.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while retrieving tasks of user"):
            get_user_tasks(1)

        mock_db_session.rollback.assert_called_once()


class TestGetProjectTasks:
    """Tests for get_project_tasks function"""

    @patch('app.services.task_services.Task')
    def test_get_project_tasks_success(self, mock_task_class, mock_task):
        """Test successful retrieval of project tasks"""
        mock_task_class.query.filter_by.return_value.all.return_value = [mock_task]

        result = get_project_tasks(1)

        assert len(result) == 1
        assert result[0] == mock_task
        mock_task_class.query.filter_by.assert_called_once_with(project_id=1)

    @patch('app.services.task_services.Task')
    def test_get_project_tasks_database_error(self, mock_task_class, mock_db_session):
        """Test project tasks retrieval with database error"""
        mock_task_class.query.filter_by.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while retrieving tasks of project"):
            get_project_tasks(1)

        mock_db_session.rollback.assert_called_once()


class TestGetUnassignedTasks:
    """Tests for get_unassigned_tasks function"""

    @patch('app.services.task_services.Task')
    def test_get_unassigned_tasks_success(self, mock_task_class, mock_task):
        """Test successful retrieval of unassigned tasks"""
        mock_task_class.query.filter.return_value.all.return_value = [mock_task]

        result = get_unassigned_tasks()

        assert len(result) == 1
        assert result[0] == mock_task

    @patch('app.services.task_services.Task')
    def test_get_unassigned_tasks_empty(self, mock_task_class):
        """Test retrieval when no unassigned tasks exist"""
        mock_task_class.query.filter.return_value.all.return_value = []

        result = get_unassigned_tasks()

        assert result == []

    @patch('app.services.task_services.Task')
    def test_get_unassigned_tasks_database_error(self, mock_task_class):
        """Test unassigned tasks retrieval with database error"""
        mock_task_class.query.filter.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while fetching unassigned tasks"):
            get_unassigned_tasks()


class TestLinkTaskToProject:
    """Tests for link_task_to_project function"""

    @patch('app.services.task_services.Project')
    @patch('app.services.task_services.Task')
    def test_link_task_to_project_success(self, mock_task_class, mock_project_class,
                                         mock_db_session, mock_task, mock_project):
        """Test successfully linking a task to a project"""
        mock_task_class.query.get.return_value = mock_task
        mock_project_class.query.get.return_value = mock_project

        result = link_task_to_project(1, 1)

        assert result == mock_task
        assert mock_task.project == mock_project
        mock_db_session.commit.assert_called_once()

    @patch('app.services.task_services.Project')
    @patch('app.services.task_services.Task')
    def test_link_task_to_project_task_not_found(self, mock_task_class, mock_project_class, 
                                                 mock_db_session):
        """Test linking when task doesn't exist"""
        mock_task_class.query.get.return_value = None

        with pytest.raises(ValueError, match="Task with ID .* not found"):
            link_task_to_project(999, 1)

    @patch('app.services.task_services.Project')
    @patch('app.services.task_services.Task')
    def test_link_task_to_project_project_not_found(self, mock_task_class, mock_project_class,
                                                    mock_db_session, mock_task):
        """Test linking when project doesn't exist"""
        mock_task_class.query.get.return_value = mock_task
        mock_project_class.query.get.return_value = None

        with pytest.raises(ValueError, match="Project with ID .* not found"):
            link_task_to_project(1, 999)

    @patch('app.services.task_services.Project')
    @patch('app.services.task_services.Task')
    def test_link_task_to_project_database_error(self, mock_task_class, mock_project_class,
                                                 mock_db_session, mock_task, mock_project):
        """Test linking with database error"""
        mock_task_class.query.get.return_value = mock_task
        mock_project_class.query.get.return_value = mock_project
        mock_db_session.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while linking task"):
            link_task_to_project(1, 1)

        mock_db_session.rollback.assert_called_once()


class TestUpdateTask:
    """Tests for update_task function"""

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_basic_fields(self, mock_task_class, mock_notif, mock_db_session, mock_task):
        """Test updating basic task fields"""
        mock_task_class.query.get.return_value = mock_task

        data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "priority": 2,
            "notes": "Updated notes"
        }

        result = update_task(1, data, None)

        assert result == mock_task
        assert mock_task.title == "Updated Title"
        assert mock_task.description == "Updated Description"
        assert mock_task.priority == 2
        assert mock_task.notes == "Updated notes"
        mock_db_session.commit.assert_called()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_duedate(self, mock_task_class, mock_notif, mock_db_session, mock_task):
        """Test updating task due date"""
        mock_task_class.query.get.return_value = mock_task
        new_date = "2025-12-31T00:00:00Z"

        data = {"duedate": new_date}

        result = update_task(1, data, None)

        assert result == mock_task
        mock_db_session.commit.assert_called()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_status(self, mock_task_class, mock_notif, mock_db_session, mock_task):
        """Test updating task status"""
        mock_task_class.query.get.return_value = mock_task

        data = {"status": "Ongoing"}

        result = update_task(1, data, None)

        assert result == mock_task
        assert mock_task.status == TaskStatus.ONGOING
        mock_db_session.commit.assert_called()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_invalid_status(self, mock_task_class, mock_notif, mock_db_session, mock_task):
        """Test updating with invalid status"""
        mock_task_class.query.get.return_value = mock_task

        data = {"status": "INVALID_STATUS"}

        with pytest.raises(ValueError, match="Invalid status"):
            update_task(1, data, None)

        mock_db_session.rollback.assert_called()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.User')
    @patch('app.services.task_services.Task')
    def test_update_task_owner(self, mock_task_class, mock_user_class, mock_notif, 
                               mock_db_session, mock_task, mock_user):
        """Test updating task owner"""
        mock_task_class.query.get.return_value = mock_task
        mock_user_class.query.filter_by.return_value.first.return_value = mock_user

        data = {"owner": "newowner@example.com"}

        result = update_task(1, data, None)

        assert result == mock_task
        assert mock_task.owner == mock_user

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.User')
    @patch('app.services.task_services.Task')
    def test_update_task_collaborators(self, mock_task_class, mock_user_class, mock_notif,
                                      mock_db_session, mock_task, mock_collaborator):
        """Test updating task collaborators"""
        mock_task_class.query.get.return_value = mock_task
        collaborators_mock = Mock()
        collaborators_mock.__iter__ = Mock(return_value=iter([]))
        mock_task.collaborators = collaborators_mock
        mock_user_class.query.filter_by.return_value.first.return_value = mock_collaborator

        data = {"collaborators": ["collaborator@example.com"]}

        result = update_task(1, data, None)

        assert result == mock_task
        mock_task.collaborators.clear.assert_called_once()
        mock_task.collaborators.append.assert_called()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Attachment')
    @patch('app.services.task_services.Task')
    def test_update_task_add_attachments(self, mock_task_class, mock_attachment_class, mock_notif,
                                        mock_db_session, mock_task):
        """Test adding new attachments to task"""
        mock_task_class.query.get.return_value = mock_task

        mock_file = Mock()
        mock_file.filename = "newfile.txt"
        mock_file.read.return_value = b"new content"

        result = update_task(1, {}, [mock_file])

        assert result == mock_task
        mock_attachment_class.assert_called_once()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_remove_attachments(self, mock_task_class, mock_notif, mock_db_session, mock_task):
        """Test removing attachments from task"""
        mock_task_class.query.get.return_value = mock_task
        
        mock_attachment = Mock()
        mock_attachment.id = 1
        mock_task.attachments = [mock_attachment]

        data = {"existing_attachments": "[]"}

        result = update_task(1, data, None)

        assert result == mock_task
        mock_db_session.delete.assert_called_once_with(mock_attachment)

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_completed_removes_notifications(self, mock_task_class, mock_notif,
                                                        mock_db_session, mock_task):
        """Test that completing a task removes notifications"""
        mock_task_class.query.get.return_value = mock_task
        # Mock the status to be COMPLETED after update
        mock_task.status = TaskStatus.COMPLETED

        data = {"status": "Completed"}

        result = update_task(1, data, None)

        # Verify notification removal was called
        mock_notif.remove_notifications_for_task.assert_called_once_with(mock_task)

    @patch('app.services.task_services.Task')
    def test_update_task_not_found(self, mock_task_class, mock_db_session):
        """Test updating non-existent task"""
        mock_task_class.query.get.return_value = None

        with pytest.raises(ValueError, match="Task with task ID .* not found"):
            update_task(999, {}, None)

    @patch('app.services.task_services.Task')
    def test_update_task_database_error(self, mock_task_class, mock_db_session, mock_task):
        """Test updating task with database error"""
        mock_task_class.query.get.return_value = mock_task
        mock_db_session.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(RuntimeError, match="Database error while updating task"):
            update_task(1, {"title": "New Title"}, None)

        mock_db_session.rollback.assert_called()

    @patch('app.services.task_services.notification_service')
    @patch('app.services.task_services.Task')
    def test_update_task_invalid_date_format(self, mock_task_class, mock_notif, mock_db_session, mock_task):
        """Test updating with invalid date format"""
        mock_task_class.query.get.return_value = mock_task

        data = {"duedate": "invalid-date"}

        with pytest.raises(ValueError, match="Invalid date format"):
            update_task(1, data, None)

        mock_db_session.rollback.assert_called()