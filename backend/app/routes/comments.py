from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Comment, Task
from app.services import notification_services

comments_bp = Blueprint("comments", __name__)

@comments_bp.route("/save-comment/<int:task_id>", methods=["POST"])
@jwt_required()
def create_comment(task_id):
    data = request.get_json()
    content = data.get("content")
    if not content:
        return jsonify({"error": "Content is required"}), 400

    user_id = int(get_jwt_identity())
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    comment = Comment(
        task_id=task_id,
        user_id=user_id,
        content=content
    )
    db.session.add(comment)
    db.session.commit()

    notification_services.create_comment_notification(comment)

    return jsonify({
        "success": True,
        "comment": {
            "id": comment.id,
            "content": comment.content,
            "user_id": comment.user_id,
            "task_id": comment.task_id,
            "created_at": comment.created_at.isoformat()
        }
    }), 201

@comments_bp.route("/get-comments/<int:task_id>", methods=["GET"])
@jwt_required()
def get_comments(task_id):
    comments = Comment.query.filter_by(task_id=task_id).order_by(Comment.created_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "content": c.content,
        "user_id": c.user_id,
        "user_email": c.user.email,
        "created_at": c.created_at.isoformat()
    } for c in comments]), 200