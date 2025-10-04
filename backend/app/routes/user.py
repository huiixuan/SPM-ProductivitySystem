from flask import Blueprint, jsonify
from app.services.user_services import *

user_bp = Blueprint("user", __name__)

@user_bp.route("/get-all-emails", methods=["GET"])
def get_all_emails_route():
    try:
        emails = get_all_emails() or []
        return jsonify(emails)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500