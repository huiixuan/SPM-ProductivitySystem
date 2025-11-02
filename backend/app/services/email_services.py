import os
import requests
import json
from datetime import datetime
from flask import current_app
from app.models import db, User, Task

class EmailService:
    def __init__(self):
        self.power_automate_webhook_url = os.getenv('POWER_AUTOMATE_WEBHOOK_URL')
        self.enabled = bool(self.power_automate_webhook_url)
        self.last_sent = {}
        self.cooldown = 300  # 5 minutes between emails for same task
    
    def can_send_email(self, task_id, recipient):
        key = f"{task_id}_{recipient}"
        now = datetime.now().timestamp()
        if key in self.last_sent and now - self.last_sent[key] < self.cooldown:
            return False
        self.last_sent[key] = now
        return True
    
    def send_notification_email(self, recipient_emails, subject, message, task_title, task_id, notification_type):
        """Send email notification via Power Automate webhook"""
        if not self.enabled or not recipient_emails:
            print(f"DEBUG: Email service disabled or no recipients. Enabled: {self.enabled}, Recipients: {recipient_emails}")
            return False
        
        # Filter recipients to avoid spamming the same person
        filtered_recipients = []
        for recipient in (recipient_emails if isinstance(recipient_emails, list) else [recipient_emails]):
            if self.can_send_email(task_id, recipient):
                filtered_recipients.append(recipient)
        
        if not filtered_recipients:
            print("DEBUG: All recipients are in cooldown period")
            return False
        
        try:
            payload = {
                "recipients": filtered_recipients,
                "subject": subject,
                "message": message,
                "task_title": task_title,
                "task_id": task_id,
                "notification_type": notification_type,
                "app_url": f"http://localhost:5173/tasks/{task_id}"
            }
            
            print(f"DEBUG: Sending email to {filtered_recipients}")
            print(f"DEBUG: Subject: {subject}")
            
            response = requests.post(
                self.power_automate_webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            success = response.status_code in [200, 202]
            print(f"DEBUG: Email sent successfully: {success}, Status: {response.status_code}")
            return success
            
        except Exception as e:
            print(f"DEBUG: Email notification failed: {e}")
            return False

# Global instance
email_service = EmailService()

def get_notification_recipients(task, excluded_user_id):
    """Get email recipients for notifications, excluding the user who triggered the event"""
    recipients = set()
    
    # Add task owner if not excluded
    if task.owner_id != excluded_user_id:
        recipients.add(task.owner.email)
    
    # Add collaborators if not excluded
    for collaborator in task.collaborators:
        if collaborator.id != excluded_user_id:
            recipients.add(collaborator.email)
    
    print(f"DEBUG: Notification recipients for task {task.id}: {list(recipients)}")
    return list(recipients)

def send_comment_email_notification(comment, task, excluded_user_id):
    """Send email for new comments"""
    recipients = get_notification_recipients(task, excluded_user_id)
    if not recipients:
        return
    
    subject = f"💬 New comment on task: {task.title}"
    
    message = f"""
    <strong>New comment by {comment.user.email}:</strong>
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #2563eb; margin: 10px 0;">
    {comment.content}
    </div>
    
    <strong>Task Details:</strong><br>
    • Task: {task.title}<br>
    • Project: {task.project.name if task.project else 'No Project'}<br>
    • Commented: {comment.created_at.strftime('%Y-%m-%d %H:%M')}
    """
    
    email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "new_comment"
    )

def send_task_update_email_notification(task, updated_by, updated_fields, excluded_user_id):
    """Send email for task updates with better field tracking"""
    recipients = get_notification_recipients(task, excluded_user_id)
    if not recipients:
        print(f"DEBUG: No recipients for task update email. Task: {task.title}, Updated by: {updated_by.email}")
        return
    
    # Format changes in a more readable way
    changes_html = ""
    for change in updated_fields:
        field_name = change['field'].title()
        old_val = change['old_value'] or 'Empty'
        new_val = change['new_value'] or 'Empty'
        
        changes_html += f"""
        <div class="field-change">
            <strong>🔧 {field_name}:</strong><br>
            <span style="color: #dc2626;">➤ From: {old_val}</span><br>
            <span style="color: #16a34a;">➤ To: {new_val}</span>
        </div>
        """
    
    subject = f"✏️ Task updated: {task.title}"
    message = f"""
    <strong>Task '{task.title}' has been updated by {updated_by.email}:</strong>
    
    {changes_html}
    
    <div class="task-info">
        <p><strong>Current Task Details:</strong></p>
        <p>• Due Date: {task.duedate.strftime('%Y-%m-%d') if task.duedate else 'Not set'}</p>
        <p>• Status: {task.status.value}</p>
        <p>• Priority: {task.priority}</p>
        <p>• Project: {task.project.name if task.project else 'No Project'}</p>
        <p>• Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <em>These changes affect your schedule and responsibilities.</em>
    """
    
    success = email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "task_updated"
    )
    
    print(f"DEBUG: Task update email sent to {len(recipients)} recipients. Success: {success}")
    print(f"DEBUG: Recipients: {recipients}")

def send_due_date_reminder_email(task, days_until_due):
    """Send due date reminder emails"""
    recipients = get_notification_recipients(task, None)
    if not recipients:
        return
    
    status = "overdue" if days_until_due < 0 else "due soon"
    days_text = f"{-days_until_due} days ago" if days_until_due < 0 else f"in {days_until_due} days"
    icon = "⚠️" if days_until_due < 0 else "📅"
    
    subject = f"{icon} Task {status}: {task.title}"
    message = f"""
    <strong>{icon} Task '{task.title}' is {status} ({days_text})</strong>
    
    <strong>Task Details:</strong><br>
    • Due Date: {task.duedate.strftime('%Y-%m-%d')}<br>
    • Project: {task.project.name if task.project else 'No Project'}<br>
    • Current Status: {task.status.value}<br>
    • Priority: {task.priority}
    
    <em>Please take appropriate action to complete this task.</em>
    """
    
    email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "due_date_reminder"
    )

def send_task_assignment_email_notification(task, assigned_by, assignee):
    """Send email when a user is assigned to a task (as owner or collaborator)"""
    
    # Don't send email if the assignee is the same as the person assigning
    if assigned_by.id == assignee.id:
        return
    
    role = "owner" if task.owner_id == assignee.id else "collaborator"
    
    subject = f"📋 New task assignment: {task.title}"
    
    message = f"""
    <strong>You have been assigned as {role} to a new task:</strong>
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #2563eb; margin: 10px 0;">
        <p><strong>Task:</strong> {task.title}</p>
        <p><strong>Description:</strong> {task.description or 'No description provided'}</p>
        <p><strong>Due Date:</strong> {task.duedate.strftime('%Y-%m-%d') if task.duedate else 'Not set'}</p>
        <p><strong>Priority:</strong> {task.priority}</p>
        <p><strong>Status:</strong> {task.status.value}</p>
        <p><strong>Assigned by:</strong> {assigned_by.email}</p>
        <p><strong>Project:</strong> {task.project.name if task.project else 'No Project'}</p>
    </div>
    
    <strong>Collaborators:</strong>
    <ul>
        <li>{task.owner.email} (Owner)</li>
        {"".join([f"<li>{collab.email}</li>" for collab in task.collaborators])}
    </ul>
    
    <em>Please review the task and update your progress accordingly.</em>
    """
    
    email_service.send_notification_email(
        [assignee.email],
        subject,
        message,
        task.title,
        task.id,
        "task_assignment"
    )

def send_task_creation_email_notification(task, created_by):
    """Send email to all involved users when a task is created"""
    recipients = get_notification_recipients(task, created_by.id)
    
    print(f"DEBUG: Task creation email - Task: {task.title}")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Recipients: {recipients}")
    print(f"DEBUG: Owner: {task.owner.email}")
    print(f"DEBUG: Collaborators: {[c.email for c in task.collaborators]}")
    
    if not recipients:
        print("DEBUG: No recipients found for email notification")
        return
    
    subject = f"🆕 New task created: {task.title}"
    
    collaborator_list = "".join([f"<li>{collab.email} (Collaborator)</li>" for collab in task.collaborators])
    
    message = f"""
    <strong>A new task has been created:</strong>
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #2563eb; margin: 10px 0;">
        <p><strong>Task:</strong> {task.title}</p>
        <p><strong>Description:</strong> {task.description or 'No description provided'}</p>
        <p><strong>Due Date:</strong> {task.duedate.strftime('%Y-%m-%d') if task.duedate else 'Not set'}</p>
        <p><strong>Priority:</strong> {task.priority}</p>
        <p><strong>Status:</strong> {task.status.value}</p>
        <p><strong>Created by:</strong> {created_by.email}</p>
        <p><strong>Project:</strong> {task.project.name if task.project else 'No Project'}</p>
    </div>
    
    <strong>Team:</strong>
    <ul>
        <li>{task.owner.email} (Owner)</li>
        {collaborator_list}
    </ul>
    
    <em>This task has been added to your schedule.</em>
    """
    
    success = email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "task_creation"
    )
    
    print(f"DEBUG: Email sent successfully: {success}")

def send_project_creation_email_notification(project, created_by):
    """Send email when a project is created"""
    recipients = get_project_notification_recipients(project, created_by.id)
    
    print(f"DEBUG: Project creation - Project: {project.name}")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Recipients: {recipients}")
    
    if not recipients:
        print("DEBUG: No recipients found for project creation email")
        return
    
    subject = f"📁 New project created: {project.name}"
    
    message = f"""
    <strong>A new project has been created:</strong>
    
    <div class="project-info">
        <p><strong>Project:</strong> {project.name}</p>
        <p><strong>Description:</strong> {project.description or 'No description provided'}</p>
        <p><strong>Deadline:</strong> {project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set'}</p>
        <p><strong>Status:</strong> {project.status.value}</p>
        <p><strong>Created by:</strong> {created_by.email}</p>
        <p><strong>Owner:</strong> {project.owner.email}</p>
    </div>
    
    <strong>Team Members:</strong>
    <ul>
        <li>{project.owner.email} (Owner)</li>
        {"".join([f"<li>{collab.email} (Collaborator)</li>" for collab in project.collaborators])}
    </ul>
    
    <em>This project has been added to your schedule.</em>
    """
    
    success = email_service.send_notification_email(
        recipients,
        subject,
        message,
        project.name,
        project.id,
        "project_creation"
    )
    
    print(f"DEBUG: Project creation email sent successfully: {success}")

def send_project_update_email_notification(project, updated_by, updated_fields):
    """Send email when a project is updated"""
    recipients = get_project_notification_recipients(project, updated_by.id)
    
    print(f"DEBUG: Project update - Project: {project.name}")
    print(f"DEBUG: Updated by: {updated_by.email}")
    print(f"DEBUG: Updated fields: {updated_fields}")
    
    if not recipients:
        print("DEBUG: No recipients found for project update email")
        return
    
    # Format changes
    changes_html = ""
    if updated_fields:
        for field, (old_value, new_value) in updated_fields.items():
            changes_html += f"""
            <div class="field-change">
            <strong>{field}:</strong><br>
            📍 From: {old_value}<br>
            📍 To: {new_value}
            </div>
            """
    
    subject = f"✏️ Project updated: {project.name}"
    
    message = f"""
    <strong>Project '{project.name}' has been updated by {updated_by.email}:</strong>
    
    {changes_html if changes_html else "<p>Project details have been modified.</p>"}
    
    <strong>Current Project Details:</strong>
    <div class="project-info">
        <p><strong>Project:</strong> {project.name}</p>
        <p><strong>Description:</strong> {project.description or 'No description provided'}</p>
        <p><strong>Deadline:</strong> {project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set'}</p>
        <p><strong>Status:</strong> {project.status.value}</p>
        <p><strong>Owner:</strong> {project.owner.email}</p>
    </div>
    
    <strong>Team Members:</strong>
    <ul>
        <li>{project.owner.email} (Owner)</li>
        {"".join([f"<li>{collab.email} (Collaborator)</li>" for collab in project.collaborators])}
    </ul>
    """
    
    success = email_service.send_notification_email(
        recipients,
        subject,
        message,
        project.name,
        project.id,
        "project_update"
    )
    
    print(f"DEBUG: Project update email sent successfully: {success}")

def send_project_collaborator_added_email_notification(project, added_by, new_collaborators):
    """Send email when collaborators are added to a project"""
    if not new_collaborators:
        return
    
    for collaborator in new_collaborators:
        # Don't send email to the person who added them
        if collaborator.id == added_by.id:
            continue
            
        print(f"DEBUG: Adding collaborator {collaborator.email} to project {project.name}")
        
        subject = f"👥 You've been added to project: {project.name}"
        
        message = f"""
        <strong>You have been added as a collaborator to a project:</strong>
        
        <div class="project-info">
            <p><strong>Project:</strong> {project.name}</p>
            <p><strong>Description:</strong> {project.description or 'No description provided'}</p>
            <p><strong>Deadline:</strong> {project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set'}</p>
            <p><strong>Status:</strong> {project.status.value}</p>
            <p><strong>Owner:</strong> {project.owner.email}</p>
            <p><strong>Added by:</strong> {added_by.email}</p>
        </div>
        
        <strong>Your Role:</strong> Collaborator
        
        <em>You can now view and contribute to this project.</em>
        """
        
        success = email_service.send_notification_email(
            [collaborator.email],
            subject,
            message,
            project.name,
            project.id,
            "project_collaborator_added"
        )
        
        print(f"DEBUG: Project collaborator email sent to {collaborator.email}: {success}")

def get_project_notification_recipients(project, excluded_user_id):
    """Get email recipients for project notifications, excluding the user who triggered the event"""
    recipients = set()
    
    # Add project owner if not excluded
    if project.owner_id != excluded_user_id:
        recipients.add(project.owner.email)
    
    # Add collaborators if not excluded
    for collaborator in project.collaborators:
        if collaborator.id != excluded_user_id:
            recipients.add(collaborator.email)
    
    return list(recipients)