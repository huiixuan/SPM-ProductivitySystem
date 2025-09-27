from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime 

db = SQLAlchemy()


project_collaborators = Table(
    'project_collaborators',
    db.Model.metadata,
    Column('project_id', Integer, ForeignKey('project.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
     # 1:N Relationship (Manager -> Projects Managed)
    projects_managed = relationship('Project', back_populates='manager')
    
    # M:N Relationship (User <-> Projects Collaborating On)
    projects_collaboration = relationship(
        'Project',
        secondary=project_collaborators,
        back_populates='collaborators' 
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False) 
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # 1:N Relationship (Project -> Manager)
    manager = relationship('User', back_populates='projects_managed')
    
    # M:N Relationship (Project <-> Collaborators/Users)
    collaborators = relationship(
        'User', 
        secondary=project_collaborators, 
        back_populates='projects_collaboration' # 🛑 CORRECTED: back_populates name must match the one in User model
    )
    
    # 1:N Relationship (Project -> Attachments)
    attachments = relationship('Attachment', back_populates='project', cascade='all, delete-orphan')
    
    
class Attachment(db.Model):
    __tablename__ = 'attachment'
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255))
    storage_path = db.Column(db.String(255), nullable=False) 
    file_type = db.Column(db.String(50)) 
    upload_date = db.Column(db.DateTime, default=datetime.utcnow) 
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # N:1 Relationship (Attachment -> Project)
    project = relationship('Project', back_populates='attachments')
