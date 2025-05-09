from flask import Flask
from app.routes import webhook_bp
from app.utils import setup_logger

def create_app():
    app = Flask(__name__)

    # Set up logging
    setup_logger()

    # Register blueprints
    app.register_blueprint(webhook_bp)

    return app
