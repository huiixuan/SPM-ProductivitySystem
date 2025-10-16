from flask import Blueprint, jsonify, request, session
from app.services import task_services
from app.models import TaskStatus
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import traceback
from flask_jwt_extended import jwt_required, get_jwt_identity

task_bp = Blueprint("task", __name__)

@task_bp.route("/create-task", methods=["POST"])
@jwt_required()
def create_task_route():
    data = request.form
    files = request.files.getlist("attachments")
    print("data:", data)
    print("form keys:", request.form.keys())
    print("files:", request.files)


    try:
        title = data.get("title")
        description = data.get("description")
        duedate_str = data.get("duedate")
        status = data.get("status")
        owner_email = data.get("owner")
        collaborators = data.getlist("collaborators")
        notes = data.get("notes")
        priority = data.get("priority")

        status_enum = TaskStatus(status)
        duedate = datetime.fromisoformat(duedate_str).date() if duedate_str else None

        task = task_services.create_task(
            title=title,
            description=description,
            duedate=duedate,
            status=status_enum,
            owner_email=owner_email,
            collaborator_emails=collaborators,
            attachments=files,
            notes=notes,
            priority=priority,
        )

        return jsonify({
            "success": True,
            "task_id": task.id,
            "title": task.title
        }), 201
    
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    
    except SQLAlchemyError as se:
        return jsonify({"success": False, "error": str(se)}), 500
    
    except Exception as e:
        print("--- AN ERROR OCCURRED ---")
        traceback.print_exc() # This will print the full error traceback
        print("--------------------------")
        return jsonify({"error": "An internal error occurred"}), 500

@task_bp.route("/get-task/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task_route(task_id):
    try:
        task = task_services.get_task(task_id)
        if not task:
            return jsonify({"error": "Task not found."}), 404
        
        return jsonify(task.to_dict()), 200
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@task_bp.route("/get-user-tasks", methods=["GET"])
@jwt_required()
def get_user_tasks_route():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Not logged in"}), 401
        
        tasks = task_services.get_user_tasks(user_id) or []
        data = [task.to_dict() for task in tasks]
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@task_bp.route("/get-project-tasks/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project_tasks_route(project_id):
    try:
        tasks = task_services.get_project_tasks(project_id) or []
        data = [task.to_dict() for task in tasks]
        return jsonify(data), 200
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@task_bp.route("/update-task/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task_route(task_id):
    try:
        print("Update route called for task:", task_id)
        print("Form data received:", request.form)
        print("Files received:", request.files)

        data = dict(request.form)
        new_files = request.files.getlist("attachments")

        print("Calling update_task service...")
        task = task_services.update_task(task_id, data, new_files)
        
        print("Update successful")
        return jsonify({"success": True, "task": task.to_dict()}), 200
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500