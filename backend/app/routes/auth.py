from flask import Blueprint, request, jsonify
from app.services.user_services import create_user, validate_login, get_user_by_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = validate_login(email, password)

    if user:
        return jsonify({"message": "Login successful", "user": {
            "id": user.id,
            "role": user.role,
            "email": user.email
        }}), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    role = data.get("role")
    email = data.get("email")
    password = data.get("password")

    if not role or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Check if email already exists
    if get_user_by_email(email):
        return jsonify({"error": "Email already exists"}), 400

    # Create new user
    create_user(email, role, password)
    return jsonify({"message": "User registered successfully"}), 201
