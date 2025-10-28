import pytest
from datetime import timedelta
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import db, User, UserRole
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


@pytest.fixture
def create_user(app_instance):
    def _create_user(email: str, password: str = "password", role: UserRole = UserRole.STAFF):
        with app_instance.app_context():
            user = User(name="Test User", email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return {"id": user.id, "email": user.email}

    return _create_user


@pytest.fixture
def auth_headers(app_instance, create_user):
    user = create_user("auth@example.com")
    with app_instance.app_context():
        token = create_access_token(identity=str(user["id"]))
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_user_and_token(client, app_instance):
    payload = {
        "name": "Alice",
        "email": "alice@example.com",
        "role": "manager",
        "password": "secret123",
    }

    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "User registered successfully"
    assert "access_token" in data

    with app_instance.app_context():
        user = User.query.filter_by(email="alice@example.com").first()
        assert user is not None
        assert user.role == UserRole.MANAGER
        assert user.check_password("secret123")


def test_register_missing_fields_returns_400(client):
    response = client.post("/auth/register", json={"email": "missing@example.com"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "All fields are required"


def test_register_duplicate_email_returns_400(client, app_instance, create_user):
    create_user("duplicate@example.com")

    response = client.post(
        "/auth/register",
        json={
            "name": "Dup",
            "email": "duplicate@example.com",
            "role": "staff",
            "password": "abc123",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Email already exists"


def test_login_success_with_remember_me(client, create_user):
    user = create_user("login@example.com", "supersecret")

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "supersecret",
            "remember_me": True,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Login successful"
    assert data["expires_in"] == int(timedelta(days=7).total_seconds())
    assert auth_routes.failed_attempts == {}


def test_login_missing_fields_returns_400(client):
    response = client.post("/auth/login", json={"email": ""})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Email and password are required"


def test_login_invalid_credentials_and_lockout(client, create_user):
    user = create_user("locked@example.com", "correct-password")

    for attempt in range(3):
        res = client.post(
            "/auth/login",
            json={"email": user["email"], "password": "wrong"},
        )
        assert res.status_code == 401
        assert res.get_json()["error"] == "Invalid email or password"

    # Fourth attempt within lockout window should be forbidden
    res = client.post(
        "/auth/login",
        json={"email": user["email"], "password": "wrong"},
    )
    assert res.status_code == 403
    assert res.get_json()["error"] == "Account locked for 15 minutes"


def test_forgot_password_success(client, app_instance, create_user):
    user = create_user("reset@example.com", "oldpass")

    response = client.post(
        "/auth/forgot-password",
        json={"email": user["email"], "new_password": "newpass"},
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Password reset successfully"

    with app_instance.app_context():
        refreshed = db.session.get(User, user["id"])
        assert refreshed.check_password("newpass")


def test_forgot_password_missing_fields(client):
    response = client.post("/auth/forgot-password", json={"email": ""})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Email and new password are required"


def test_forgot_password_nonexistent_user_returns_generic_message(client):
    response = client.post(
        "/auth/forgot-password",
        json={"email": "ghost@example.com", "new_password": "whatever"},
    )
    assert response.status_code == 200
    assert "password has been reset" in response.get_json()["message"]


def test_dashboard_returns_role_and_email(client, auth_headers, app_instance):
    response = client.get("/auth/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["role"] == "staff"
    assert data["email"] == "auth@example.com"


def test_dashboard_user_not_found_returns_404(client, app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="999")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/dashboard", headers=headers)
    assert response.status_code == 404
    assert response.get_json()["error"] == "User associated with token not found"


def test_dashboard_invalid_identity_returns_401(client, app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="not-an-int")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/dashboard", headers=headers)
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid token identity"
