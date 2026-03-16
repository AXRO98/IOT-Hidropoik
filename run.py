"""
File        : run.py
Author      : Keyfin Agustio Suratman
Description : App dashboard untuk IoT Hidroponik project robotik SMA Negeri 7 Manado.
Created     : 2026-03-16
"""

import  os
from    sys import exit
from    dotenv import load_dotenv
from    flask_minify import Minify

from apps.config import config_dict
from apps import create_app


# Load environment variables dari .env
load_dotenv()


# -------------------------------------------------
# Debug Mode
# -------------------------------------------------

DEBUG = (os.getenv("DEBUG", "False") == "True")
PORT = int(os.getenv("PORT", 5000))


# -------------------------------------------------
# Load Configuration
# -------------------------------------------------

config_mode = "Debug" if DEBUG else "Production"

try:
    app_config = config_dict[config_mode]

except KeyError:
    exit("Error: Invalid <config_mode>. Expected values [Debug, Production]")


# -------------------------------------------------
# Create Flask App
# -------------------------------------------------

app = create_app(app_config)


# -------------------------------------------------
# Enable HTML Minification
# -------------------------------------------------

if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)


# -------------------------------------------------
# Debug Logging
# -------------------------------------------------

if DEBUG:
    app.logger.info(f"DEBUG = {DEBUG}")
    app.logger.info(f"PORT  = {PORT}")


# -------------------------------------------------
# Run Server
# -------------------------------------------------

if __name__ == "__main__":

    try:
        app.run(
            debug=DEBUG,
            host="0.0.0.0",
            port=PORT
        )

    except Exception as error_page:

        print("[=========================[ ERROR ]=========================]")
        print(f"Error: {error_page}")
        print("[===========================================================]")