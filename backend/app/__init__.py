from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from .models import db
from .routes.auth import auth_bp
from .routes.user import user_bp
from .routes.task import task_bp
from .routes.project import project_bp

migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    CORS(app, origins=["http://localhost:5173"])

    # uploads (for project PDF attachments)
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")

    # ✅ Allow both localhost + 127.0.0.1, Authorization header, all methods
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

    CORS(
        app,
        resources={r"/*": {"origins": ALLOWED_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )

    # JWT config
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")
    jwt.init_app(app)

    # DB + Migrations
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(task_bp, url_prefix="/api/task")
    app.register_blueprint(project_bp, url_prefix="/api/project")

    return app
