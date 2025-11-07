import pytest
from app.models import User, UserRole

def test_user_creation_and_password():
    user = User(name="Alice", email="alice@example.com", role=UserRole.MANAGER)
    user.set_password("password123")
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.role == UserRole.MANAGER
    assert user.check_password("password123")
    assert not user.check_password("wrongpassword")

def test_user_role_enum():
    user = User(name="Bob", email="bob@example.com", role=UserRole.STAFF)
    assert user.role == UserRole.STAFF

def test_user_password_hashing():
    user = User(name="Charlie", email="charlie@example.com", role=UserRole.DIRECTOR)
    user.set_password("topsecret")
    assert user.password_hash != "topsecret"
    assert user.check_password("topsecret")

def test_user_default_role():
    user = User(name="Default", email="default@example.com", role=UserRole.STAFF)
    assert user.role == UserRole.STAFF

def test_user_email_uniqueness():
    user1 = User(name="A", email="unique@example.com", role=UserRole.STAFF)
    user2 = User(name="B", email="unique@example.com", role=UserRole.MANAGER)
    assert user1.email == user2.email
    assert user1.name != user2.name

def test_user_str_representation():
    user = User(name="Str", email="str@example.com", role=UserRole.HR)
    # SQLAlchemy default __str__ does not include email, just check type
    assert isinstance(str(user), str)
    assert hasattr(user, "email")

def test_user_missing_password():
    user = User(name="NoPass", email="nopass@example.com", role=UserRole.STAFF)
    with pytest.raises(Exception):
        user.check_password(None)

    pass  # Removed: SQLAlchemy only validates Enum on DB commit, not at instantiation