"""
Module      : apps.services.mqtt_client
Author      : Keyfin Suratman
Description : MQTT Client untuk koneksi ke broker
Created     : 2026-03-23
Updated     : 2026-03-24
"""

import paho.mqtt.client as mqtt
import json
import threading
import ssl
from flask import current_app

# Import MQTT specific logger
from apps.utils import log_mqtt, log_info, log_success, log_warning, log_error
from apps.services.mqtt_service import process_sensor_data

class MQTTClient:
    """MQTT Client untuk koneksi ke broker"""
    
    def __init__(self, app=None):
        self.client = None
        self.app = None
        self.connected = False
        self.subscribed_topics = []

        self.broker_url = None
        self.broker_port = None
        self.keepalive = None

        self.reconnect_delay = 5
        self.max_reconnect_delay = 60

        self.reconnect_enabled = True
        self.status_auth = ''
        self.invalid_logged = False

        # topic default (belum ada app)
        self.topic_all = None

        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app

        # Ambil config DI SINI (bukan di __init__)
        self.topic_all = app.config.get('MQTT_TOPIC_ALL')
        self.topic_temp = app.config.get('MQTT_TOPIC_TEMPERATURE')

        self.broker_url = app.config.get('MQTT_BROKER_URL')
        self.broker_port = app.config.get('MQTT_BROKER_PORT')
        self.keepalive = app.config.get('MQTT_KEEPALIVE')
        
        # Ambil konfigurasi MQTT dari app.config atau dari run.py
        mqtt_config = app.config.get('MQTT_CONFIG', {})
                
        # Credentials
        username = mqtt_config.get('username') or app.config.get('MQTT_USERNAME')
        password = mqtt_config.get('password') or app.config.get('MQTT_PASSWORD')
        
        # Client ID
        client_id = mqtt_config.get('client_id') or app.config.get('MQTT_CLIENT_ID', 'flask_sensor_app')
        
        # Buat MQTT client
        self.client = mqtt.Client(client_id=client_id)
        
        # Set username/password jika ada
        if username and password:
            self.client.username_pw_set(username, password)
            log_info(f"MQTT credentials set for user: {username}")
        
        # Setup TLS jika port 8883 (HiveMQ Cloud)
        if self.broker_port == 8883:
            log_info("Setting up TLS for port 8883...")
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)
        
        # Set callback functions
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_disconnect = self._on_disconnect
        self.client.on_log = self._on_log
        
        # Start connection in background thread
        self._start_loop()
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.reconnect_delay = 5
            self.reconnect_enabled = True
            self.subscribe(self.topic_all)  # Subscribe ke semua topic sensor
            log_mqtt("CONNECTED", f"{self.broker_url}:{self.broker_port}", "Connection successful")
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            error_msg = error_messages.get(rc, f"Unknown error (code: {rc})")
            log_error(f"Failed to connect to MQTT broker: {error_msg}")
            log_mqtt("ERROR", f"{self.broker_url}:{self.broker_port}", error_msg)

            # Jika username/password salah, matikan reconnect dan hentikan loop
            if rc in [4, 5]:
                self.status_auth = 'invalid_credentials'
                self.reconnect_enabled = False  # Matikan reconnect
                if not self.invalid_logged:
                    log_error(f"MQTT loop stopped: invalid credentials for {self.broker_url}:{self.broker_port}")
                    log_mqtt("ERROR", f"{self.broker_url}:{self.broker_port}", "Invalid username/password - check .env")
                    self.invalid_logged = True
                # Hentikan loop client agar tidak ada percobaan lagi
                if self.client:
                    self.client.loop_stop()
            self.connected = False
    
    def _on_message(self, client, userdata, msg):
        """Callback saat menerima message dari MQTT broker"""
        try:
            topic = msg.topic
            payload_raw = msg.payload.decode('utf-8')

            # ================================
            # PARSE TOPIC
            # ================================
            topic_parts = topic.split('/')

            if len(topic_parts) == 2:
                base, sensor_type = topic_parts
            else:
                sensor_type = "unknown"
                log_warning(f"Invalid topic format: {topic}")

            # ================================
            # PARSE PAYLOAD (INI YANG DIPERBAIKI)
            # ================================
            try:
                data = json.loads(payload_raw)

                if not isinstance(data, dict):
                    data = {"value": data}

            except json.JSONDecodeError:
                data = {"value": payload_raw}
                log_warning(f"Non-JSON payload received: {payload_raw}")

            # ================================
            # TAMBAHKAN METADATA
            # ================================
            data['_sensor_type'] = sensor_type
            data['_topic'] = topic

            # ================================
            # PROCESS DATA
            # ================================
            with self.app.app_context():
                process_sensor_data(topic, data)

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            log_error(error_msg)
            log_mqtt("ERROR", topic if 'topic' in locals() else "unknown", error_msg)
    
    def _on_publish(self, client, userdata, mid):
        """Callback saat publish berhasil"""
        log_mqtt("PUB-ACK", f"mid:{mid}", "Message published successfully")
    
    def _on_disconnect(self, client, userdata, rc):
        if rc == 0:
            log_info("Disconnected from MQTT broker (clean disconnect)")
            log_mqtt("DISCONNECT", f"{self.broker_url}:{self.broker_port}", "Clean disconnect")
        else:
            if rc == 4 or rc == 5:
                log_error(f"Disconnected from MQTT broker due to invalid credentials (code: {rc})")
            else:
                log_warning(f"Unexpected disconnect from MQTT broker (code: {rc})")
                log_mqtt("ERROR", f"{self.broker_url}:{self.broker_port}", f"Unexpected disconnect (code: {rc})")

        self.connected = False

        # Jangan lakukan reconnect jika kredensial tidak valid atau reconnect dinonaktifkan
        if self.status_auth == 'invalid_credentials' or not self.reconnect_enabled:
            log_info("Reconnect disabled due to invalid credentials")
            return

        # Jika disconnect tidak bersih, coba reconnect dengan backoff
        if rc != 0:
            log_info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
            threading.Timer(self.reconnect_delay, self._start_loop).start()
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    def _on_log(self, client, userdata, level, buf):
        """Callback untuk log internal paho-mqtt (optional)"""
        # Only log important messages (debug level 1)
        if level <= 1:  # MQTT_LOG_INFO
            log_mqtt("DEBUG", "paho", buf)
    
    def _start_loop(self):
        """Start MQTT loop in background thread"""
        # Jangan start jika kredensial tidak valid
        if self.status_auth == 'invalid_credentials':
            log_info("MQTT connection permanently stopped due to invalid credentials")
            return

        try:
            log_info(f"Connecting to MQTT broker {self.broker_url}:{self.broker_port}...")
            log_mqtt("CONNECTING", f"{self.broker_url}:{self.broker_port}", "Attempting to connect...")
            self.client.connect(self.broker_url, self.broker_port, self.keepalive)
            self.client.loop_start()
        except Exception as e:
            error_msg = str(e)
            log_error(f"Failed to start MQTT loop: {error_msg}")
            log_mqtt("ERROR", f"{self.broker_url}:{self.broker_port}", error_msg)

            # Reconnect hanya jika kredensial valid dan reconnect diaktifkan
            if self.status_auth != 'invalid_credentials' and self.reconnect_enabled:
                log_info(f"Retrying in {self.reconnect_delay} seconds...")
                threading.Timer(self.reconnect_delay, self._start_loop).start()
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    def subscribe(self, topic):
        """Subscribe ke topic MQTT"""
        if topic in self.subscribed_topics:
            log_info(f"Already subscribed to topic: {topic}")
            return
        
        if self.client and self.connected:
            self.client.subscribe(topic)
            log_success(f"Subscribed to topic: {topic}")
            log_mqtt("SUBSCRIBE", topic, "Subscription successful")
        else:
            log_warning(f"Cannot subscribe to {topic} - MQTT not connected, will retry on reconnect")
            log_mqtt("ERROR", topic, "Cannot subscribe - MQTT not connected")
        
        self.subscribed_topics.append(topic)
    
    def publish(self, topic, payload, qos=0, retain=False):
        """Publish message ke MQTT broker"""
        if self.client and self.connected:
            try:
                # Convert payload to string if it's dict
                if isinstance(payload, dict):
                    payload_str = json.dumps(payload)
                else:
                    payload_str = str(payload)
                
                # Log before publish
                log_mqtt("SEND", topic, payload_str)
                
                result = self.client.publish(topic, payload_str, qos=qos, retain=retain)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    log_success(f"Published to {topic}")
                    return True
                else:
                    error_msg = f"Error code: {result.rc}"
                    log_error(f"Failed to publish to {topic}: {error_msg}")
                    log_mqtt("ERROR", topic, error_msg)
                    return False
            except Exception as e:
                error_msg = str(e)
                log_error(f"Error publishing message: {error_msg}")
                log_mqtt("ERROR", topic, error_msg)
                return False
        else:
            error_msg = "MQTT client not connected"
            log_warning(f"Cannot publish to {topic}: {error_msg}")
            log_mqtt("ERROR", topic, error_msg)
            return False
    
    def stop(self):
        """Stop MQTT client"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            log_info("MQTT client stopped")
            log_mqtt("DISCONNECT", f"{self.broker_url}:{self.broker_port}", "Client stopped")
    
    def is_connected(self):
        """Check if MQTT client is connected"""
        return self.connected


# Global instance
mqtt_client = MQTTClient()