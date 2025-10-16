
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.models import db, User, Task, Project

calendar_bp = Blueprint("calendar", __name__)

@calendar_bp.route("/personal", methods=["GET"])
@jwt_required()
def get_personal_calendar():
    """Get current user's tasks and projects for calendar"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get user's tasks
        user_tasks = Task.query.filter(
            (Task.owner_id == user_id) | (Task.collaborators.any(User.id == user_id))
        ).all()

        # Get user's projects
        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        events = []
        
        # Convert tasks to calendar events
        for task in user_tasks:
            if task.duedate:
                status = "upcoming"
                if task.duedate < datetime.now().date():
                    status = "overdue"
                elif task.status.value == "Completed":
                    status = "completed"
                elif task.status.value in ["Ongoing", "Pending Review"]:
                    status = "ongoing"
                
                events.append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "start": datetime.combine(task.duedate, datetime.min.time()).isoformat(),
                    "end": datetime.combine(task.duedate, datetime.max.time()).isoformat(),
                    "type": "task",
                    "status": status,
                    "taskId": task.id
                })

        # Convert projects to calendar events
        for project in user_projects:
            if project.deadline:
                status = "upcoming"
                if project.deadline < datetime.now().date():
                    status = "overdue"
                elif project.status.value == "Completed":
                    status = "completed"
                elif project.status.value == "In Progress":
                    status = "ongoing"
                
                events.append({
                    "id": project.id + 10000,  # Offset to avoid ID conflicts
                    "title": project.name,
                    "description": project.description,
                    "start": datetime.combine(project.deadline, datetime.min.time()).isoformat(),
                    "end": datetime.combine(project.deadline, datetime.max.time()).isoformat(),
                    "type": "project",
                    "status": status,
                    "projectId": project.id
                })

        return jsonify({"events": events}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

@calendar_bp.route("/team", methods=["GET"])
@jwt_required()
def get_team_calendar():
    """Get team tasks and projects for calendar view"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get user's projects to find team members
        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        # Collect all team member IDs from projects
        team_member_ids = set()
        for project in user_projects:
            team_member_ids.add(project.owner_id)
            for collaborator in project.collaborators:
                team_member_ids.add(collaborator.id)

        # Get tasks for all team members
        team_tasks = Task.query.filter(
            (Task.owner_id.in_(team_member_ids)) | 
            (Task.collaborators.any(User.id.in_(team_member_ids)))
        ).all()

        events = []
        
        for task in team_tasks:
            status = "upcoming"
            if task.duedate:
                if task.duedate < datetime.now().date():
                    status = "overdue"
                elif task.status.value == "Completed":
                    status = "completed"
                elif task.status.value in ["Ongoing", "Pending Review"]:
                    status = "ongoing"
            
            events.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "start": datetime.combine(task.duedate, datetime.min.time()) if task.duedate else None,
                "end": datetime.combine(task.duedate, datetime.max.time()) if task.duedate else None,
                "type": "task",
                "status": status,
                "assignee": task.owner.email,
                "taskId": task.id
            })

        return jsonify({"events": events}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

@calendar_bp.route("/team/members", methods=["GET"])
@jwt_required()
def get_team_members():
    """Get team members with workload information"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get user's projects to find team members
        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        # Collect all team members from projects
        team_members = set()
        for project in user_projects:
            team_members.add(project.owner)
            for collaborator in project.collaborators:
                team_members.add(collaborator)

        members_with_workload = []
        for member in team_members:
            # Count active tasks for this member
            task_count = Task.query.filter(
                (Task.owner_id == member.id) | (Task.collaborators.any(User.id == member.id)),
                Task.status.notin_(["Completed"])
            ).count()

            members_with_workload.append({
                "id": member.id,
                "name": member.name,
                "email": member.email,
                "role": member.role.value,
                "workload": task_count
            })

        return jsonify({"members": members_with_workload}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500