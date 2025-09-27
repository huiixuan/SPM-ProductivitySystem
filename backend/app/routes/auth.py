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


# -------------------------------------------------------------
# 1. CORE FUNCTION: Retrieves User OBJECT (and its role) from DB
# -------------------------------------------------------------
def get_current_user_from_db_mock():
    # This simulates token lookup: it reads the Mock-User-ID header
    mock_header = request.headers.get('Authorization')
    if mock_header and mock_header.startswith('Mock-User-ID'):
        try:
            # Extract the ID
            user_id = int(mock_header.split(' ')[1])
            
            # DATABASE RETRIEVAL: Fetch User object using the ID
            user = db.session.get(User, user_id) 
            
            if user:
                # The user object contains the .role property retrieved from the DB
                return user
        except:
            pass
            
    return None

# -------------------------------------------------------------
# 2. DECORATOR: Required for Viewing (All Logged-in Roles)
# -------------------------------------------------------------
def login_required_mock(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user_from_db_mock() 

        if user is None:
            # 401: No user identified (header missing or ID invalid)
            return jsonify({'error': '401 Unauthorized: Please log in.'}), 401
        
        # Access Granted: Pass the user's ID to the view function
        return f(current_user_id=user.id, *args, **kwargs)
            
    return decorated_function

# -------------------------------------------------------------
# 3. DECORATOR: Required for Creation (Manager/Director Role Check)
# -------------------------------------------------------------
def manager_or_director_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user_from_db_mock() 

        if user is None:
            return jsonify({'error': '401 Unauthorized: Please log in.'}), 401
        
        # ROLE CHECK FROM DB: Uses the 'role' property retrieved from the database
        if user.role in ['Manager', 'Director']:
            # Access Granted: Pass the user's ID
            return f(current_manager_id=user.id, *args, **kwargs)
        
        else:
            # 403: User's role (e.g., 'Staff') is not authorized for creation
            return jsonify({'error': f'403 Forbidden: Role "{user.role}" not authorized to create projects.'}), 403
            
    return decorated_function


