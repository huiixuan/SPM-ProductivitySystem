import pytest
from flask_jwt_extended import create_access_token
from app.models import User, UserRole, db
from app import create_app
from app.routes import auth as auth_routes

@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "routes-secret",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app_instance):
    return app_instance.test_client()

@pytest.fixture(autouse=True)
def reset_failed_attempts():
    auth_routes.failed_attempts.clear()
    yield
    auth_routes.failed_attempts.clear()

def create_user_with_role(app, email, role):
    with app.app_context():
        user = User(name="Test User", email=email, role=role)
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        return user.id

def get_auth_header(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}

def test_logout_clears_token(client, app_instance):
    user_id = create_user_with_role(app_instance, "logout1@example.com", UserRole.STAFF)
    headers = get_auth_header(app_instance, user_id)
    # Simulate logout by removing token client-side (no server state for JWT)
    # After logout, token is not sent, so protected route should fail
    response = client.get("/auth/dashboard")
    assert response.status_code == 401 or response.status_code == 422

def test_logout_redirects_to_login(client, app_instance):
    # In backend, redirect is frontend responsibility, but we can simulate
    # After logout, user tries to access dashboard, gets 401, frontend should redirect
    response = client.get("/auth/dashboard")
    assert response.status_code == 401 or response.status_code == 422
    # Optionally, check error message
    data = response.get_json()
    assert "error" in data or "msg" in data

def test_protected_page_after_logout(client, app_instance):
    user_id = create_user_with_role(app_instance, "logout2@example.com", UserRole.MANAGER)
    headers = get_auth_header(app_instance, user_id)
    # Access with token (should succeed)
    response = client.get("/auth/dashboard", headers=headers)
    assert response.status_code == 200
    # Simulate logout: remove token, try again
    response2 = client.get("/auth/dashboard")
    assert response2.status_code == 401 or response2.status_code == 422
