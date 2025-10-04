from flask import Blueprint, jsonify, request
from app.services import task_services
from app.models import TaskStatus
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import traceback

task_bp = Blueprint("task", __name__)

@task_bp.route("/create-task", methods=["POST"])
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
            notes=notes
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
def get_task_route(task_id):
    try:
        task = task_services.get_task(task_id)
        if not task:
            return jsonify({"error": "Task not found."}), 404
        
        return jsonify(task.to_dict()), 200
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
