# routes/team.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User

team_bp = Blueprint("team", __name__)

@team_bp.route("/members", methods=["GET"])
@jwt_required()
def get_team_members():
    """Get all team members for team calendar"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        current_user = db.session.get(User, user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        # Get all users (or filter by organization if needed)
        all_users = User.query.all()
        
        team_members = []
        for user in all_users:
            team_members.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role.value
            })

        return jsonify({"members": team_members}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500