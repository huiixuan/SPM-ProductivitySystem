import json
from app.models import db, Project, Attachment, User, ProjectStatus, Task, TaskStatus, RecurrenceType
from app.services.user_services import get_user_by_email
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func 
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.services.email_services import (
    send_project_creation_email_notification,
    send_project_update_email_notification,
    send_project_collaborator_added_email_notification
)
from app.services.notification_services import (
    send_project_assignment_notification  # ✅ ADDED: For project assignment notifications
)

def create_project(name, description, deadline, status, owner_email, collaborator_emails, attachments, notes, created_by):
    try:
        owner = get_user_by_email(owner_email)
        if not owner:
            raise ValueError(f"Owner with email {owner_email} not found")
        
        collaborators = []
        if collaborator_emails:
            if isinstance(collaborator_emails, list) and len(collaborator_emails) == 1 and collaborator_emails[0] == '[]':
                collaborator_emails = []

            for email in collaborator_emails:
                user = get_user_by_email(email)
                if user:
                    collaborators.append(user)

        project = Project(
            name=name,
            description=description,
            deadline=deadline,
            status=status,
            owner=owner,
            collaborators=collaborators,
            notes=notes
        )

        attachment_filenames = []
        if attachments:
            for file in attachments:
                attachment = Attachment(filename=file.filename, content=file.read(), project=project)
                db.session.add(attachment)
                attachment_filenames.append(file.filename)

        db.session.add(project)
        db.session.commit()
        
        # Send attachment notifications for initial attachments
        if attachment_filenames and created_by:
            for filename in attachment_filenames:
                from app.services.notification_services import send_project_attachment_notification
                send_project_attachment_notification(project, created_by, filename)
        
        # Notify owner if they're not the creator
        if created_by.id != owner.id:
            from app.services.notification_services import send_project_assignment_notification
            send_project_assignment_notification(project, created_by, owner, "owner")
        
        # Notify collaborators
        for collaborator in collaborators:
            if collaborator.id != created_by.id:
                from app.services.notification_services import send_project_assignment_notification
                send_project_assignment_notification(project, created_by, collaborator, "collaborator")

        # Send project creation notifications
        from app.services.notification_services import send_project_creation_notification
        send_project_creation_notification(project, created_by)
        
        return project
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while creating project: {e}")
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while creating project: {e}")

def get_all_projects(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return []
        projects = Project.query.filter(
            (Project.owner_id == user.id) | (Project.collaborators.contains(user))
        ).distinct().all()
        return projects
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching projects: {e}")

def get_project_by_id(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")
        return project
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project {project_id}: {e}")

def get_project_users(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")
        users = [project.owner] + project.collaborators
        users_data = [
            {"id": user.id, "role": user.role.value, "name": user.name, "email": user.email}
            for user in users
        ]
        return users_data
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project {project_id}: {e}")

def update_project(project_id, data, new_files, collaborator_emails=None, updated_by=None):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        old_values = {
            'name': project.name,
            'description': project.description,
            'notes': project.notes,
            'status': project.status,
            'deadline': project.deadline,
            'owner_id': project.owner_id,
            'collaborators': [user.email for user in project.collaborators]
        }
        
        updated_fields = []
        old_collaborator_emails = {user.email for user in project.collaborators}
        
        if "name" in data: 
            project.name = data["name"]
        if "description" in data: 
            project.description = data["description"]
        if "notes" in data: 
            project.notes = data["notes"]
        if "status" in data: 
            project.status = ProjectStatus(data["status"])
        if "deadline" in data and data["deadline"]:
            project.deadline = datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")).date()
        if "owner" in data:
            owner = User.query.filter_by(email=data["owner"]).first()
            if owner: 
                project.owner = owner

        new_collaborators = []
        if collaborator_emails is not None:
            project.collaborators.clear()
            for email in collaborator_emails:
                user = User.query.filter_by(email=email).first()
                if user:
                    project.collaborators.append(user)
                    if email not in old_collaborator_emails:
                        new_collaborators.append(user)

        removed_attachments = []

        if "existing_attachments" in data:
            existing_attachments = json.loads(data["existing_attachments"])
            existing_ids = [att.get("id") for att in existing_attachments]
            
            for att in project.attachments[:]:
                if att.id not in existing_ids:
                    removed_attachments.append(att.filename)
                    db.session.delete(att)
                    print(f"DEBUG: Marked project attachment for deletion: {att.filename}")

                    updated_fields.append({
                        'field': 'attachment',
                        'old_value': att.filename,
                        'new_value': 'Removed'
                    })

        new_project_attachments = []

        if new_files:
            for file in new_files:
                if file.filename:
                    attachment = Attachment(filename=file.filename, content=file.read(), project=project)
                    db.session.add(attachment)
                    print(f"DEBUG: Added new attachment: {file.filename}")
            
                    if updated_by:
                        from app.services.notification_services import send_project_attachment_notification
                        send_project_attachment_notification(project, updated_by, file.filename)
                    
                    updated_fields.append({
                        'field': 'attachment',
                        'old_value': 'None',
                        'new_value': file.filename
                    })


        db.session.commit()
        
        updated_fields = []
        
        if old_values['name'] != project.name:
            updated_fields.append({
                'field': 'name',
                'old_value': old_values['name'],
                'new_value': project.name
            })
            
        if old_values['description'] != project.description:
            updated_fields.append({
                'field': 'description',
                'old_value': old_values['description'],
                'new_value': project.description
            })
            
        if old_values['notes'] != project.notes:
            updated_fields.append({
                'field': 'notes',
                'old_value': old_values['notes'],
                'new_value': project.notes
            })
            
        if old_values['status'] != project.status:
            updated_fields.append({
                'field': 'status',
                'old_value': old_values['status'].value,
                'new_value': project.status.value
            })
            
        if old_values['deadline'] != project.deadline:
            old_deadline = old_values['deadline'].strftime('%Y-%m-%d') if old_values['deadline'] else 'Not set'
            new_deadline = project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set'
            updated_fields.append({
                'field': 'deadline',
                'old_value': old_deadline,
                'new_value': new_deadline
            })
            
        if old_values['owner_id'] != project.owner_id:
            old_owner = User.query.get(old_values['owner_id'])
            updated_fields.append({
                'field': 'owner',
                'old_value': old_owner.email if old_owner else 'Unknown',
                'new_value': project.owner.email
            })
            
        current_collaborator_emails = {user.email for user in project.collaborators}
        if set(old_values['collaborators']) != current_collaborator_emails:
            old_collabs = ', '.join(old_values['collaborators']) if old_values['collaborators'] else 'None'
            new_collabs = ', '.join(current_collaborator_emails) if current_collaborator_emails else 'None'
            updated_fields.append({
                'field': 'collaborators',
                'old_value': old_collabs,
                'new_value': new_collabs
            })
        
        for filename in removed_attachments:
            updated_fields.append({
                'field': 'attachment',
                'old_value': filename,
                'new_value': 'Removed'
            })

        for file in new_files:
            if file.filename:
                updated_fields.append({
                    'field': 'attachment',
                    'old_value': 'None',
                    'new_value': file.filename
                })
        
        if new_collaborators and updated_by:
            for collaborator in new_collaborators:
                if collaborator.id != updated_by.id:
                    send_project_assignment_notification(project, updated_by, collaborator, "collaborator")

        # Send project update notifications
        if updated_by and updated_fields:
            print(f"DEBUG: Sending project update notifications for {len(updated_fields)} changes")
            from app.services.notification_services import create_project_update_notification
            create_project_update_notification(project, updated_by, updated_fields)
            send_project_update_email_notification(project, updated_by, updated_fields)
        
        return project
    
    except Exception as e:
        print(f"ERROR in update_project: {e}")
        db.session.rollback()
        raise e

def get_recurring_task_instances(task, start_date, end_date):
    if not task.isRecurring or task.recurrence_type == RecurrenceType.NONE:
        return []
    
    instances = []
    current_date = task.duedate
    
    if not current_date:
        return []

    while current_date < start_date:
        if task.recurrence_type == RecurrenceType.DAILY:
            current_date += timedelta(days=1)
        elif task.recurrence_type == RecurrenceType.WEEKLY:
            current_date += timedelta(weeks=1)
        elif task.recurrence_type == RecurrenceType.MONTHLY:
            current_date += relativedelta(months=1)
        elif task.recurrence_type == RecurrenceType.CUSTOM and task.recurrence_interval:
            current_date += timedelta(days=task.recurrence_interval)
        else:
            break
    
    max_instances = 50
    while current_date <= end_date and len(instances) < max_instances:
        instances.append({
            "title": f"{task.title} (Projected)",
            "duedate": current_date.isoformat(),
            "status": "Projected", 
        })
        
        if task.recurrence_type == RecurrenceType.DAILY:
            current_date += timedelta(days=1)
        elif task.recurrence_type == RecurrenceType.WEEKLY:
            current_date += timedelta(weeks=1)
        elif task.recurrence_type == RecurrenceType.MONTHLY:
            current_date += relativedelta(months=1)
        elif task.recurrence_type == RecurrenceType.CUSTOM and task.recurrence_interval:
            current_date += timedelta(days=task.recurrence_interval)
        else:
            break
    
    return instances

def get_project_report_data(project_id, user_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        user = User.query.get(user_id)
        if not user:
            raise PermissionError("User not found.")
        
        if user.id != project.owner_id and user not in project.collaborators:
            raise PermissionError("You do not have access to generate reports for this project.")
        
        status_counts_query = db.session.query(
            Task.status, 
            func.count(Task.id)
        ).filter(
            Task.project_id == project_id
        ).group_by(
            Task.status
        ).all()

        task_counts = {status.value: 0 for status in TaskStatus}
        for status_enum, count in status_counts_query:
            task_counts[status_enum.value] = count
        
        project_tasks = Task.query.filter_by(project_id=project_id).all()
        
        task_schedule = []
        
        start_date = datetime.utcnow().date()
        end_date = start_date + timedelta(days=90)

        projected_task_count = 0

        for task in project_tasks:
            if task.status != TaskStatus.COMPLETED:
                task_schedule.append({
                    "title": task.title,
                    "duedate": task.duedate.isoformat() if task.duedate else None,
                    "status": task.status.value,
                })

            if task.isRecurring:
                projected_tasks = get_recurring_task_instances(task, start_date, end_date)
                task_schedule.extend(projected_tasks)
                projected_task_count += len(projected_tasks)

        task_counts["Projected"] = projected_task_count

        return {
            "task_counts": task_counts,
            "task_schedule": task_schedule
        }

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while generating report data: {e}")