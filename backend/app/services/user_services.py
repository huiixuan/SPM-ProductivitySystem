from app.models import db, User
from flask import jsonify 
from sqlalchemy.exc import SQLAlchemyError

def get_all_emails():
    try:
        users_email = User.query.with_entities(User.email).all()
        return [email for (email,) in users_email]
    
    except SQLAlchemyError as e:
        return jsonify({"error": "Database error", "message": "Unable to fetch uasers."})