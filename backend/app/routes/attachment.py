from flask import Blueprint, jsonify, send_file
from app.services import attachment_services
import io

attachment_bp = Blueprint("attachment", __name__)

@attachment_bp.route("/get-attachment/<int:attachment_id>", methods=["GET"])
def get_attachment_route(attachment_id):
  try:
    attachment = attachment_services.get_attachment(attachment_id)
    if not attachment:
      return jsonify({"error": "Attachment not found."}), 404
    
    return send_file(
      io.BytesIO(attachment.content),
      download_name=attachment.filename,
      as_attachment=False,
      mimetype="application/pdf"
    )
  
  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500

@attachment_bp.route("/get-task-attachments/<int:task_id>", methods=["GET"])
def get_attachment_by_task(task_id):
  try:
    attachments = attachment_services.get_attachment_by_task(task_id)
    
    return 
  
  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500