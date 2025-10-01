from flask import Blueprint, request, jsonify
from app.models import db, User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.services.user_services import create_user

# The blueprint for authentication routes
auth_bp = Blueprint("auth", __name__)

# In-memory dictionary to track failed login attempts for brute-force protection
failed_attempts = {}
LOCKOUT_TIME = timedelta(minutes=15)


# ---------- Register ----------
@auth_bp.route('/register', methods=['POST'])
def register():
    """Registers a new user."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    role = (data.get("role") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not all([role, name, email, password]):
        return jsonify({"error": "All fields are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    # Create user via service and add to the session
    user = create_user(name, email, role, password)

    # Create a token with the new user's unique ID as the identity
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "message": "User registered successfully",
        "access_token": access_token
    }), 201


# ---------- Login ----------
@auth_bp.route("/login", methods=["POST"])
def login():
    """Logs in a user and returns a JWT."""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember_me = bool(data.get("remember_me", False))

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    now = datetime.utcnow()

    # Lockout check to prevent brute-force attacks
    if email in failed_attempts:
        attempt = failed_attempts[email]
        if attempt["count"] >= 3:
            lock_time = attempt.get("lock_time")
            if lock_time and now - lock_time < LOCKOUT_TIME:
                return jsonify({"error": "Account locked for 15 minutes"}), 403
            else:
                # Reset attempts if lockout time has passed
                failed_attempts.pop(email, None)

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        # On successful login, clear any failed attempts
        failed_attempts.pop(email, None)

        # Set token duration
        expires_delta = timedelta(days=7) if remember_me else timedelta(hours=1)

        # ✅ CRITICAL: The token's identity is the user's integer ID, converted to a string.
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=expires_delta,
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "expires_in": int(expires_delta.total_seconds())
        }), 200
    else:
        # On failed login, track the attempt
        if email not in failed_attempts:
            failed_attempts[email] = {"count": 1, "lock_time": None}
        else:
            failed_attempts[email]["count"] += 1
            if failed_attempts[email]["count"] >= 3:
                failed_attempts[email]["lock_time"] = now

        return jsonify({"error": "Invalid email or password"}), 401


# ---------- Forgot Password ----------
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Allows a user to reset their password."""
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        new_password = data.get("new_password") or ""

        if not email or not new_password:
            return jsonify({"error": "Email and new password are required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            # Return a generic message to prevent user enumeration
            return jsonify({"message": "If a user with that email exists, the password has been reset."}), 200

        user.set_password(new_password)
        db.session.commit()
        return jsonify({"message": "Password reset successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500


# ---------- Dashboard (Example Protected Route) ----------
@auth_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    """An example of a protected route that returns user-specific data."""
    try:
        # ✅ CRITICAL: Get the user ID (as a string) from the token's identity.
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)

        # Fetch the user by their primary key (ID). This is efficient and correct.
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({"error": "User associated with token not found"}), 404
            
        # Return the user's role for the dashboard
        role = user.role.value.lower()
        return jsonify({"dashboard": role}), 200

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid token identity"}), 401
    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500
