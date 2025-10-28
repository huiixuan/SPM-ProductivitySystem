from app.models import db, User, UserRole
from flask import jsonify 
from sqlalchemy.exc import SQLAlchemyError

def create_user(name, email, role, password):
    """Create and save a new user"""
    if isinstance(role, str):
        try:
            role = UserRole[role.upper()]
        except KeyError as exc:
            raise ValueError(f"Invalid role: {role}") from exc
    elif not isinstance(role, UserRole):
        raise ValueError("Role must be a str or UserRole")

    user = User(name=name, role=role, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def get_user_by_email(email):
    """Find a user by email"""
    return User.query.filter_by(email=email).first()

def validate_login(email, password):
    """Check if email and password are valid"""
    user = get_user_by_email(email)
    if user and user.check_password(password):
        return user
    return None

def get_users_info():
    try:
        users = User.query.all()
        users_data = [
            {"id": user.id, "role": user.role.value, "name": user.name, "email": user.email} 
            for user in users
        ]

        return users_data
    
    except SQLAlchemyError as e:
        return jsonify({"error": "Database error", "message": "Unable to fetch users."})
