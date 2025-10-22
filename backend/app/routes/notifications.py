from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Notification
from app.services.notification_services import get_notifications_for_user, mark_notification_as_read, mark_all_notifications_as_read

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("", methods=["GET"])
@jwt_required()
def get_user_notifications():
    """Return all notifications for the logged-in user (newest first)."""
    user_id = int(get_jwt_identity())
    notifs = get_notifications_for_user(user_id)
    return jsonify([
        {
            "id": n.id,
            "task_id": n.task_id,
            "type": n.type.value if hasattr(n, 'type') else 'due_date_reminder',
            "payload": n.payload,
            "trigger_days_before": n.trigger_days_before,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
            "message": n.message,
            "comment_id": n.comment_id if hasattr(n, 'comment_id') else None,
        }
        for n in notifs
    ]), 200

@notifications_bp.route("/<int:notif_id>/read", methods=["PATCH"])
@jwt_required()
def mark_as_read(notif_id):
    """Mark one notification as read."""
    notif = mark_notification_as_read(notif_id)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"success": True}), 200

@notifications_bp.route("/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read for current user."""
    user_id = int(get_jwt_identity())
    mark_all_notifications_as_read(user_id)
    return jsonify({"success": True}), 200

@notifications_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def get_unread_count():
    """Get unread notification count for current user."""
    user_id = int(get_jwt_identity())
    count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({"unread_count": count}), 200