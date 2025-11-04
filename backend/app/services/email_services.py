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
        self.cooldown = 60  # Reduced to 1 minute for better UX
    
    def can_send_email(self, task_id, recipient, notification_type):
        # Different cooldown for different notification types
        key = f"{task_id}_{recipient}_{notification_type}"
        now = datetime.now().timestamp()
        
        # Allow immediate sending for comment and update notifications
        if notification_type in ["new_comment", "task_updated", "task_creation"]:
            return True
            
        if key in self.last_sent and now - self.last_sent[key] < self.cooldown:
            return False
        self.last_sent[key] = now
        return True
    
    def send_notification_email(self, recipient_emails, subject, message, task_title, task_id, notification_type):
        """Send email notification via Power Automate webhook"""
        if not self.enabled or not recipient_emails:
            print(f"DEBUG: Email service disabled or no recipients. Enabled: {self.enabled}, Recipients: {recipient_emails}")
            return False
        
        # Filter recipients with cooldown check
        filtered_recipients = []
        for recipient in (recipient_emails if isinstance(recipient_emails, list) else [recipient_emails]):
            if self.can_send_email(task_id, recipient, notification_type):
                filtered_recipients.append(recipient)
        
        if not filtered_recipients:
            print(f"DEBUG: All recipients are in cooldown period for {notification_type}")
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
            
            print(f"DEBUG: Sending {notification_type} email to {filtered_recipients}")
            print(f"DEBUG: Subject: {subject}")
            
            response = requests.post(
                self.power_automate_webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            success = response.status_code in [200, 202]
            print(f"DEBUG: {notification_type} email sent successfully: {success}, Status: {response.status_code}")
            return success
            
        except Exception as e:
            print(f"DEBUG: {notification_type} email notification failed: {e}")
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
    """Send email for new comments - FIXED to always send to all involved users"""
    recipients = get_notification_recipients(task, excluded_user_id)
    
    print(f"DEBUG: Comment email - Task: {task.title}")
    print(f"DEBUG: Comment by: {comment.user.email}")
    print(f"DEBUG: Recipients: {recipients}")
    
    if not recipients:
        print("DEBUG: No recipients found for comment email")
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
    • Commented: {comment.created_at.strftime('%Y-%m-%d %H:%M')}<br>
    • Status: {task.status.value}<br>
    • Due Date: {task.duedate.strftime('%Y-%m-%d') if task.duedate else 'Not set'}
    
    <br><br>
    <em>You can view and reply to this comment in the task details.</em>
    """
    
    success = email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "new_comment"
    )
    
    print(f"DEBUG: Comment email sent successfully: {success}")

def send_task_update_email_notification(task, updated_by, updated_fields, excluded_user_id):
    """Send email for task updates with better field tracking - SYNCED with in-app"""
    recipients = get_notification_recipients(task, excluded_user_id)
    
    print(f"DEBUG: Task update email - Task: {task.title}, Updated by: {updated_by.email}")
    print(f"DEBUG: Updated fields: {[f['field'] for f in updated_fields]}")
    print(f"DEBUG: Recipients: {recipients}")
    
    if not recipients:
        print(f"DEBUG: No recipients for task update email")
        return
    
    # Format changes in a more readable way - SYNCED with in-app notification
    changes_html = ""
    for change in updated_fields:
        field_name = change['field'].replace('_', ' ').title()
        old_val = change['old_value'] or 'Empty'
        new_val = change['new_value'] or 'Empty'
        
        # Use same formatting as in-app notifications
        if field_name.lower() == 'due date':
            changes_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107;">
                <strong>📅 Due Date:</strong><br>
                <span style="color: #dc2626;">From: {old_val}</span><br>
                <span style="color: #16a34a;">To: {new_val}</span>
            </div>
            """
        elif field_name.lower() == 'priority':
            changes_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #d1ecf1; border-left: 4px solid #0dcaf0;">
                <strong>⚡ Priority:</strong><br>
                <span style="color: #dc2626;">From: {old_val}</span><br>
                <span style="color: #16a34a;">To: {new_val}</span>
            </div>
            """
        elif field_name.lower() == 'status':
            changes_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #d4edda; border-left: 4px solid #198754;">
                <strong>🔄 Status:</strong><br>
                <span style="color: #dc2626;">From: {old_val}</span><br>
                <span style="color: #16a34a;">To: {new_val}</span>
            </div>
            """
        elif field_name.lower() == 'assignee':
            changes_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #e2e3e5; border-left: 4px solid #6c757d;">
                <strong>👤 Assignee:</strong><br>
                <span style="color: #dc2626;">From: {old_val}</span><br>
                <span style="color: #16a34a;">To: {new_val}</span>
            </div>
            """
        elif field_name.lower() == 'collaborators':
            changes_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #e2e3e5; border-left: 4px solid #6c757d;">
                <strong>👥 Collaborators have been updated</strong>
            </div>
            """
        elif field_name.lower() == 'attachment':
            if new_val == "Removed":
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #f8d7da; border-left: 4px solid #dc3545;">
                    <strong>📎 File Removed:</strong><br>
                    <span style="color: #dc2626;">Removed file: {old_val}</span>
                </div>
                """
            elif old_val == "None":
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #d1edf1; border-left: 4px solid #0dcaf0;">
                    <strong>📎 File Added:</strong><br>
                    <span style="color: #16a34a;">Added new file: {new_val}</span>
                </div>
                """
            else:
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #e2e3e5; border-left: 4px solid #6c757d;">
                    <strong>📎 File Changed:</strong><br>
                    <span style="color: #dc2626;">From: {old_val}</span><br>
                    <span style="color: #16a34a;">To: {new_val}</span>
                </div>
                """
        else:
            changes_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #6c757d;">
                <strong>🔧 {field_name}:</strong><br>
                <span style="color: #dc2626;">From: {old_val}</span><br>
                <span style="color: #16a34a;">To: {new_val}</span>
            </div>
            """
    
    subject = f"✏️ Task updated: {task.title}"
    message = f"""
    <strong>{updated_by.email} updated task '{task.title}':</strong>
    
    {changes_html if changes_html else "<p>Task details have been modified.</p>"}
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
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
    """Send email to all involved users when a task is created - SYNCED with in-app"""
    recipients = get_notification_recipients(task, created_by.id)
    
    print(f"DEBUG: Task creation email - Task: {task.title}")
    print(f"DEBUG: Created by: {created_by.email}")
    print(f"DEBUG: Recipients: {recipients}")
    
    if not recipients:
        print("DEBUG: No recipients found for email notification")
        return
    
    subject = f"🆕 New task created: {task.title}"
    
    # Same information as in-app notification
    message = f"""
    <strong>🆕 New task has been created by {created_by.email}:</strong>
    
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
        {"".join([f"<li>{collab.email} (Collaborator)</li>" for collab in task.collaborators])}
    </ul>
    
    <em>This task has been added to your schedule. You will receive due date reminders as the deadline approaches.</em>
    """
    
    success = email_service.send_notification_email(
        recipients,
        subject,
        message,
        task.title,
        task.id,
        "task_creation"
    )
    
    print(f"DEBUG: Task creation email sent successfully: {success}")

def send_due_date_reminder_email(task, days_until_due):
    """Send due date reminder emails - SYNCED with in-app"""
    recipients = get_notification_recipients(task, None)
    if not recipients:
        return
    
    status = "overdue" if days_until_due < 0 else "due soon"
    days_text = f"{-days_until_due} days ago" if days_until_due < 0 else f"in {days_until_due} days"
    icon = "⚠️" if days_until_due < 0 else "📅"
    
    subject = f"{icon} Task {status}: {task.title}"
    
    # Same information as in-app notification
    if days_until_due == 0:
        message_text = "is due today!"
    elif days_until_due == 1:
        message_text = "is due tomorrow!"
    else:
        message_text = f"is due in {days_until_due} days"
    
    message = f"""
    <strong>{icon} Task '{task.title}' {message_text}</strong>
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #2563eb; margin: 10px 0;">
        <p><strong>Due Date:</strong> {task.duedate.strftime('%Y-%m-%d')}</p>
        <p><strong>Project:</strong> {task.project.name if task.project else 'No Project'}</p>
        <p><strong>Current Status:</strong> {task.status.value}</p>
        <p><strong>Priority:</strong> {task.priority}</p>
    </div>
    
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
    """Send email when a project is updated - FIXED to handle list of changes"""
    recipients = get_project_notification_recipients(project, updated_by.id)
    
    print(f"DEBUG: Project update email - Project: {project.name}")
    print(f"DEBUG: Updated by: {updated_by.email}")
    print(f"DEBUG: Updated fields: {len(updated_fields)} changes")
    print(f"DEBUG: Recipients: {recipients}")
    
    if not recipients:
        print("DEBUG: No recipients found for project update email")
        return
    
    # Format changes
    changes_html = ""
    if updated_fields:
        for change in updated_fields:
            field = change.get('field', '').title()
            old_value = change.get('old_value', '')
            new_value = change.get('new_value', '')
            
            if field.lower() == 'attachment':
                if new_value == "Removed":
                    changes_html += f"""
                    <div style="margin: 10px 0; padding: 10px; background: #f8d7da; border-left: 4px solid #dc3545;">
                        <strong>📎 File Removed:</strong><br>
                        <span style="color: #dc2626;">Removed file: {old_value}</span>
                    </div>
                    """
                elif old_value == "None":
                    changes_html += f"""
                    <div style="margin: 10px 0; padding: 10px; background: #d1edf1; border-left: 4px solid #0dcaf0;">
                        <strong>📎 File Added:</strong><br>
                        <span style="color: #16a34a;">Added new file: {new_value}</span>
                    </div>
                    """
            elif field.lower() == 'deadline':
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107;">
                    <strong>📅 Deadline:</strong><br>
                    <span style="color: #dc2626;">From: {old_value}</span><br>
                    <span style="color: #16a34a;">To: {new_value}</span>
                </div>
                """
            elif field.lower() == 'status':
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #d4edda; border-left: 4px solid #198754;">
                    <strong>🔄 Status:</strong><br>
                    <span style="color: #dc2626;">From: {old_value}</span><br>
                    <span style="color: #16a34a;">To: {new_value}</span>
                </div>
                """
            elif field.lower() == 'owner':
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #e2e3e5; border-left: 4px solid #6c757d;">
                    <strong>👤 Owner:</strong><br>
                    <span style="color: #dc2626;">From: {old_value}</span><br>
                    <span style="color: #16a34a;">To: {new_value}</span>
                </div>
                """
            elif field.lower() == 'collaborators':
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #e2e3e5; border-left: 4px solid #6c757d;">
                    <strong>👥 Collaborators Updated</strong><br>
                    <span style="color: #dc2626;">From: {old_value}</span><br>
                    <span style="color: #16a34a;">To: {new_value}</span>
                </div>
                """
            else:
                changes_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #6c757d;">
                    <strong>🔧 {field}:</strong><br>
                    <span style="color: #dc2626;">From: {old_value}</span><br>
                    <span style="color: #16a34a;">To: {new_value}</span>
                </div>
                """
    
    subject = f"✏️ Project updated: {project.name}"
    
    message = f"""
    <strong>Project '{project.name}' has been updated by {updated_by.email}:</strong>
    
    {changes_html if changes_html else "<p>Project details have been modified.</p>"}
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
        <p><strong>Current Project Details:</strong></p>
        <p><strong>Project:</strong> {project.name}</p>
        <p><strong>Description:</strong> {project.description or 'No description provided'}</p>
        <p><strong>Deadline:</strong> {project.deadline.strftime('%Y-%m-%d') if project.deadline else 'Not set'}</p>
        <p><strong>Status:</strong> {project.status.value}</p>
        <p><strong>Owner:</strong> {project.owner.email}</p>
        <p><strong>Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
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