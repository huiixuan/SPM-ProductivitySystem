from flask import Blueprint, jsonify
from app.services.user_services import *

user_bp = Blueprint("user", __name__)

@user_bp.route("/get-all-users", methods=["GET"])
def get_all_users_route():
    try:
        user_data = get_users_info() or []
        return jsonify(user_data)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500