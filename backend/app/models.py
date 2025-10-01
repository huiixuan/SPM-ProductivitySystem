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

task_collaborators = db.Table(
    "task_collaborators",
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True)
)

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(UserRole, native_enum=False), nullable=False, default=UserRole.STAFF)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)

    owned_tasks = relationship("Task", back_populates="owner")

    tasks = relationship(
        "Task", secondary=task_collaborators, back_populates="collaborators"
    )

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

    collaborators = relationship(
        "User", secondary=task_collaborators, back_populates="tasks"
    )

    attachments = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )

class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)

    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="attachments")
