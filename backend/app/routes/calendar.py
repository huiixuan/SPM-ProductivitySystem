from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
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

        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        user_tasks = Task.query.filter(
            (Task.owner_id == user_id) | (Task.collaborators.any(User.id == user_id))
        ).all()

        now = date.today()
        
        # Process projects
        for project in user_projects:
            if project.deadline:
                if project.deadline < now and project.status != ProjectStatus.COMPLETED:
                    status = "overdue"
                elif project.status == ProjectStatus.COMPLETED:
                    status = "completed"
                elif project.status == ProjectStatus.IN_PROGRESS:
                    status = "ongoing"
                else:
                    status = "upcoming"
                
                events.append({
                    "id": f"project-{project.id}",
                    "title": project.name,
                    "description": project.description,
                    "start": project.deadline.isoformat(),
                    "end": project.deadline.isoformat(),
                    "type": "project",
                    "status": status,
                    "deadline": project.deadline.isoformat(),
                })

        for task in user_tasks:
            if task.duedate:
                if task.duedate < now and task.status != TaskStatus.COMPLETED:
                    status = "overdue"
                elif task.status == TaskStatus.COMPLETED:
                    status = "completed"
                elif task.status in [TaskStatus.ONGOING, TaskStatus.PENDING_REVIEW]:
                    status = "ongoing"
                else:
                    status = "upcoming"
                
                events.append({
                    "id": f"task-{task.id}",
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
    """Get team calendar data - ENHANCED for better filtering"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        current_user = db.session.get(User, user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        team_member_ids = set()
        
        for project in user_projects:
            team_member_ids.add(project.owner_id)
            for collaborator in project.collaborators:
                team_member_ids.add(collaborator.id)
        
        user_tasks = Task.query.filter(
            (Task.owner_id == user_id) | (Task.collaborators.any(User.id == user_id))
        ).all()
        
        for task in user_tasks:
            team_member_ids.add(task.owner_id)
            for collaborator in task.collaborators:
                team_member_ids.add(collaborator.id)

        # Get all team members for reference
        all_team_members = User.query.filter(User.id.in_(list(team_member_ids))).all()
        team_member_emails = {member.id: member.email for member in all_team_members}

        team_tasks = Task.query.filter(
            (Task.owner_id.in_(list(team_member_ids))) | 
            (Task.collaborators.any(User.id.in_(list(team_member_ids))))
        ).all()

        team_projects = Project.query.filter(
            (Project.owner_id.in_(list(team_member_ids))) | 
            (Project.collaborators.any(User.id.in_(list(team_member_ids))))
        ).all()

        events = []
        now = date.today()

        for project in team_projects:
            if project.deadline:
                if project.deadline < now and project.status != ProjectStatus.COMPLETED:
                    status = "overdue"
                elif project.status == ProjectStatus.COMPLETED:
                    status = "completed"
                elif project.status == ProjectStatus.IN_PROGRESS:
                    status = "ongoing"
                else:
                    status = "upcoming"
                
                owner = db.session.get(User, project.owner_id)
                owner_email = owner.email if owner else "Unknown"
                

                project_collaborator_emails = [collab.email for collab in project.collaborators]
                
                events.append({
                    "id": f"project-{project.id}",
                    "title": project.name,
                    "description": project.description,
                    "start": project.deadline.isoformat(),
                    "end": project.deadline.isoformat(),
                    "type": "project",
                    "status": status,
                    "assignee": owner.name if owner else "Unknown",
                    "assigneeEmail": owner_email,
                    "collaborators": project_collaborator_emails
                })

        for task in team_tasks:
            if task.duedate:
                if task.duedate < now and task.status != TaskStatus.COMPLETED:
                    status = "overdue"
                elif task.status == TaskStatus.COMPLETED:
                    status = "completed"
                elif task.status in [TaskStatus.ONGOING, TaskStatus.PENDING_REVIEW]:
                    status = "ongoing"
                else:
                    status = "upcoming"
                
                owner = db.session.get(User, task.owner_id)
                owner_email = owner.email if owner else "Unknown"
                
                collaborator_emails = [collab.email for collab in task.collaborators]
                
                events.append({
                    "id": f"task-{task.id}",
                    "title": task.title,
                    "description": task.description,
                    "start": task.duedate.isoformat(),
                    "end": task.duedate.isoformat(),
                    "type": "task",
                    "status": status,
                    "assignee": owner.name if owner else "Unknown",
                    "assigneeEmail": owner_email,
                    "collaborators": collaborator_emails  
                })

        return jsonify({"events": events}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

@calendar_bp.route("/workload", methods=["GET"])
@jwt_required()
def get_workload_data():
    """Get workload data for all users - FIXED to only count active calendar items"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        current_user = db.session.get(User, user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        all_users = User.query.all()
        
        workload_data = []
        now = date.today()
        
        for user in all_users:
            calendar_tasks_count = Task.query.filter(
                ((Task.owner_id == user.id) | (Task.collaborators.any(User.id == user.id))),
                Task.duedate.isnot(None),  # Only tasks with due dates
                Task.status != TaskStatus.COMPLETED  # Only active tasks
            ).count()
            
  
            overdue_tasks_count = Task.query.filter(
                ((Task.owner_id == user.id) | (Task.collaborators.any(User.id == user.id))),
                Task.duedate.isnot(None),
                Task.status != TaskStatus.COMPLETED,
                Task.duedate < now
            ).count()
            
            calendar_projects_count = Project.query.filter(
                (Project.owner_id == user.id) | (Project.collaborators.any(User.id == user.id)),
                Project.deadline.isnot(None),  
                Project.status != ProjectStatus.COMPLETED  
            ).count()
            
            total_workload = calendar_tasks_count + calendar_projects_count
            
            workload_data.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
                "workload": total_workload,  
                "task_count": calendar_tasks_count,
                "project_count": calendar_projects_count,
                "overdue_count": overdue_tasks_count
            })
        
        return jsonify({"team_members": workload_data}), 200
        
    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

@calendar_bp.route("/debug-team", methods=["GET"])
@jwt_required()
def debug_team_data():
    """Debug endpoint to check team data"""
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        
        user_projects = Project.query.filter(
            (Project.owner_id == user_id) | (Project.collaborators.any(User.id == user_id))
        ).all()

        team_member_ids = set()
        
        for project in user_projects:
            team_member_ids.add(project.owner_id)
            for collaborator in project.collaborators:
                team_member_ids.add(collaborator.id)
        
        user_tasks = Task.query.filter(
            (Task.owner_id == user_id) | (Task.collaborators.any(User.id == user_id))
        ).all()
        
        for task in user_tasks:
            team_member_ids.add(task.owner_id)
            for collaborator in task.collaborators:
                team_member_ids.add(collaborator.id)

        all_team_members = User.query.filter(User.id.in_(list(team_member_ids))).all()
        
        debug_info = {
            "user_id": user_id,
            "team_member_ids": list(team_member_ids),
            "team_members": [
                {
                    "id": member.id,
                    "name": member.name,
                    "email": member.email
                } for member in all_team_members
            ],
            "user_projects_count": len(user_projects),
            "user_tasks_count": len(user_tasks)
        }

        return jsonify(debug_info), 200

    except Exception as e:
        return jsonify({"error": f"Debug error: {e}"}), 500