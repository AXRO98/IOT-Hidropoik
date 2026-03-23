"""
Flask Application Factory
"""

import os
from flask import Flask, redirect
from importlib import import_module

from apps.extensions import login_manager, socketio
from apps.utils import log_info, log_success, log_warning, log_error
from apps.services.mqtt_client import mqtt_client

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

BLUEPRINT_MODULES = [
    "authentication",
    "dashboard",
]

# -------------------------------------------------
# BLUEPRINT REGISTRATION
# -------------------------------------------------

def register_blueprints(app: Flask):
    for module_name in BLUEPRINT_MODULES:
        module = import_module(f"apps.{module_name}.routes")
        app.register_blueprint(module.blueprint)

# -------------------------------------------------
# EXTENSIONS
# -------------------------------------------------

def register_extensions(app: Flask):
    login_manager.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = "authentication_blueprint.login"

# -------------------------------------------------
# HANDLERS
# -------------------------------------------------

def register_handlers(app: Flask):

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect("/login")

# -------------------------------------------------
# MQTT INTEGRATION
# -------------------------------------------------

def init_mqtt(app: Flask):
    """
    Inisialisasi MQTT client dan integrasi dengan WebSocket.
    Hanya dijalankan sekali pada proses utama Flask.
    """
    # Cek apakah ini proses utama (bukan reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        log_info("Skipping MQTT init - reloader process")
        return None, None

    from apps.services.mqtt_client import mqtt_client
    from apps.services.websocket_service import websocket_service

    # Initialize MQTT client
    log_info("Initializing MQTT client...")
    mqtt_client.init_app(app)

    # Link MQTT client to WebSocket service
    websocket_service.set_mqtt_client(mqtt_client)

    log_success("MQTT and WebSocket integration initialized")

    return mqtt_client, websocket_service

# -------------------------------------------------
# APP FACTORY
# -------------------------------------------------

def create_app(config):
    """Create Flask App (Factory Pattern)"""

    base_dir = config.BASE_DIR

    app = Flask(
        __name__,
        static_url_path="/static",
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )

    # Load config
    app.config.from_object(config)

    # Register core components (tanpa MQTT)
    register_extensions(app)
    register_blueprints(app)
    register_handlers(app)

    return app