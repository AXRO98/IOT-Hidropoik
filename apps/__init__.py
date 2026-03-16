"""
Flask Application Factory

File ini bertugas untuk:
1. Membuat instance aplikasi Flask
2. Memuat konfigurasi aplikasi
3. Mendaftarkan semua Blueprint (module aplikasi)

Struktur project yang diasumsikan:

apps/
 ├── authentication/
 │    └── routes.py
 │
 ├── dashboard/
 │    └── routes.py
 │
 ├── config.py
 │
 └── __init__.py  (file ini)
"""

from flask import Flask
from importlib import import_module


def register_blueprints(app: Flask):
    """
    Mendaftarkan semua blueprint dari module aplikasi.

    Setiap module harus memiliki file:
        apps/<module>/routes.py

    Dan di dalamnya harus terdapat:
        blueprint = Blueprint(...)
    """

    modules = (
        "authentication",
        "dashboard"
    )

    for module_name in modules:
        module = import_module(f"apps.{module_name}.routes")
        app.register_blueprint(module.blueprint)


def create_app(config):
    """
    Application Factory.

    Parameter
    ---------
    config : object
        Class konfigurasi Flask yang akan digunakan
        (Debug / Production)

    Returns
    -------
    Flask
        Instance aplikasi Flask yang sudah siap digunakan.
    """

    app = Flask(__name__)

    # Load konfigurasi aplikasi
    app.config.from_object(config)

    # Register semua blueprint
    register_blueprints(app)

    return app