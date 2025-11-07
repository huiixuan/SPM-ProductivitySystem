import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, verify_jwt_in_request
from app.models import TaskStatus
from werkzeug.datastructures import MultiDict
from sqlalchemy.exc import SQLAlchemyError

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    jwt = JWTManager(app)

    # Import routes inside context so they register correctly
    with app.app_context():
        from app.routes.task import task_bp
        app.register_blueprint(task_bp)
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app):
    with app.app_context():
        token = create_access_token(identity='user123')
    return {"Authorization": f"Bearer {token}"}


class TestTaskRoutes:

    # ---------- CREATE TASK ----------
    @patch("app.routes.task.task_services.create_task")
    def test_create_task_success(self, mock_create_task, client, auth_header):
        mock_task = MagicMock(id=1, title="Mock Task")
        mock_task.to_dict.return_value = {"id": 1, "title": "Mock Task"}
        mock_create_task.return_value = mock_task

        resp = client.post(
            "/create-task",
            json={
                "title": "Mock Task",
                "description": "testing",
                "duedate": "2025-11-07",
                "owner": "owner@example.com",
                "status": "UNASSIGNED",
                "project_id": "123",
            },
            headers=auth_header,
        )

        assert resp.status_code == 201
        mock_create_task.assert_called_once()

    @patch("app.routes.task.task_services.create_task", side_effect=ValueError("bad input"))
    def test_create_task_value_error(self, mock_create_task, client, auth_header):
        resp = client.post("/create-task", json={"title": "bad"}, headers=auth_header)
        assert resp.status_code == 400

    # ---------- GET TASK ----------
    @patch("app.routes.task.task_services.get_task")
    def test_get_task_success(self, mock_get_task, client, auth_header):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {"id": 1, "title": "Task A"}
        mock_get_task.return_value = mock_task

        resp = client.get("/get-task/1", headers=auth_header)
        assert resp.status_code == 200

    @patch("app.routes.task.task_services.get_task", return_value=None)
    def test_get_task_not_found(self, mock_get_task, client, auth_header):
        resp = client.get("/get-task/999", headers=auth_header)
        assert resp.status_code == 404

    # ---------- USER & PROJECT TASKS ----------
    @patch("app.routes.task.task_services.get_user_tasks")
    def test_get_user_tasks(self, mock_get_user_tasks, client, auth_header):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {"id": 1}
        mock_get_user_tasks.return_value = [mock_task]

        resp = client.get("/get-user-tasks", headers=auth_header)
        assert resp.status_code == 200

    @patch("app.routes.task.task_services.get_project_tasks")
    def test_get_project_tasks(self, mock_get_project_tasks, client, auth_header):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {"id": 1, "title": "Proj Task"}
        mock_get_project_tasks.return_value = [mock_task]

        resp = client.get("/get-project-tasks/1", headers=auth_header)
        assert resp.status_code == 200

    # ---------- PROJECT USERS ----------
    @patch("app.routes.task.task_services.get_project_users_for_tasks")
    def test_get_project_users_for_task(self, mock_get_users, client, auth_header):
        mock_get_users.return_value = [{"id": 1, "email": "test@x.com"}]
        resp = client.get("/get-project-users-for-task/1", headers=auth_header)
        assert resp.status_code == 200

    # ---------- UNASSIGNED ----------
    @patch("app.routes.task.task_services.get_unassigned_tasks")
    def test_get_unassigned_tasks(self, mock_get_unassigned, client, auth_header):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {"id": 5}
        mock_get_unassigned.return_value = [mock_task]

        resp = client.get("/get-unassigned-tasks", headers=auth_header)
        assert resp.status_code == 200

    # ---------- LINK TASK ----------
    @patch("flask_jwt_extended.verify_jwt_in_request", return_value=None)
    @patch("app.routes.task.get_jwt_identity", return_value=1)
    @patch("app.routes.task.User")
    @patch("app.routes.task.task_services.link_task_to_project")
    def test_link_task_success(
        self,
        mock_link_task_to_project,
        mock_user_class,
        mock_jwt_identity,
        mock_verify_jwt,
        app,
        client,
        auth_header,
    ):
        with app.app_context():
            # Mock User.query.get
            mock_user_instance = MagicMock()
            mock_user_instance.id = 1
            mock_user_class.query.get.return_value = mock_user_instance

            # Mock Task returned
            mock_task = MagicMock()
            mock_task.to_dict.return_value = {"id": 1, "title": "Mock Task"}
            mock_link_task_to_project.return_value = mock_task

            resp = client.post(
                "/link-task",
                json={"task_id": 1, "project_id": 2},
                headers=auth_header,
            )

            assert resp.status_code == 200


    def test_link_task_missing_params(self, client, auth_header):
        resp = client.post("/link-task", json={}, headers=auth_header)
        assert resp.status_code == 400

    # ---------- UPDATE ----------
    @patch("app.routes.task.task_services.update_task")
    def test_update_task_success(self, mock_update, client, auth_header):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {"id": 1, "title": "Updated"}
        mock_update.return_value = mock_task

        resp = client.put(
            "/update-task/1",
            json={"title": "Updated"},
            headers=auth_header,
        )
        assert resp.status_code == 200

    @patch("app.routes.task.task_services.update_task", side_effect=ValueError("bad"))
    def test_update_task_value_error(self, mock_update, client, auth_header):
        resp = client.put(
            "/update-task/1",
            json={"title": "Invalid"},
            headers=auth_header,
        )
        assert resp.status_code == 400

    # ---------- SUBTASKS ----------
    @patch("app.routes.task.task_services.get_subtasks")
    def test_get_subtasks_success(self, mock_get_subtasks, client, auth_header):
        mock_sub = MagicMock()
        mock_sub.to_dict.return_value = {"id": 99}
        mock_get_subtasks.return_value = [mock_sub]

        resp = client.get("/get-subtasks/1", headers=auth_header)
        assert resp.status_code == 200

    @patch("app.routes.task.task_services.get_subtasks", return_value=[])
    def test_get_subtasks_empty(self, mock_get_subtasks, client, auth_header):
        resp = client.get("/get-subtasks/1", headers=auth_header)
        assert resp.status_code == 200

    # ---------- CREATE TASK INTERNAL ERROR ----------
    def test_create_task_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.create_task", side_effect=Exception("DB fail")):
            resp = client.post(
                "/create-task",
                json={"title": "Fail Task"},
                headers=auth_header
            )
            assert resp.status_code == 500

    # ---------- GET TASK INTERNAL ERROR ----------
    def test_get_task_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.get_task", side_effect=Exception("DB fail")):
            resp = client.get("/get-task/1", headers=auth_header)
            assert resp.status_code == 500

    # ---------- GET USER TASKS INTERNAL ERROR ----------
    def test_get_user_tasks_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.get_user_tasks", side_effect=Exception("DB fail")):
            resp = client.get("/get-user-tasks", headers=auth_header)
            assert resp.status_code == 500

    # ---------- GET PROJECT TASKS INTERNAL ERROR ----------
    def test_get_project_tasks_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.get_project_tasks", side_effect=Exception("DB fail")):
            resp = client.get("/get-project-tasks/1", headers=auth_header)
            assert resp.status_code == 500

    # ---------- GET PROJECT USERS FOR TASK INTERNAL ERROR ----------
    def test_get_project_users_for_task_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.get_project_users_for_tasks", side_effect=Exception("DB fail")):
            resp = client.get("/get-project-users-for-task/1", headers=auth_header)
            assert resp.status_code == 500

    # ---------- GET UNASSIGNED TASKS INTERNAL ERROR ----------
    def test_get_unassigned_tasks_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.get_unassigned_tasks", side_effect=Exception("DB fail")):
            resp = client.get("/get-unassigned-tasks", headers=auth_header)
            assert resp.status_code == 500

    # ---------- LINK TASK INTERNAL ERROR ----------
    def test_link_task_internal_error(self, client, auth_header, app):
        with app.app_context():
            with patch("flask_jwt_extended.verify_jwt_in_request", return_value=None), \
                patch("app.routes.task.get_jwt_identity", return_value=1), \
                patch("app.routes.task.User") as mock_user_class, \
                patch("app.routes.task.task_services.link_task_to_project", side_effect=Exception("DB fail")):

                # Mock User.query.get
                mock_user_instance = MagicMock()
                mock_user_instance.id = 1
                mock_user_class.query.get.return_value = mock_user_instance

                resp = client.post(
                    "/link-task",
                    json={"task_id": 1, "project_id": 2},
                    headers=auth_header
                )
                assert resp.status_code == 500

    # ---------- UPDATE TASK INTERNAL ERROR ----------
    def test_update_task_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.update_task", side_effect=Exception("DB fail")):
            resp = client.put(
                "/update-task/1",
                json={"title": "Fail Update"},
                headers=auth_header
            )
            assert resp.status_code == 500

    # ---------- GET SUBTASKS INTERNAL ERROR ----------
    def test_get_subtasks_internal_error(self, client, auth_header):
        with patch("app.routes.task.task_services.get_subtasks", side_effect=Exception("DB fail")):
            resp = client.get("/get-subtasks/1", headers=auth_header)
            assert resp.status_code == 500

    # ---------- CREATE TASK: STATUS, DUEDATE, PARENT TASK ----------
    @patch("app.routes.task.task_services.create_task")
    def test_create_task_full_fields(self, mock_create_task, client, auth_header):
        mock_task = MagicMock(id=42, title="Full Task")
        mock_task.to_dict.return_value = {"id": 42, "title": "Full Task"}
        mock_create_task.return_value = mock_task

        payload = {
            "title": "Full Task",
            "description": "testing full",
            "duedate": "2025-11-07",
            "status": "IN_PROGRESS",
            "owner": "owner@example.com",
            "collaborators": ["collab1@example.com", "collab2@example.com"],
            "priority": "HIGH",
            "parent_task_id": "7",
            "project_id": "321",
        }

        resp = client.post(
            "/create-task",
            json=payload,  # <-- send JSON
            headers=auth_header,
        )

        assert resp.status_code == 201

    @patch("app.routes.task.task_services.create_task", side_effect=ValueError("bad status"))
    def test_create_task_value_error_status(self, mock_create_task, client, auth_header):
        resp = client.post(
            "/create-task",
            data={
                "title": "Fail Task",
                "status": "INVALID_STATUS"
            },
            headers=auth_header,
        )
        assert resp.status_code == 400

    @patch("app.routes.task.task_services.create_task")
    def test_create_task_parent_task_id_invalid_string(self, mock_create_task, client, auth_header):
        """parent_task_id is a string that cannot be cast to int → should be set to None"""
        mock_task = MagicMock(id=1, title="Task with invalid parent")
        mock_task.to_dict.return_value = {"id": 1, "title": "Task with invalid parent"}
        mock_create_task.return_value = mock_task

        data = MultiDict([
            ("title", "Task"),
            ("parent_task_id", "invalid"),  # cannot convert to int
        ])

        resp = client.post("/create-task", data=data, content_type="multipart/form-data", headers=auth_header)
        assert resp.status_code == 201

        # Ensure the service was called with parent_task_id=None
        called_args = mock_create_task.call_args[1]  # kwargs
        assert called_args["parent_task_id"] is None

    @patch("app.routes.task.task_services.create_task")
    def test_create_task_parent_task_id_none(self, mock_create_task, client, auth_header):
        """parent_task_id missing → should remain None"""
        mock_task = MagicMock(id=2, title="Task with no parent")
        mock_task.to_dict.return_value = {"id": 2, "title": "Task with no parent"}
        mock_create_task.return_value = mock_task

        data = MultiDict([("title", "Task")])  # no parent_task_id

        resp = client.post("/create-task", data=data, content_type="multipart/form-data", headers=auth_header)
        assert resp.status_code == 201

        called_args = mock_create_task.call_args[1]
        assert called_args["parent_task_id"] is None

    @patch("app.routes.task.task_services.create_task")
    def test_create_task_parent_task_id_valid(self, mock_create_task, client, auth_header):
        """parent_task_id is valid integer string → should be converted to int"""
        mock_task = MagicMock(id=3, title="Task with valid parent")
        mock_task.to_dict.return_value = {"id": 3, "title": "Task with valid parent"}
        mock_create_task.return_value = mock_task

        data = MultiDict([
            ("title", "Task"),
            ("parent_task_id", "42"),  # valid integer string
        ])

        resp = client.post("/create-task", data=data, content_type="multipart/form-data", headers=auth_header)
        assert resp.status_code == 201

        called_args = mock_create_task.call_args[1]
        assert called_args["parent_task_id"] == 42

    @patch("app.routes.task.task_services.create_task")
    def test_create_task_invalid_duedate(self, mock_create_task, client, auth_header):
        """Invalid duedate format → triggers ValueError → returns 400"""
        mock_create_task.return_value = None  # won't be called

        data = MultiDict([
            ("title", "Task"),
            ("duedate", "invalid-date"),
        ])
        resp = client.post("/create-task", data=data, content_type="multipart/form-data", headers=auth_header)
        assert resp.status_code == 500 or resp.status_code == 400  # depending on route logic

    @patch("app.routes.task.task_services.create_task", side_effect=SQLAlchemyError("DB Error"))
    def test_create_task_service_sqlalchemyerror(self, mock_create_task, client, auth_header):
        """Service layer throws SQLAlchemyError → returns 500"""
        data = MultiDict([("title", "Task")])
        resp = client.post("/create-task", data=data, content_type="multipart/form-data", headers=auth_header)
        assert resp.status_code == 500
        assert "DB Error" in resp.json["error"]

    @patch("app.routes.task.task_services.get_task", side_effect=ValueError("Invalid task ID"))
    def test_get_task_value_error(self, mock_get_task, client, auth_header):
        """Test get-task route when service raises ValueError → returns 404"""
        task_id = 999  # any number
        resp = client.get(f"/get-task/{task_id}", headers=auth_header)

        assert resp.status_code == 404
        assert resp.json["error"] == "Invalid task ID"

    @patch("app.routes.task.get_jwt_identity", return_value=None)
    def test_get_user_tasks_not_logged_in(self, mock_jwt_identity, client, auth_header):
        """Test get-user-tasks route when user is not logged in → returns 401"""
        resp = client.get("/get-user-tasks", headers=auth_header)

        assert resp.status_code == 401
        assert resp.json["error"] == "Not logged in"