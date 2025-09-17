from flask import Flask
from flask_cors import CORS
from .routes.hello import hello_bp

def create_app():
    app = Flask(__name__)
    CORS(app) 

    # Register blueprints
    app.register_blueprint(hello_bp, url_prefix="/api")

    return app