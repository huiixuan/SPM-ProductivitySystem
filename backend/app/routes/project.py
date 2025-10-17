from flask import Blueprint, jsonify, request
from app.services import project_services
from app.models import ProjectStatus, User # Make sure User is imported
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt_identity
import traceback # Helpful for debugging

project_bp = Blueprint("project", __name__)

@project_bp.route("/create-project", methods=["POST"])
@jwt_required()
def create_project_route():
    data = request.form
    files = request.files.getlist("attachments")
    
    try:
        name = data.get("name")
        description = data.get("description")
        deadline_str = data.get("deadline")
        status = data.get("status")
        owner_email = data.get("owner")
        collaborator_emails = data.getlist("collaborators")
        notes = data.get("notes")

        status_enum = ProjectStatus(status) if status else ProjectStatus.NOT_STARTED
        deadline = datetime.fromisoformat(deadline_str).date() if deadline_str else None

        project = project_services.create_project(
            name=name,
            description=description,
            deadline=deadline,
            status=status_enum,
            owner_email=owner_email,
            collaborator_emails=collaborator_emails,
            attachments=files,
            notes=notes
        )

        return jsonify({
            "success": True,
            "project_id": project.id,
            "message": "Project created successfully."
        }), 201

    except Exception as e:
        print(f"Error in create_project_route: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# --- THIS IS THE CORRECTED FUNCTION ---
@project_bp.route("/get-all-projects", methods=["GET"])
@jwt_required()
def get_all_projects_route():
    try:
        # 1. Get the ID of the currently logged-in user from the JWT token.
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not found or not logged in"}), 401

        # 2. Pass the user's ID to the service function to get only their projects.
        projects = project_services.get_all_projects(user_id) or []
        
        data = [p.to_dict() for p in projects]
        return jsonify(data), 200
    except Exception as e:
        print(f"Error in get_all_projects_route: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/get-project/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project_route(project_id):
    try:
        project = project_services.get_project_by_id(project_id)
        return jsonify(project.to_dict()), 200
    except Exception as e:
        print(f"Error in get_project_route for ID {project_id}: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/update-project/<int:project_id>", methods=["PUT"])
@jwt_required()
def update_project_route(project_id):
    try:
        data = request.form
        new_files = request.files.getlist("attachments")
        collaborator_emails = data.getlist("collaborators")
        project = project_services.update_project(project_id, dict(data), new_files, collaborator_emails)

        return jsonify({
            "success": True, 
            "project": project.to_dict(),
            "message": "Project updated successfully."
        }), 200
    except Exception as e:
        print(f"Error in update_project_route for ID {project_id}: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500