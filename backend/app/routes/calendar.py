# routes/calendar.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.models import db, User, Project, Task, ProjectStatus, TaskStatus

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

        events = []

        # Get user's projects
        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        # Get user's tasks - we need to query tasks properly
        # Since your Task model doesn't have direct user relationship, we'll get owned tasks
        user_tasks = Task.query.filter(Task.owner_id == user_id).all()

        now = datetime.now().date()
        
        # Process projects
        for project in user_projects:
            if project.deadline:
                status = "upcoming"
                if project.status == ProjectStatus.COMPLETED:
                    status = "completed"
                elif project.status == ProjectStatus.IN_PROGRESS:
                    status = "ongoing"
                elif project.deadline < now:
                    status = "overdue"
                
                events.append({
                    "id": project.id,
                    "title": project.name,
                    "description": project.description,
                    "start": project.deadline.isoformat(),
                    "end": project.deadline.isoformat(),
                    "type": "project",
                    "status": status,
                    "deadline": project.deadline.isoformat(),
                })

        # Process tasks
        for task in user_tasks:
            if task.duedate:
                status = "upcoming"
                if task.status == TaskStatus.COMPLETED:
                    status = "completed"
                elif task.status in [TaskStatus.ONGOING, TaskStatus.PENDING_REVIEW]:
                    status = "ongoing"
                elif task.duedate < now:
                    status = "overdue"
                
                events.append({
                    "id": task.id + 10000,  # Offset to avoid ID conflicts
                    "title": task.title,
                    "description": task.description,
                    "start": task.duedate.isoformat(),
                    "end": task.duedate.isoformat(),
                    "type": "task",
                    "status": status,
                    "duedate": task.duedate.isoformat(),
                })

        return jsonify({"events": events}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

@calendar_bp.route("/team", methods=["GET"])
@jwt_required()
def get_team_calendar():
    """Get team calendar data"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        current_user = db.session.get(User, user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        # Get all projects the current user has access to
        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        # Get all tasks for team members (users in the same projects)
        team_member_ids = set()
        for project in user_projects:
            team_member_ids.add(project.owner_id)
            for collaborator in project.collaborators:
                team_member_ids.add(collaborator.id)

        # Get tasks for all team members
        team_tasks = Task.query.filter(Task.owner_id.in_(team_member_ids)).all()

        events = []
        now = datetime.now().date()

        # Process projects
        for project in user_projects:
            if project.deadline:
                status = "upcoming"
                if project.status == ProjectStatus.COMPLETED:
                    status = "completed"
                elif project.status == ProjectStatus.IN_PROGRESS:
                    status = "ongoing"
                elif project.deadline < now:
                    status = "overdue"
                
                # Get project owner email
                owner = db.session.get(User, project.owner_id)
                owner_email = owner.email if owner else "Unknown"
                
                events.append({
                    "id": project.id,
                    "title": project.name,
                    "description": project.description,
                    "start": project.deadline.isoformat(),
                    "end": project.deadline.isoformat(),
                    "type": "project",
                    "status": status,
                    "assignee": owner.name if owner else "Unknown",
                    "assigneeEmail": owner_email,
                })

        # Process tasks for team members
        for task in team_tasks:
            if task.duedate:
                status = "upcoming"
                if task.status == TaskStatus.COMPLETED:
                    status = "completed"
                elif task.status in [TaskStatus.ONGOING, TaskStatus.PENDING_REVIEW]:
                    status = "ongoing"
                elif task.duedate < now:
                    status = "overdue"
                
                # Get task owner
                owner = db.session.get(User, task.owner_id)
                owner_email = owner.email if owner else "Unknown"
                
                events.append({
                    "id": task.id + 20000,  # Different offset for tasks
                    "title": task.title,
                    "description": task.description,
                    "start": task.duedate.isoformat(),
                    "end": task.duedate.isoformat(),
                    "type": "task",
                    "status": status,
                    "assignee": owner.name if owner else "Unknown",
                    "assigneeEmail": owner_email,
                })

        return jsonify({"events": events}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

@calendar_bp.route("/workload", methods=["GET"])
@jwt_required()
def get_workload_data():
    """Get workload data for all users"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        current_user = db.session.get(User, user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        # Get all users
        all_users = User.query.all()
        
        workload_data = []
        now = datetime.now().date()
        
        for user in all_users:
            # Count active tasks (not completed) where user is owner
            active_tasks_count = Task.query.filter(
                Task.owner_id == user.id,
                Task.status != 'Completed'
            ).count()
            
            # Count active projects (not completed) where user is owner or collaborator
            active_projects_count = Project.query.filter(
                (Project.owner_id == user.id) | (Project.collaborators.any(User.id == user.id)),
                Project.status != 'Completed'
            ).count()
            
            # DEBUG: Let's see what's being counted
            print(f"User {user.email}: {active_tasks_count} tasks, {active_projects_count} projects")
            
            # For workload, we might want to count tasks + projects, or just tasks
            # Let's use just tasks for now to match your expectation
            total_workload = active_tasks_count
            
            workload_data.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
                "workload": total_workload,  # Only tasks for workload
                "task_count": active_tasks_count,
                "project_count": active_projects_count
            })
        
        return jsonify({"team_members": workload_data}), 200
        
    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500