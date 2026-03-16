import os


class Debug:
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")


class Production:
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY", "production-secret-key")


config_dict = {
    "Debug": Debug,
    "Production": Production
}