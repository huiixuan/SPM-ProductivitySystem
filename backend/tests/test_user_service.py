import pytest
from app.models import db, UserRole
from app.services.user_services import create_user, get_user_by_email, validate_login
from flask import Flask
from sqlalchemy.exc import IntegrityError

@pytest.fixture
def app():
    """Minimal Flask app bound to the SQLAlchemy db for unit tests."""
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="test-secret",
    )
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def ctx(app):
    """Push an app context for tests that call the database directly."""
    with app.app_context():
        yield

# Check user creation, retrieval, and password validation
def test_create_and_get_user(ctx):
    user = create_user("Alice", "alice@example.com", UserRole.MANAGER, "password123")
    fetched = get_user_by_email("alice@example.com")
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.name == "Alice"
    assert fetched.email == "alice@example.com"
    # role is an enum, not a string
    assert fetched.role == UserRole.MANAGER
    assert fetched.check_password("password123") is True

# Check login validation
def test_validate_login_success(ctx):
    create_user("Bob", "bob@example.com", UserRole.STAFF, "secret")
    user = validate_login("bob@example.com", "secret")
    assert user is not None
    assert user.email == "bob@example.com"

# Check login failure with wrong password
def test_validate_login_failure(ctx):
    create_user("Charlie", "charlie@example.com", UserRole.DIRECTOR, "topsecret")
    user = validate_login("charlie@example.com", "wrongpassword")
    assert user is None

# xxx
def test_get_all_emails_returns_list(ctx):
    create_user("Dana", "dana@example.com", UserRole.HR, "pw1")
    create_user("Eve", "eve@example.com", UserRole.STAFF, "pw2")
    emails = get_all_emails()
    assert isinstance(emails, list)
    assert set(emails) >= {"dana@example.com", "eve@example.com"}

# Check behavior when user not found
def test_get_user_by_email_nonexistent(ctx):
    assert get_user_by_email("boo@example.com") is None

# Check password hashing and verification
def test_check_password_incorrect(ctx):
    u = create_user("FailUser", "fail@example.com", UserRole.STAFF, "pw")
    assert u.check_password("wrong") is False

# Check login with non-existent user
def test_validate_login_no_user(ctx):
    user = validate_login("nouser@example.com", "pw")
    assert user is None

# Check duplicate email raises IntegrityError
def test_duplicate_email_raises(ctx):
    create_user("X", "dup@example.com", UserRole.HR, "pw")
    with pytest.raises(IntegrityError):
        create_user("Y", "dup@example.com", UserRole.STAFF, "pw")