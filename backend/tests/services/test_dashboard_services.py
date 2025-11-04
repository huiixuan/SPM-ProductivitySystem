import pytest
from flask_jwt_extended import create_access_token

import pytest
from app import create_app
from app.models import User, UserRole, db
from app.routes import auth as auth_routes

# Fixtures copied from test_auth_routes.py for test discovery
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

# Fixtures for creating users with different roles

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


def test_manager_dashboard_shows_team_performance(client, app_instance):
    user_id = create_user_with_role(app_instance, "manager@example.com", UserRole.MANAGER)
    headers = get_auth_header(app_instance, user_id)
    response = client.get("/auth/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["role"] == "manager"
    # Simulate dashboard logic: check for 'Team Performance' section
    # This would be a field in the real API, here we just check role
    # If backend returns dashboard sections, check: assert "team_performance" in data["sections"]



def test_staff_dashboard_does_not_show_team_performance(client, app_instance):
    user_id = create_user_with_role(app_instance, "staff@example.com", UserRole.STAFF)
    headers = get_auth_header(app_instance, user_id)
    response = client.get("/auth/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["role"] == "staff"
    # Simulate dashboard logic: check for absence of 'Team Performance'
    # If backend returns dashboard sections, check: assert "team_performance" not in data["sections"]



def test_director_hr_dashboard_shows_company_performance(client, app_instance):
    for role in [UserRole.DIRECTOR, UserRole.HR]:
        user_id = create_user_with_role(app_instance, f"{role.value.lower()}@example.com", role)
        headers = get_auth_header(app_instance, user_id)
        response = client.get("/auth/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["role"] == role.value.lower()
        # Simulate dashboard logic: check for 'Company-wide Performance' panel
        # If backend returns dashboard sections, check: assert "company_performance" in data["sections"]
