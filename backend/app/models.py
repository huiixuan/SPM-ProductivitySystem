from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import UniqueConstraint, Index

db = SQLAlchemy()

class UserRole(enum.Enum):
    STAFF = "STAFF"
    MANAGER = "MANAGER"
    DIRECTOR = "DIRECTOR"
    HR = "HR"

class TaskStatus(enum.Enum):
    UNASSIGNED = "Unassigned"
    ONGOING = "Ongoing"
    PENDING_REVIEW = "Pending Review"
    COMPLETED = "Completed"

class ProjectStatus(enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

class NotificationType(enum.Enum):
    DUE_DATE_REMINDER = "due_date_reminder"
    NEW_COMMENT = "new_comment"
    TASK_UPDATED = "task_updated"
    PROJECT_UPDATED = "project_updated"
    TASK_ASSIGNMENT = "task_assignment" 
    PROJECT_ASSIGNMENT = "project_assignment"  

class RecurrenceType(enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

# association tables
task_collaborators = db.Table(
    "task_collaborators",
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)

project_collaborators = db.Table(
    "project_collaborators",
    db.Column("project_id", db.Integer, db.ForeignKey("projects.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(UserRole, native_enum=False), nullable=False, default=UserRole.STAFF)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)

    owned_tasks = relationship("Task", back_populates="owner")
    tasks = relationship("Task", secondary=task_collaborators, back_populates="collaborators")

    owned_projects = relationship("Project", back_populates="owner")
    projects = relationship("Project", secondary=project_collaborators, back_populates="collaborators")

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="comments")
    user = relationship("User")
    notifications = relationship("Notification", back_populates="comment")

class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    duedate = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.UNASSIGNED)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    notes = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    priority = db.Column(db.Integer, nullable=False, server_default='1', default=1)

    isRecurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_type = db.Column(db.Enum(RecurrenceType, native_enum=False), default=RecurrenceType.NONE, nullable=False)
    recurrence_interval = db.Column(db.Integer, nullable=True)

    owner = relationship("User", back_populates="owned_tasks")
    project = relationship("Project", back_populates="project_tasks")
    
    collaborators = relationship(
        "User", secondary=task_collaborators, back_populates="tasks"
    )

    attachments = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )

    notifications = relationship(
        "Notification",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

    parent_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    subtasks = relationship("Task", backref=db.backref("parent", remote_side=[id]), cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "duedate": self.duedate.isoformat() if self.duedate else None,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notes": self.notes,
            "owner_email": self.owner.email if self.owner else None,
            "project": self.project.name if self.project else None,
            "priority": self.priority,
            "parent_id": self.parent_id,
            "subtasks": [sub.to_dict() for sub in self.subtasks],
            "collaborators": [
                {"id": user.id, "email": user.email, "name": user.name}
                for user in self.collaborators
            ],
            "attachments": [
                {"id": att.id, "filename": att.filename}
                for att in self.attachments
            ],
            "is_recurring": self.isRecurring,
            "recurrence_type": self.recurrence_type.value if self.recurrence_type else None,
            "recurrence_interval": self.recurrence_interval
        }
    
class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)

    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True) 
    task = relationship("Task", back_populates="attachments")
    
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = relationship("Project", back_populates="attachments")

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    deadline = db.Column(db.Date)
    status = db.Column(db.Enum(ProjectStatus, native_enum=False), default=ProjectStatus.NOT_STARTED)
    
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="owned_projects")

    project_tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="project", cascade="all, delete-orphan")

    collaborators = relationship(
        "User",
        secondary=project_collaborators,
        back_populates="projects",
    )

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

   
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "notes": self.notes,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value if self.status else None,
        
            "owner_email": self.owner.email if self.owner else None,

            "attachments": [{"id": att.id, "filename": att.filename} for att in self.attachments],
            
            "collaborators": [{"id": c.id, "email": c.email} for c in self.collaborators],
        }

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    type = db.Column(db.Enum(NotificationType, native_enum=False), nullable=False, default=NotificationType.DUE_DATE_REMINDER)
    payload = db.Column(
        JSONB,
        nullable=False,
        default=dict,
    )

    trigger_days_before = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "task_id", "trigger_days_before", "type", name="uq_notification_unique_trigger"),
        Index("ix_notification_user_isread_created", "user_id", "is_read", "created_at"),
    )

    user = db.relationship("User", back_populates="notifications")
    task = db.relationship("Task", back_populates="notifications")
    project = db.relationship("Project")
    comment = db.relationship("Comment", back_populates="notifications")

    @staticmethod
    def build_payload(notification_type: NotificationType, **kwargs):
        if notification_type == NotificationType.DUE_DATE_REMINDER:
            return {
                "project_name": kwargs.get("project_name"),
                "task_title": kwargs.get("task_title"),
                "duedate": kwargs.get("duedate").isoformat() if kwargs.get("duedate") else None,
            }
        elif notification_type == NotificationType.NEW_COMMENT:
            return {
                "project_name": kwargs.get("project_name"),
                "task_title": kwargs.get("task_title"),
                "comment_author": kwargs.get("comment_author"),
                "comment_excerpt": kwargs.get("comment_excerpt"),
                "comment_id": kwargs.get("comment_id"),
            }
        elif notification_type == NotificationType.TASK_UPDATED:
            return {
                "project_name": kwargs.get("project_name"),
                "task_title": kwargs.get("task_title"),
                "updated_fields": kwargs.get("updated_fields"),  
                "updated_by": kwargs.get("updated_by"),
            }
        elif notification_type == NotificationType.PROJECT_UPDATED:
            return {
                "project_name": kwargs.get("project_name"),
                "updated_fields": kwargs.get("updated_fields"),
                "updated_by": kwargs.get("updated_by"),
            }
        elif notification_type == NotificationType.TASK_ASSIGNMENT: 
            return {
                "project_name": kwargs.get("project_name"),
                "task_title": kwargs.get("task_title"),
                "assigned_by": kwargs.get("assigned_by"),
                "role": kwargs.get("role"),
            }
        elif notification_type == NotificationType.PROJECT_ASSIGNMENT:  
            return {
                "project_name": kwargs.get("project_name"),
                "assigned_by": kwargs.get("assigned_by"),
                "role": kwargs.get("role"),
            }
        else:
            return {}

    @property
    def message(self):
        p = self.payload or {}
        notification_type = p.get("notification_type", "")

        if notification_type == "task_attachment_removed":
            task_title = p.get("task_title", "Task")
            attachment_filename = p.get("attachment_filename", "file")
            removed_by = p.get("removed_by", "Someone")
            return f"🗑️ {removed_by} removed attachment '{attachment_filename}' from task: '{task_title}'"

        if notification_type == "recurring_task_created":
            original_task_title = p.get("original_task_title", "Task")
            task_title = p.get("task_title", "Task")
            return f"🔄 New recurring task created from '{original_task_title}': '{task_title}'"

        if notification_type == "due_date_reminder":
            project_name = p.get("project_name", "No Project")
            task_title = p.get("task_title", "Task")
            days_until_due = p.get("days_until_due", 0)
            actual_days = p.get("actual_days_until_due", 0)
            
            if actual_days == 0:
                return f"📅 {project_name}: '{task_title}' is due today!"
            elif actual_days == 1:
                return f"📅 {project_name}: '{task_title}' is due tomorrow!"
            elif actual_days > 1:
                return f"📅 {project_name}: '{task_title}' is due in {actual_days} days."
            else:
                return f"⚠️ {project_name}: '{task_title}' is {-actual_days} days overdue!"


        if notification_type == "task_attachment_added":
            task_title = p.get("task_title", "Task")
            attachment_filename = p.get("attachment_filename", "file")
            added_by = p.get("added_by", "Someone")
            return f"📎 {added_by} added attachment '{attachment_filename}' to task: '{task_title}'"
    
 
        elif notification_type == "project_attachment_added":
            project_name = p.get("project_name", "Project")
            attachment_filename = p.get("attachment_filename", "file")
            added_by = p.get("added_by", "Someone")
            return f"📎 {added_by} added attachment '{attachment_filename}' to project: '{project_name}'"
    

        if notification_type == "project_creation":
            project_name = p.get("project_name", "Project")
            created_by = p.get("created_by", "Someone")
            return f"📁 {created_by} created new project: '{project_name}'"
        

        elif notification_type == "project_updated":
            project_name = p.get("project_name", "Project")
            updated_by = p.get("updated_by", "Someone")
            fields = p.get("updated_fields", [])
            
            if fields:
                changes = []
                for change in fields:
                    field = change.get('field', '').replace('_', ' ').title()
                    old_val = change.get('old_value', 'None')
                    new_val = change.get('new_value', 'None')
                    
                    if field.lower() == 'deadline':
                        changes.append(f"📅 Deadline changed from {old_val} to {new_val}")
                    elif field.lower() == 'status':
                        changes.append(f"🔄 Status changed from {old_val} to {new_val}")
                    elif field.lower() == 'owner':
                        changes.append(f"👤 Owner changed from {old_val} to {new_val}")
                    elif field.lower() == 'collaborators':
                        changes.append(f"👥 Collaborators updated")
                    elif field.lower() == 'attachment':
                        if new_val == "Removed":
                            changes.append(f"📎 Removed file: {old_val}")
                        elif old_val == "None":
                            changes.append(f"📎 Added file: {new_val}")
                        else:
                            changes.append(f"📎 File changed from {old_val} to {new_val}")
                    else:
                        changes.append(f"{field} changed from {old_val} to {new_val}")
                
                changes_str = ', '.join(changes)
                return f"✏️ {updated_by} updated project '{project_name}': {changes_str}"
            else:
                return f"✏️ {updated_by} updated project '{project_name}'"
        

        elif notification_type == "project_collaborator_added":
            project_name = p.get("project_name", "Project")
            added_by = p.get("added_by", "Someone")
            return f"👥 {added_by} added you as collaborator to project: '{project_name}'"


        elif self.type == NotificationType.TASK_ASSIGNMENT or notification_type == "task_assignment":
            project_name = p.get("project_name", "No Project")
            task_title = p.get("task_title", "Task")
            assigned_by = p.get("assigned_by", "Someone")
            role = p.get("role", "collaborator")
            return f"👤 {assigned_by} assigned you as {role} to task: '{task_title}' in {project_name}"

      
        elif self.type == NotificationType.PROJECT_ASSIGNMENT or notification_type == "project_assignment":
            project_name = p.get("project_name", "Project")
            assigned_by = p.get("assigned_by", "Someone")
            role = p.get("role", "collaborator")
            return f"👥 {assigned_by} assigned you as {role} to project: '{project_name}'"
    
        if self.type == NotificationType.DUE_DATE_REMINDER or notification_type == "due_date_reminder":
            pn = p.get("project_name", "No Project")
            tt = p.get("task_title", "Task")
            actual_days = p.get("actual_days_until_due", 0)
        
            if actual_days == 0:
                return f"📅 {pn}: '{tt}' is due today!"
            elif actual_days == 1:
                return f"📅 {pn}: '{tt}' is due tomorrow!"
            else:
                return f"📅 {pn}: '{tt}' is due in {actual_days} days."
    
        elif self.type == NotificationType.TASK_UPDATED:
            pn = p.get("project_name", "No Project")
            tt = p.get("task_title", "Task")
        
            if notification_type == "task_creation":
                created_by = p.get("created_by", "Someone")
                return f"🆕 {created_by} created new task: '{tt}' in {pn}"
        
            elif notification_type == "task_updated":
                updated_by = p.get("updated_by", "Someone")
                fields = p.get("updated_fields", [])
            
                if fields:
                    changes = []
                    for change in fields:
                        field = change.get('field', '').replace('_', ' ').title()
                        old_val = change.get('old_value', 'None')
                        new_val = change.get('new_value', 'None')
                    
                        # Format specific fields better
                        if field.lower() == 'due date':
                            changes.append(f"📅 Due date changed from {old_val} to {new_val}")
                        elif field.lower() == 'priority':
                            changes.append(f"⚡ Priority changed from {old_val} to {new_val}")
                        elif field.lower() == 'status':
                            changes.append(f"🔄 Status changed from {old_val} to {new_val}")
                        elif field.lower() == 'assignee':
                            changes.append(f"👤 Assignee changed from {old_val} to {new_val}")
                        elif field.lower() == 'collaborators':
                            changes.append(f"👥 Collaborators updated")
                        elif field.lower() == 'attachment':
                            if new_val == "Removed":
                                changes.append(f"📎 Removed file: {old_val}")
                            elif old_val == "None":
                                changes.append(f"📎 Added file: {new_val}")
                            else:
                                changes.append(f"📎 File changed from {old_val} to {new_val}")
                        else:
                            changes.append(f"{field} changed from {old_val} to {new_val}")
                
                    changes_str = ', '.join(changes)
                    return f"✏️ {updated_by} updated '{tt}': {changes_str}"
                else:
                    return f"✏️ {updated_by} updated '{tt}' in {pn}"
        
            # Fallback for old task update format
            updated_by = p.get("updated_by", "Someone")
            fields = p.get("updated_fields", [])
            if fields:
                changes = []
                for change in fields:
                    field = change.get('field', '').replace('_', ' ').title()
                    old_val = change.get('old_value', 'None')
                    new_val = change.get('new_value', 'None')
                    changes.append(f"{field} from {old_val} to {new_val}")
                changes_str = ', '.join(changes)
                return f"✏️ {updated_by} updated '{tt}' in {pn}: {changes_str}"
            else:
                return f"✏️ {updated_by} updated '{tt}' in {pn}"
    
        elif self.type == NotificationType.NEW_COMMENT:
            pn = p.get("project_name", "No Project") 
            tt = p.get("task_title", "Task")
            author = p.get("comment_author", "Someone")
            excerpt = p.get("comment_excerpt", "")
            return f"💬 {author} commented on '{tt}' in {pn}: {excerpt}"
    
        return "🔔 New notification"