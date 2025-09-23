from flask import Blueprint, request, jsonify
from app.models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return jsonify({"message": "Login successful", "user": {
            "id": user.id,
            "role": user.role,
            "name": user.name,
            "username": user.username
        }}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    role = data.get("role")
    name = data.get("name")
    username = data.get("username")
    password = data.get("password")

    if not role or not name or not username or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    # Create new user
    user = User(role=role, name=name, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201
