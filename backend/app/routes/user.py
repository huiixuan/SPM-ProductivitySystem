from flask import Blueprint, jsonify
from app.services.user_services import *

user_bp = Blueprint("user", __name__)

@user_bp.route("/get-all-emails", methods=["GET"])
def get_all_emails_route():
    emails = get_all_emails()
    return jsonify(emails)