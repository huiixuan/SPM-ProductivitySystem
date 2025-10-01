from app.models import db, User
from flask import jsonify 
from sqlalchemy.exc import SQLAlchemyError

def create_user(name, email, role, password):
    """Create and save a new user"""
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

def get_all_emails():
    try:
        users_email = User.query.with_entities(User.email).all()
        return [email for (email,) in users_email]
    
    except SQLAlchemyError as e:
        return jsonify({"error": "Database error", "message": "Unable to fetch users."})
