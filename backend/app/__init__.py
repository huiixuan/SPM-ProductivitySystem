from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from .models import db
from .routes.auth import auth_bp
from .routes.user import user_bp
from .routes.task import task_bp

migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
   
    
    CORS(app, resources={r"/auth/*": {"origins": "http://localhost:5173"},
                         r"/api/*": {"origins": "http://localhost:5173"}})

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


    return app