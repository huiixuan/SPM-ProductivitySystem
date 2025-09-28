from flask import Blueprint, request, jsonify
from app.models import db, User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from app.services.user_service import create_user, validate_login, get_user_by_email

auth_bp = Blueprint("auth", __name__)

# Track failed login attempts in memory
failed_attempts = {}
LOCKOUT_TIME = timedelta(minutes=15)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get("name")
    role = data.get("role")
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not role or not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 400

    # Create new user
    user = create_user(name, email, role, password)

    # Create access token
    access_token = create_access_token(identity=user.email)
    return jsonify({"message": "User registered successfully", "access_token": access_token}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    remember_me = data.get("remember_me", False)  # Get remember_me flag

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    now = datetime.utcnow()

    # Lockout check
    if email in failed_attempts:
        attempt = failed_attempts[email]
        if attempt["count"] >= 3:
            lock_time = attempt.get("lock_time")
            if lock_time and now - lock_time < LOCKOUT_TIME:
                return jsonify({"error": "Account locked for 15 minutes"}), 403
            else:
                failed_attempts.pop(email)

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        # Reset failed attempts on success
        failed_attempts.pop(email, None)

        # Set token expiration based on remember_me
        if remember_me:
            # 1 week expiration for "Remember me"
            expires_delta = timedelta(days=7)
        else:
            # 1 hour expiration for normal session
            expires_delta = timedelta(hours=1)

        # Use email as identity
        access_token = create_access_token(
            identity=email,
            expires_delta=expires_delta,
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "expires_in": expires_delta.total_seconds()  # Optional: send expiration time
        }), 200
    else:
        # Track failed attempts
        if email not in failed_attempts:
            failed_attempts[email] = {"count": 1, "lock_time": None}
        else:
            failed_attempts[email]["count"] += 1
            if failed_attempts[email]["count"] == 3:
                failed_attempts[email]["lock_time"] = now

        return jsonify({"error": "Invalid email or password"}), 401

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get("email")
        new_password = data.get("new_password")

        if not email or not new_password:
            return jsonify({"error": "email and new password are required"}), 400

        # Find the user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Update the password
        user.set_password(new_password)
        db.session.commit()

        return jsonify({"message": "Password reset successfully"}), 200

    except Exception as e:
        print(f"Password reset error: {e}")
        db.session.rollback()
        return jsonify({"error": "Server error during password reset"}), 500


@auth_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    try:
        # Get the current user's identity (email)
        email = get_jwt_identity()
        
        # Look up the user in the database to get their actual role
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        role = user.role.lower()
        print(f"Debug: User {email}, Role: {role}")  # This will help debug

        if role == "manager":
            return jsonify({"dashboard": "Manager"}), 200
        elif role == "hr":
            return jsonify({"dashboard": "HR"}), 200
        elif role == "director":
            return jsonify({"dashboard": "Director"}), 200
        elif role == "staff":
            return jsonify({"dashboard": "Staff"}), 200
        else:
            return jsonify({"error": "Unauthorized role"}), 403
    except Exception as e:
        print(f"Dashboard error: {e}")
        return jsonify({"error": "Server error"}), 500
