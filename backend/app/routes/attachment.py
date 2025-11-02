from flask import Blueprint, jsonify, send_file
from app.services import attachment_services
import io
import mimetypes

attachment_bp = Blueprint("attachment", __name__)

@attachment_bp.route("/get-attachment/<int:attachment_id>", methods=["GET"])
def get_attachment_route(attachment_id):
  try:
    attachment = attachment_services.get_attachment(attachment_id)
    if not attachment:
      return jsonify({"error": "Attachment not found."}), 404
    
    # Detect MIME type
    mimetype, _ = mimetypes.guess_type(attachment.filename)
    if not mimetype:
        mimetype = "application/octet-stream"
    
    return send_file(
      io.BytesIO(attachment.content),
      download_name=attachment.filename,
      as_attachment=False,
      mimetype=mimetype
    )
  
  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500

@attachment_bp.route("/get-task-attachments/<int:task_id>", methods=["GET"])
def get_attachment_by_task(task_id):
  try:
    attachments = attachment_services.get_attachment_by_task(task_id)
    
    attachments_data = [{
      "id": att.id,
      "filename": att.filename,
      "task_id": att.task_id,
      "project_id": att.project_id
    } for att in attachments]
    
    return jsonify(attachments_data), 200
  
  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500