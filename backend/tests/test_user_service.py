import pytest
from app import create_app
from app.models import db, User
from app.services.user_services import create_user, get_user_by_email, validate_login

@pytest.fixture
def app():
    """Create a Flask app with a test database."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """For later use in tests."""
    return app.test_client()

def test_create_and_get_user(app):
    """Create a user and fetch them."""
    with app.app_context():
        create_user("Alice", "alice@example.com", "manager", "password123")

        user = get_user_by_email("alice@example.com")
        assert user is not None
        assert user.name == "Alice"
        assert user.email == "alice@example.com"
        assert user.role == "manager"
        assert user.check_password("password123") is True

def test_validate_login_success(app):
    """Validate correct login credentials."""
    with app.app_context():
        create_user("Bob", "bob@example.com", "staff", "secret")
        user = validate_login("bob@example.com", "secret")
        assert user is not None
        assert user.email == "bob@example.com"

def test_validate_login_failure(app):
    """Validate wrong credentials fail."""
    with app.app_context():
        create_user("Charlie", "charlie@example.com", "director", "topsecret")
        user = validate_login("charlie@example.com", "wrongpassword")
        assert user is None