import pytest
from datetime import datetime
from unittest.mock import patch
from flask_jwt_extended import create_access_token
from app.models import db, User, Task, Project, Comment, TaskStatus, ProjectStatus


@pytest.fixture
def app():
    from app import create_app
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "JWT_SECRET_KEY": "test-secret",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_comment_success(client):
    """Test successful comment creation"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(
            title="Test Task", 
            description="Test task", 
            duedate=datetime.now().date(), 
            owner=user, 
            project=project
        )
        
        db.session.add_all([user, project, task])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        comment_data = {"content": "This is a test comment"}
        response = client.post(f"/api/comments/save-comment/{task.id}", json=comment_data, headers=headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "comment" in data
        assert data["comment"]["content"] == comment_data["content"]


def test_create_comment_missing_content(client):
    """Test comment creation with missing content"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
        
        db.session.add_all([user, project, task])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        comment_data = {"content": ""}
        response = client.post(f"/api/comments/save-comment/{task.id}", json=comment_data, headers=headers)
        
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_create_comment_task_not_found(client):
    """Test comment creation for non-existent task"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        comment_data = {"content": "This comment should fail"}
        response = client.post("/api/comments/save-comment/999", json=comment_data, headers=headers)
        
        assert response.status_code == 404
        assert "error" in response.get_json()


def test_get_comments_success(client):
    """Test successful retrieval of comments"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
        
        comment = Comment(task=task, user=user, content="Test comment")
        
        db.session.add_all([user, project, task, comment])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get(f"/api/comments/get-comments/{task.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["content"] == "Test comment"


def test_get_comments_empty(client):
    """Test retrieval of comments for task with no comments"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
        
        db.session.add_all([user, project, task])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get(f"/api/comments/get-comments/{task.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []


def test_get_comments_task_not_found(client):
    """Test retrieval of comments for non-existent task"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/comments/get-comments/999", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []


def test_comments_jwt_required(client):
    """Test that comments endpoints require JWT authentication"""
    # Test POST without auth
    response = client.post("/api/comments/save-comment/1", json={"content": "Test comment"})
    assert response.status_code == 401
    
    # Test GET without auth  
    response = client.get("/api/comments/get-comments/1")
    assert response.status_code == 401


def test_comment_creation_triggers_notification(client):
    """Test that comment creation triggers notification service"""
    with patch('app.routes.comments.notification_services.create_comment_notification') as mock_notification:
        with client.application.app_context():
            user = User(email="test@example.com", name="Test User", role="STAFF")
            user.set_password("password123")
            
            project = Project(name="Test Project", owner=user)
            task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
            
            db.session.add_all([user, project, task])
            db.session.commit()

            access_token = create_access_token(identity=str(user.id))
            headers = {"Authorization": f"Bearer {access_token}"}

            comment_data = {"content": "This comment should trigger notification"}
            response = client.post(f"/api/comments/save-comment/{task.id}", json=comment_data, headers=headers)
            
            assert response.status_code == 201
            mock_notification.assert_called_once()


def test_comment_user_info_included(client):
    """Test that comment response includes user information"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
        
        comment = Comment(task=task, user=user, content="Test comment")
        
        db.session.add_all([user, project, task, comment])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get(f"/api/comments/get-comments/{task.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data[0]["user_email"] == "test@example.com"


def test_comment_content_length_validation(client):
    """Test that comment content is properly validated"""
    with client.application.app_context():
        user = User(email="test@example.com", name="Test User", role="STAFF")
        user.set_password("password123")
        
        project = Project(name="Test Project", owner=user)
        task = Task(title="Test Task", duedate=datetime.now().date(), owner=user, project=project)
        
        db.session.add_all([user, project, task])
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}

        long_content = "A" * 1000
        comment_data = {"content": long_content}
        response = client.post(f"/api/comments/save-comment/{task.id}", json=comment_data, headers=headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["comment"]["content"] == long_content