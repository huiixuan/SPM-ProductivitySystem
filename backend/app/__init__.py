from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from .models import db
from .routes.auth import auth_bp
from .routes.user import user_bp
from .routes.task import task_bp


migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    CORS(app) 

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(task_bp, url_prefix="/api/task")


    return app