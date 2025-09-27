# backend/app/routes/project.py 

from flask import Blueprint, request, jsonify
from app.services.project_service import create_project_and_handle_upload, get_all_projects
from .auth import manager_or_director_required, login_required_mock # <-- Import BOTH decorators
from flask_jwt_extended import jwt_required

project_bp = Blueprint('project', __name__, url_prefix='/api')
@jwt_required() 

# -----------------------------------------------------------------
# POST: Create a Project (Manager/Director Only)
# -----------------------------------------------------------------
@project_bp.route('/projects', methods=['POST'])
@manager_or_director_required # Stricter check for creation
def create_project(current_manager_id): 
    # ... (function body remains the same, uses current_manager_id) ...
    try:
        project_data = request.form.to_dict()
        file = request.files.get('attachment')
        
        new_project = create_project_and_handle_upload(project_data, file, current_manager_id)

        return jsonify({
            "message": "Project created successfully", 
            "id": new_project.id,
            "name": new_project.name
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -----------------------------------------------------------------
# GET: List all Projects (Staff, Manager, Director)
# -----------------------------------------------------------------
@project_bp.route('/projects', methods=['GET'])
@login_required_mock # <-- NEW: Less restrictive check for viewing
def list_projects(current_user_id): # <-- Must accept the ID from the decorator
    try:
        # Note: current_user_id is available here if you want to filter projects later
        projects = get_all_projects()
        
        return jsonify([
            {
                "id": p.id,
                "name": p.name,
                "status": p.status,
                "deadline": p.deadline.strftime('%Y-%m-%d') if p.deadline else None,
            } for p in projects
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500