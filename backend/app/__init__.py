from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from .models import db
from .routes.hello import hello_bp

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    CORS(app) 

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(hello_bp, url_prefix="/api")

    return app