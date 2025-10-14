from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import enum

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

    # relationships
    owned_tasks = relationship("Task", back_populates="owner")
    tasks = relationship("Task", secondary=task_collaborators, back_populates="collaborators")

    owned_projects = relationship("Project", back_populates="owner")
    projects = relationship("Project", secondary=project_collaborators, back_populates="collaborators")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    

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
    owner = relationship("User", back_populates="owned_tasks")

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="project_tasks")

    collaborators = relationship(
        "User", secondary=task_collaborators, back_populates="tasks"
    )

    attachments = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )

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
            "collaborators": [
                {"id": user.id, "email": user.email, "name": user.name}
                for user in self.collaborators
            ],
            "attachments": [
                {"id": att.id, "filename": att.filename}
                for att in self.attachments
            ]
        }
    
class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)

    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="attachments")

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.Date)
    status = db.Column(db.Enum(ProjectStatus, native_enum=False), default=ProjectStatus.NOT_STARTED)
    attachment_path = db.Column(db.String(255))

    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="owned_projects")

    project_tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

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
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value if self.status else None,
            "attachment_path": self.attachment_path,
            "owner_id": self.owner_id,
            "collaborators": [c.email for c in self.collaborators],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
