import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from app.models import db, UserRole, User
from app.routes.auth import auth_bp
from datetime import timedelta

@pytest.fixture
def app():
    """Full app with JWT and the auth blueprint registered under /auth."""
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY="test-jwt-secret",
    )
    db.init_app(app)
    JWTManager(app)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

# Check successful registration
def test_register_success(client):
    payload = {
        "name": "Reg User",
        "role": "STAFF",  # API accepts string; model stores enum
        "email": "reg@example.com",
        "password": "strongpw"
    }
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 201
    body = res.get_json()
    assert "access_token" in body
    assert body["message"] == "User registered successfully"

# Check registration with missing fields
def test_register_missing_fields(client):
    res = client.post("/auth/register", json={"email": "x@y.com"})
    assert res.status_code == 400
    assert "error" in res.get_json()

# Check successful login and token expiry with remember_me variations
def test_login_success_and_expiry_claim(client, app):
    # Seed a user
    with app.app_context():
        u = User(name="Lara", email="lara@example.com", role=UserRole.STAFF)
        u.set_password("pw")
        db.session.add(u)
        db.session.commit()

    # login with remember_me=False (1 hour)
    res = client.post("/auth/login", json={"email": "lara@example.com", "password": "pw", "remember_me": False})
    assert res.status_code == 200
    body = res.get_json()
    assert body["message"] == "Login successful"
    assert "access_token" in body
    assert int(body["expires_in"]) in (3600, 3600.0)

    # login with remember_me=True (1 week)
    res2 = client.post("/auth/login", json={"email": "lara@example.com", "password": "pw", "remember_me": True})
    assert res2.status_code == 200
    body2 = res2.get_json()
    assert int(body2["expires_in"]) in (604800, 604800.0)

# Check lockout after 3 failed logins
def test_login_lockout_after_three_failures(client, app):
    # Seed a user
    with app.app_context():
        u = User(name="Zed", email="zed@example.com", role=UserRole.STAFF)
        u.set_password("pw")
        db.session.add(u)
        db.session.commit()

    # 1st wrong
    r1 = client.post("/auth/login", json={"email": "zed@example.com", "password": "bad"})
    assert r1.status_code == 401
    # 2nd wrong
    r2 = client.post("/auth/login", json={"email": "zed@example.com", "password": "bad"})
    assert r2.status_code == 401
    # 3rd wrong triggers lock time set
    r3 = client.post("/auth/login", json={"email": "zed@example.com", "password": "bad"})
    assert r3.status_code == 401
    # Now locked
    r4 = client.post("/auth/login", json={"email": "zed@example.com", "password": "pw"})
    assert r4.status_code in (401, 403)  # Depending on timing, 403 "locked" or 401 if state reset

# Check password reset and then login
def test_forgot_password_and_login_with_new_password(client, app):
    # Seed a user
    with app.app_context():
        u = User(name="Hana", email="hana@example.com", role=UserRole.HR)
        u.set_password("oldpw")
        db.session.add(u)
        db.session.commit()

    # Reset password
    res = client.post("/auth/forgot-password", json={"email": "hana@example.com", "new_password": "newpw"})
    assert res.status_code == 200
    assert res.get_json()["message"] == "Password reset successfully"

    # Login with new password
    res2 = client.post("/auth/login", json={"email": "hana@example.com", "password": "newpw"})
    assert res2.status_code == 200

# Check access with valid token
def test_dashboard_authorized_with_token(client, app):
    with app.app_context():
        u = User(name="Manny", email="manny@example.com", role=UserRole.MANAGER)
        u.set_password("pw")
        db.session.add(u)
        db.session.commit()

        # Create token for the user
        token = create_access_token(identity=u.email)

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/auth/dashboard", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["dashboard"] == "Manager"

# Check access with invalid token
def test_dashboard_with_invalid_token(client):
    """Ensure invalid token is rejected"""
    headers = {"Authorization": "Bearer INVALIDTOKEN"}
    res = client.get("/auth/dashboard", headers=headers)
    assert res.status_code in (401, 422)

# Check access with expired token
def test_dashboard_with_expired_token(client, app):
    """Ensure expired token cannot access dashboard"""
    with app.app_context():
        u = User(name="ExpiredUser", email="expired@example.com", role=UserRole.STAFF)
        u.set_password("pw")
        db.session.add(u)
        db.session.commit()
        # Create token with 0-second lifespan
        token = create_access_token(identity=u.email, expires_delta=timedelta(seconds=-1))

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/auth/dashboard", headers=headers)
    assert res.status_code == 401  # Token expired

# Check duplicate email registration fails
def test_register_duplicate_email(client):
    payload = {"name": "D1", "role": "STAFF", "email": "dupe@example.com", "password": "pw"}
    client.post("/auth/register", json=payload)
    res = client.post("/auth/register", json=payload)
    assert res.status_code in (400, 409)

# Check login with non-existent user
def test_login_nonexistent_user(client):
    res = client.post("/auth/login", json={"email": "nope@example.com", "password": "pw"})
    assert res.status_code == 401

# Check accessing dashboard without token
def test_dashboard_without_token(client):
    res = client.get("/auth/dashboard")
    assert res.status_code == 401

# Check password reset for non-existent user
def test_forgot_password_nonexistent_user(client):
    res = client.post("/auth/forgot-password", json={"email": "ghost@example.com", "new_password": "pw"})
    assert res.status_code in (400, 404)

# Check token is returned in login response
def test_token_in_login_response(client, app):
    """Ensure token is returned after successful login"""
    with app.app_context():
        u = User(name="TokenUser", email="token@example.com", role=UserRole.STAFF)
        u.set_password("pw")
        db.session.add(u)
        db.session.commit()

    res = client.post("/auth/login", json={"email": "token@example.com", "password": "pw"})
    data = res.get_json()
    assert res.status_code == 200
    assert "access_token" in data
    assert isinstance(data["access_token"], str)

