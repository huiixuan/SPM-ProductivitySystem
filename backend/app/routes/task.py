from flask import Blueprint, jsonify

task_bp = Blueprint("task", __name__)

@task_bp.route("/save-task", methods=["GET"])
def save_task_route():
    return jsonify(message="Hello from Flask backend!")
