"""
File        : run.py
Author      : Keyfin Agustio Suratman
Description : App dashboard untuk IoT Hidroponik project robotik SMA Negeri 7 Manado.
"""

import os
import sys
import time
import logging
import werkzeug
from sys import exit

from dotenv import load_dotenv
from flask import request, g
from flask_minify import Minify
from flask_wtf.csrf import CSRFProtect
# from flask_talisman import Talisman

from apps import create_app
from apps.config import config_dict
from apps.services import init_services
from apps.extensions import socketio

from apps.utils import (
    log_request,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_server_event,
    print_startup_banner
)

# -------------------------------------------------
# ENV & BASIC SETUP
# -------------------------------------------------

load_dotenv()

DEBUG = os.getenv("DEBUG", "False") == "True"
PORT = int(os.getenv("PORT", 5000))
CONFIG_MODE = "Development" if DEBUG else "Production"


# -------------------------------------------------
# DISABLE DEFAULT FLASK LOGGING
# -------------------------------------------------

def disable_flask_logging():
    logging.getLogger("werkzeug").disabled = True
    sys.modules['flask.cli'].show_server_banner = lambda *x: None
    werkzeug.serving._log = lambda *args, **kwargs: None

# -------------------------------------------------
# LOAD CONFIG
# -------------------------------------------------

def get_config():
    try:
        return config_dict[CONFIG_MODE]
    except KeyError:
        exit("Error: Invalid config mode")

# -------------------------------------------------
# CREATE APP
# -------------------------------------------------

app = create_app(get_config())

@app.context_processor
def inject_version():
    return {'app_version': os.getenv("VERSION", "0.0.0")}

# -------------------------------------------------
# MIDDLEWARE (REQUEST LOGGER)
# -------------------------------------------------

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    response_time = time.time() - g.start_time if hasattr(g, "start_time") else None

    log_request(
        request.headers.get("X-Forwarded-For", request.remote_addr),
        request.method,
        request.path,
        response.status_code,
        request.headers.get("User-Agent", "Unknown"),
        response_time
    )
    return response

# -------------------------------------------------
# SECURITY & PERFORMANCE
# -------------------------------------------------

def init_security(app):
    if not DEBUG:
        Minify(app=app, html=True, js=True, cssless=True)
        CSRFProtect(app)
        # Talisman(app)

        log_success("Security: ENABLED")
    else:
        log_warning("Debug Mode: ON")

# -------------------------------------------------
# ERROR HANDLER
# -------------------------------------------------

def register_error_handlers(app):

    @app.errorhandler(404)
    def not_found(error):
        log_error(f"404: {request.path}")
        return "Page not found", 404

    @app.errorhandler(500)
    def internal(error):
        log_error(f"500: {str(error)}")
        return "Internal server error", 500

# -------------------------------------------------
# INIT (RUN ONLY ONCE)
# -------------------------------------------------

def init_once():
    """Semua yang HARUS jalan sekali saja"""
    
    print_startup_banner(
        CONFIG_MODE,
        DEBUG,
        PORT,
        os.getenv("VERSION"),
        os.getenv("AUTHOR")
    )


# -------------------------------------------------
# MAIN
# -------------------------------------------------

# run.py (bagian MAIN)

if __name__ == "__main__":
    try:
        disable_flask_logging()
        register_error_handlers(app)

        # 🔥 FIX DOUBLE RUN (PENTING)
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            # 1. Banner dicetak duluan
            init_once()                     # mencetak banner

            # 2. Keamanan
            init_security(app)

            # 3. Inisialisasi MQTT (log akan muncul setelah banner)
            from apps import init_mqtt
            mqtt_client, ws_service = init_mqtt(app)
            app.mqtt_client = mqtt_client
            app.websocket_service = ws_service

            # 4. Inisialisasi service lainnya (WebSocket, simulasi, dll)
            init_services(app)

        socketio.run(
            app,
            host="0.0.0.0",
            port=PORT,
            debug=DEBUG,
            allow_unsafe_werkzeug=DEBUG,
            use_reloader=DEBUG
        )

    except KeyboardInterrupt:
        print()
        log_server_event("STOP", "User interrupted")

    except Exception as err:
        print()
        log_error("=" * 60)
        log_error(f"Startup Failed: {str(err)}")
        log_error("=" * 60)

        if DEBUG:
            import traceback
            traceback.print_exc()

        exit(1)