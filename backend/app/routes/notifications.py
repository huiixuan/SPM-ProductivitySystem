from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Notification
from app.services import notification_service

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("", methods=["GET"])
@jwt_required()
def get_user_notifications():
    """Return all notifications for the logged-in user (newest first)."""
    user_id = int(get_jwt_identity())
    notifs = notification_service.get_notifications_for_user(user_id)
    return jsonify([
        {
            "id": n.id,
            "task_id": n.task_id,
            "payload": n.payload,
            "trigger_days_before": n.trigger_days_before,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
            "message": n.message,
        }
        for n in notifs
    ]), 200


@notifications_bp.route("/<int:notif_id>/read", methods=["PATCH"])
@jwt_required()
def mark_as_read(notif_id):
    """Mark one notification as read."""
    notif = notification_service.mark_notification_as_read(notif_id)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"success": True}), 200
