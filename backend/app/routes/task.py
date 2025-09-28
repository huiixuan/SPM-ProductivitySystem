from flask import Blueprint, jsonify, request
from app.services import task_services
from app.models import TaskStatus
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

task_bp = Blueprint("task", __name__)

@task_bp.route("/save-task", methods=["POST"])
def save_task_route():
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
        # attachments = request.files.getlist("attachments") if "attachments" in request.files else []

        status_enum = TaskStatus(status)
        duedate = datetime.fromisoformat(duedate_str).date() if duedate_str else None

        task = task_services.save_task(
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
        return jsonify({"success": False, "error": str(e)}), 500

    
