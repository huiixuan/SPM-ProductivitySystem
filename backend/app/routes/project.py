import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

# ✅ Import UserRole if your User model uses it for the 'role' attribute
from ..models import db, User, Project, ProjectStatus, UserRole

project_bp = Blueprint("project", __name__)

ALLOWED_ROLES = {"manager", "director"}
ALLOWED_MIMETYPES = {"application/pdf"}

# --- CORS is now handled globally in __init__.py, so all local CORS code has been removed ---


def role_required(allowed_roles):
    """Decorator to ensure user has one of the allowed roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # ✅ CORRECT: Get user ID (string) from token and convert to integer
                user_id_str = get_jwt_identity()
                user_id = int(user_id_str)
                user = db.session.get(User, user_id)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid token identity"}), 401

            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if the user's role (e.g., "manager") is in the allowed set
            if user.role.value.lower() not in allowed_roles:
                return jsonify({"error": "Forbidden: Insufficient role"}), 403
            
            # Attach user to the request context for easy access in the route
            request.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _save_pdf(file_storage):
    """Helper function to validate and save a PDF file."""
    if not file_storage:
        return None
    if file_storage.mimetype not in ALLOWED_MIMETYPES:
        raise ValueError("Only PDF files are allowed.")
    
    fname = secure_filename(file_storage.filename or "attachment.pdf")
    if not fname.lower().endswith(".pdf"):
        fname += ".pdf"
        
    new_name = f"{uuid.uuid4().hex}_{fname}"
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    path = os.path.join(upload_folder, new_name)
    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(path)
    return path


# --- Create project ---
@project_bp.route("", methods=["POST"])
@jwt_required()
@role_required(ALLOWED_ROLES)
def create_project():
    # 'request.current_user' is now available thanks to the decorator
    owner = request.current_user

    # ... (rest of the function remains the same)
    name = (request.form.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Project name is required"}), 400

    description = request.form.get("description", "")
    status_raw = request.form.get("status", "Not Started").strip()
    deadline_raw = request.form.get("deadline")
    collaborators_raw = request.form.get("collaborators", "")
    attachment_file = request.files.get("attachment")

    try:
        status_enum = ProjectStatus(status_raw)
        deadline = datetime.fromisoformat(deadline_raw) if deadline_raw else None
        attachment_path = _save_pdf(attachment_file)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    project = Project(
        name=name,
        description=description,
        deadline=deadline,
        status=status_enum,
        attachment_path=attachment_path,
        owner_id=owner.id,
    )

    if collaborators_raw:
        collaborator_emails = {e.strip() for e in collaborators_raw.split(',') if e.strip()}
        users = db.session.query(User).filter(User.email.in_(collaborator_emails)).all()
        
        found_emails = {u.email for u in users}
        missing_emails = collaborator_emails - found_emails
        if missing_emails:
            return jsonify({"error": "Collaborator emails not found", "missing": list(missing_emails)}), 404
        
        project.collaborators = users

    db.session.add(project)
    db.session.commit()
    return jsonify({"message": "Project created successfully", "project": project.to_dict()}), 201


# --- List projects ---
@project_bp.route("", methods=["GET"])
@jwt_required()
def list_projects():
    try:
        
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        user = db.session.get(User, user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid token identity"}), 401

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Find projects where the user is the owner
    owned_projects = db.session.query(Project).filter(Project.owner_id == user.id)
    
    # Find projects where the user is a collaborator
    collab_projects = db.session.query(Project).join(Project.collaborators).filter(User.id == user.id)

    # Combine, remove duplicates, order, and execute the query
    all_projects = owned_projects.union(collab_projects).order_by(Project.created_at.desc()).all()
    
    return jsonify({"projects": [p.to_dict() for p in all_projects]}), 200