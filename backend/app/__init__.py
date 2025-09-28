from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from .models import db
from .routes.hello import hello_bp
from .routes.auth import auth_bp

migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    CORS(app)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # JWT config
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")  
    jwt.init_app(app)

    # DB + Migrations
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(hello_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    return app