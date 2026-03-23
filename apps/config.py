import os
from pathlib import Path



class Config(object):
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # folder database
    DB_DIR = BASE_DIR / "database"
    
    # pastikan folder ada
    DB_DIR.mkdir(exist_ok=True)
    
    # file database
    DATABASE = DB_DIR / "database.db"
    
    # ================================================
    # MQTT CONFIGURATION
    # ================================================
    MQTT_BROKER_URL = os.getenv('MQTT_BROKER_URL', None)
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', None)
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'server-webs')
    MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', 60))
   
    # ================================================
    # MQTT TOPIC STRUCTURE (CONSISTENT)
    # ================================================
    MQTT_TOPIC_BASE = "sensors"

    MQTT_TOPIC_TEMPERATURE = f"{MQTT_TOPIC_BASE}/temperature"
    MQTT_TOPIC_HUMIDITY    = f"{MQTT_TOPIC_BASE}/humidity"
    MQTT_TOPIC_PH          = f"{MQTT_TOPIC_BASE}/ph"
    MQTT_TOPIC_TDS         = f"{MQTT_TOPIC_BASE}/tds"

    # Subscribe semua sensor
    MQTT_TOPIC_ALL = f"{MQTT_TOPIC_BASE}/+"

    # ================================================
    # WEBSOCKET CONFIGURATION
    # ================================================
    SOCKETIO_CORS_ALLOWED = os.getenv("SOCKETIO_CORS_ALLOWED", "*")
    SOCKETIO_PING_TIMEOUT = int(os.getenv("SOCKETIO_PING_TIMEOUT", 60))
    SOCKETIO_PING_INTERVAL = int(os.getenv("SOCKETIO_PING_INTERVAL", 25))
    
    # ================================================
    # SIMULATION MODE (untuk development tanpa MQTT broker)
    # ================================================
    ENABLE_SIMULATION = os.getenv("ENABLE_SIMULATION", "False") == "True"
    SIMULATION_INTERVAL = int(os.getenv("SIMULATION_INTERVAL", 1))


class Debug(Config):
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # Di development, kita bisa matikan auto-connect jika tidak ada broker
    MQTT_AUTO_CONNECT = os.getenv("DEV_MQTT_AUTO_CONNECT", "False") == "True"
    
    # Development WebSocket (allow all origins for testing)
    SOCKETIO_CORS_ALLOWED = os.getenv("DEV_SOCKETIO_CORS_ALLOWED", "*")
    
    # Logging level untuk development
    LOG_LEVEL = "DEBUG"


class Production(Config):
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY", "production-secret-key")
    
    # Production MQTT (biasanya broker eksternal)
    MQTT_BROKER = os.getenv("PROD_MQTT_BROKER", "mqtt.example.com")
    MQTT_PORT = int(os.getenv("PROD_MQTT_PORT", 1883))
    MQTT_USERNAME = os.getenv("PROD_MQTT_USERNAME", "")
    MQTT_PASSWORD = os.getenv("PROD_MQTT_PASSWORD", "")
    MQTT_AUTO_CONNECT = os.getenv("PROD_MQTT_AUTO_CONNECT", "True") == "True"
    
    # Di production, matikan simulasi
    ENABLE_SIMULATION = False
    
    # Production WebSocket (hanya allow specific domains)
    SOCKETIO_CORS_ALLOWED = os.getenv("PROD_SOCKETIO_CORS_ALLOWED", "https://yourdomain.com")
    
    # Logging level untuk production
    LOG_LEVEL = "WARNING"



config_dict = {
    "Production": Production,
    "Development": Debug # Alias untuk Debug
}