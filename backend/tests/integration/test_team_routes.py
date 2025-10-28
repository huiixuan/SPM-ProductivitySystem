import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.models import db, User


@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "team-secret",
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


@pytest.fixture
def auth_headers(app_instance):
    with app_instance.app_context():
        user = User(name="Member", email="member@example.com", role="STAFF")
        user.set_password("password")
        db.session.add(user)
        other = User(name="Other", email="other@example.com", role="MANAGER")
        other.set_password("password")
        db.session.add(other)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_get_team_members_returns_list(client, auth_headers):
    response = client.get("/api/team/members", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "members" in data
    assert any(member["email"] == "member@example.com" for member in data["members"])


def test_get_team_members_user_not_found_returns_404(client, app_instance):
    with app_instance.app_context():
        token = create_access_token(identity="999")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/team/members", headers=headers)
    assert response.status_code == 404
    assert response.get_json()["error"] == "User not found"
