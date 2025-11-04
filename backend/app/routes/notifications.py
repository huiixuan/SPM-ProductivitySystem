from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Notification
from app.services.notification_services import get_notifications_for_user, mark_notification_as_read, mark_all_notifications_as_read

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("", methods=["GET"])
@jwt_required()
def get_user_notifications():
    """Return all notifications for the logged-in user (newest first)."""
    try:
        user_id = int(get_jwt_identity())
        print(f"DEBUG: Getting notifications for user {user_id}")
        
        notifs = get_notifications_for_user(user_id)
        
        print(f"DEBUG: Processing {len(notifs)} notifications for response")
        
        response_data = []
        for n in notifs:
            notification_data = {
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
            response_data.append(notification_data)
            print(f"DEBUG: Notification {n.id}: {n.message}")

        return jsonify(response_data), 200

    except Exception as e:
        print(f"ERROR in get_user_notifications: {e}")
        return jsonify({"error": f"Failed to get notifications: {str(e)}"}), 500

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

@notifications_bp.route("/debug", methods=["GET"])
@jwt_required()
def debug_notifications():
    """Debug endpoint to check notification status"""
    try:
        user_id = int(get_jwt_identity())
        
        # Check all notifications for this user
        all_notifs = Notification.query.filter_by(user_id=user_id).all()
        
        # Check tasks for this user
        from app.models import Task, User
        user = User.query.get(user_id)
        user_tasks = Task.query.filter(
            (Task.owner_id == user_id) | (Task.collaborators.any(User.id == user_id))
        ).all()
        
        debug_info = {
            "user_id": user_id,
            "user_email": user.email if user else "Unknown",
            "total_notifications": len(all_notifs),
            "notifications": [
                {
                    "id": n.id,
                    "task_id": n.task_id,
                    "type": n.type.value,
                    "trigger_days": n.trigger_days_before,
                    "created_at": n.created_at.isoformat(),
                    "is_read": n.is_read,
                    "message": n.message
                } for n in all_notifs
            ],
            "user_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "due_date": t.duedate.isoformat() if t.duedate else None,
                    "status": t.status.value,
                    "is_recurring": t.isRecurring
                } for t in user_tasks
            ]
        }
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/check-future", methods=["POST"])
@jwt_required()
def check_future_notifications():
    """Manually check and create future notifications (for testing)"""
    try:
        from app.services.notification_services import check_and_create_future_notifications
        count = check_and_create_future_notifications()
        return jsonify({
            "success": True,
            "message": f"Created {count} future notifications",
            "notifications_created": count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/debug-task/<int:task_id>", methods=["GET"])
@jwt_required()
def debug_task_notifications(task_id):
    """Debug endpoint to check notifications for a specific task"""
    try:
        from app.models import Task
        task = Task.query.get(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        # Get all notifications for this task
        task_notifications = Notification.query.filter_by(task_id=task_id).all()
        
        debug_info = {
            "task": {
                "id": task.id,
                "title": task.title,
                "due_date": task.duedate.isoformat() if task.duedate else None,
                "project": task.project.name if task.project else "No Project",
                "owner": task.owner.email if task.owner else None
            },
            "notifications": [
                {
                    "id": n.id,
                    "user_id": n.user_id,
                    "type": n.type.value,
                    "trigger_days_before": n.trigger_days_before,
                    "payload": n.payload,
                    "message": n.message,
                    "created_at": n.created_at.isoformat(),
                    "is_read": n.is_read
                } for n in task_notifications
            ],
            "total_notifications": len(task_notifications)
        }
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500