"""
File        : websocket_service.py
Author      : Keyfin Agustio Suratman
Description : WebSocketIO service untuk real-time communication dengan dashboard
              Terintegrasi dengan MQTT untuk broadcast data sensor
Created     : 2026-03-20
Updated     : 2026-03-23
"""

import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from flask import request
from flask_login import current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

from apps.utils import (
    log_info,
    log_success,
    log_warning,
    log_error,
    log_websocket,
)


class WebSocketService:
    """
    WebSocket Service untuk real-time communication.
    
    Service ini menangani semua koneksi WebSocket real-time antara server dan client,
    termasuk room management, broadcasting, dan komunikasi bi-directional.
    Terintegrasi dengan MQTT untuk menerima dan mengirim data sensor.
    
    Attributes:
        socketio (SocketIO): Instance SocketIO untuk komunikasi real-time
        connected_clients (dict): Dictionary menyimpan informasi client yang terhubung
        rooms (dict): Dictionary menyimpan mapping client ke rooms yang diikuti
        simulation_running (bool): Flag untuk status simulasi data
        mqtt_client (MQTTClient): Reference ke MQTT client
    """

    def __init__(self, app=None):
        """
        Inisialisasi WebSocket Service.
        
        Args:
            app: Flask application instance (optional)
        """
        self.socketio: Optional[SocketIO] = None
        self.connected_clients: Dict[str, dict] = {}
        self.rooms: Dict[str, List[str]] = {}
        self.simulation_running: bool = False
        self.mqtt_client = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Inisialisasi SocketIO dengan Flask app.
        
        Args:
            app: Flask application instance
        """
        cors_allowed = app.config.get("SOCKETIO_CORS_ALLOWED", "*")

        self.socketio = SocketIO(
            app,
            cors_allowed_origins=cors_allowed,
            async_mode="threading",
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=10e6,  # 10MB
        )

        self._register_handlers()
        app.websocket_service = self

        log_success("WebSocketIO Service initialized")

    def set_mqtt_client(self, mqtt_client):
        """
        Set MQTT client reference untuk integrasi.
        
        Args:
            mqtt_client: Instance MQTT client
        """
        self.mqtt_client = mqtt_client
        log_success("MQTT Client linked to WebSocket Service")

    # ==================== PRIVATE HELPER METHODS ====================
    
    def _get_username(self) -> str:
        """
        Mendapatkan username dari user yang sedang login.
        
        Returns:
            str: Username atau 'anonymous' jika tidak login
        """
        if current_user.is_authenticated:
            return getattr(current_user, "username", "unknown")
        return "anonymous"

    def _require_auth(self) -> bool:
        """
        Memeriksa apakah user sudah login.
        
        Jika belum login, akan disconnect dan mencatat warning.
        
        Returns:
            bool: True jika terautentikasi, False jika tidak
        """
        if not current_user.is_authenticated:
            log_warning(f"UNAUTHORIZED EVENT - SID: {request.sid}")
            disconnect()
            return False
        return True

    def _log_client_event(self, action: str, client_id: str, details: str = ""):
        """
        Helper untuk mencatat log event client dengan informasi username.
        
        Args:
            action: Tipe aksi (CONNECT, DISCONNECT, JOIN, dll)
            client_id: Socket ID client
            details: Detail tambahan untuk log
        """
        username = self._get_username()
        prefix = f"User: {username}"
        if details:
            details = f"{prefix} | {details}"
        else:   
            details = prefix
        log_websocket(action, client_id, details)

    def _register_handlers(self):
        """Register semua event handlers untuk SocketIO."""
        
        @self.socketio.on("connect")
        def handle_connect():
            """Handle koneksi client baru."""
            if not current_user.is_authenticated:
                log_warning(f"UNAUTHORIZED CONNECT ATTEMPT - IP: {request.remote_addr}")
                return False

            client_id = request.sid
            username = self._get_username()

            self.connected_clients[client_id] = {
                "username": username,
                "user_id": current_user.get_id(),
                "connected_at": datetime.now().isoformat(),
                "ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", "Unknown"),
            }

            self._log_client_event("CONNECT", client_id, f"IP: {request.remote_addr}")

            emit(
                "connected",
                {
                    "status": "connected",
                    "client_id": client_id,
                    "username": username,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        @self.socketio.on("disconnect")
        def handle_disconnect():
            """Handle disconnection client."""
            client_id = request.sid
            username = self.connected_clients.get(client_id, {}).get("username", "Unknown")

            # Leave all rooms
            if client_id in self.rooms:
                for room in list(self.rooms[client_id]):
                    leave_room(room)
                del self.rooms[client_id]

            # Remove from connected clients
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]

            log_websocket("DISCONNECT", client_id, f"User: {username}")

        @self.socketio.on("join")
        def handle_join(data):
            """
            Handle request client untuk join room.
            
            Event data format:
            {
                "room": "room_name"
            }
            """
            if not self._require_auth():
                return

            client_id = request.sid
            username = self._get_username()
            data = data or {}
            room = data.get("room")

            if not room:
                self._send_error(client_id, "Room tidak boleh kosong")
                return

            join_room(room)

            self.rooms.setdefault(client_id, [])
            if room not in self.rooms[client_id]:
                self.rooms[client_id].append(room)

            self._log_client_event("JOIN", client_id, f"Room: {room}")

            # Confirm to client
            emit(
                "joined",
                {
                    "room": room,
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                },
                room=client_id,
            )

            # Notify room members
            emit(
                "user_joined",
                {
                    "user_id": client_id,
                    "username": username,
                    "room": room,
                    "timestamp": datetime.now().isoformat(),
                },
                room=room,
                include_self=False,
            )

        @self.socketio.on("leave")
        def handle_leave(data):
            """
            Handle request client untuk leave room.
            
            Event data format:
            {
                "room": "room_name"
            }
            """
            if not self._require_auth():
                return

            client_id = request.sid
            username = self._get_username()
            data = data or {}
            room = data.get("room")

            if not room:
                self._send_error(client_id, "Room tidak boleh kosong")
                return

            leave_room(room)

            if client_id in self.rooms and room in self.rooms[client_id]:
                self.rooms[client_id].remove(room)

            self._log_client_event("LEAVE", client_id, f"Room: {room}")

            # Confirm to client
            emit(
                "left",
                {
                    "room": room,
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                },
                room=client_id,
            )

            # Notify room members
            emit(
                "user_left",
                {
                    "user_id": client_id,
                    "username": username,
                    "room": room,
                    "timestamp": datetime.now().isoformat(),
                },
                room=room,
                include_self=False,
            )

        @self.socketio.on("message")
        def handle_message(data):
            """
            Handle incoming message dari client.
            
            Event data format:
            {
                "type": "sensor_request | actuator_command | ping | mqtt_publish",
                "content": {...}
            }
            """
            if not self._require_auth():
                return

            client_id = request.sid
            username = self._get_username()
            data = data or {}

            message_type = data.get("type", "unknown")
            content = data.get("content", {})

            self._log_client_event("MESSAGE", client_id, f"Type: {message_type}")

            # Route message based on type
            handlers = {
                "sensor_request": self._handle_sensor_request,
                "actuator_command": self._handle_actuator_command,
                "ping": self._handle_ping,
                "mqtt_publish": self._handle_mqtt_publish,
                "mqtt_subscribe": self._handle_mqtt_subscribe,
            }
            
            handler = handlers.get(message_type)
            if handler:
                handler(client_id, content)
            else:
                self._handle_unknown_message(client_id, message_type)

        @self.socketio.on("notification")
        def handle_notification(data):
            """
            Handle incoming notification dari client.
            
            Event data format:
            {
                "message": "notification text",
                "type": "info | success | warning | error"
            }
            """
            if not self._require_auth():
                return

            client_id = request.sid
            username = self._get_username()
            data = data or {}

            self._log_client_event("NOTIFICATION", client_id, f"{str(data)[:100]}")

            message = data.get("message", "No message")
            notif_type = data.get("type", "info")

            # Broadcast notification to all clients
            self.send_notification(message, notif_type)

        @self.socketio.on("error")
        def handle_error(error):
            """Handle socket error."""
            client_id = request.sid
            username = self._get_username()
            log_error(f"WebSocket Error - Client: {client_id}, User: {username}, Error: {str(error)}")

    # ==================== MESSAGE HANDLERS ====================
    
    def _send_error(self, client_id: str, message: str):
        """
        Mengirim pesan error ke client tertentu.
        
        Args:
            client_id: Socket ID client target
            message: Pesan error
        """
        emit(
            "error",
            {
                "message": message,
                "timestamp": datetime.now().isoformat(),
            },
            room=client_id,
        )

    def _handle_sensor_request(self, client_id: str, content: dict):
        """
        Handle request data sensor dari client.
        Mengambil data terbaru dari MQTT cache atau database.
        
        Args:
            client_id: Socket ID client
            content: Dictionary berisi device_id dan sensor_type
        """
        content = content or {}
        sensor_type = content.get("sensor_type")
        
        # Get data from MQTT service
        try:
            from apps.services.mqtt_service import get_latest_sensor_data
            
            latest_data = get_latest_sensor_data()
            
            if sensor_type and sensor_type in latest_data:
                data = latest_data[sensor_type]
            else:
                data = latest_data
            
            emit(
                "sensor_data",
                {
                    "sensor_type": sensor_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                },
                room=client_id,
            )
        except Exception as e:
            log_error(f"Error handling sensor request: {e}")
            self._send_error(client_id, f"Failed to get sensor data: {str(e)}")

    def _handle_actuator_command(self, client_id: str, content: dict):
        """
        Handle command actuator dari client.
        Mengirim command via MQTT.
        
        Args:
            client_id: Socket ID client
            content: Dictionary berisi device_id, actuator, dan command
        """
        content = content or {}
        topic = content.get("topic")
        command = content.get("command")
        value = content.get("value")
        
        if not topic or not command:
            self._send_error(client_id, "Topic and command are required")
            return
        
        # Publish via MQTT
        if self.mqtt_client:
            from apps.services.mqtt_service import publish_command
            
            success = publish_command(topic, command, value)
            
            emit(
                "command_ack",
                {
                    "topic": topic,
                    "command": command,
                    "value": value,
                    "status": "executed" if success else "failed",
                    "timestamp": datetime.now().isoformat(),
                },
                room=client_id,
            )
        else:
            self._send_error(client_id, "MQTT client not available")

    def _handle_ping(self, client_id: str, content: dict):
        """
        Handle ping request dari client.
        
        Args:
            client_id: Socket ID client
            content: Dictionary (tidak digunakan)
        """
        emit(
            "pong",
            {
                "timestamp": datetime.now().isoformat(),
            },
            room=client_id,
        )
    
    def _handle_mqtt_publish(self, client_id: str, content: dict):
        """
        Handle MQTT publish request dari client.
        
        Args:
            client_id: Socket ID client
            content: Dictionary berisi topic dan payload
        """
        content = content or {}
        topic = content.get("topic")
        payload = content.get("payload")
        
        if not topic or not payload:
            self._send_error(client_id, "Topic and payload are required")
            return
        
        if self.mqtt_client:
            success = self.mqtt_client.publish(topic, payload)
            
            emit(
                "mqtt_publish_ack",
                {
                    "topic": topic,
                    "status": "published" if success else "failed",
                    "timestamp": datetime.now().isoformat(),
                },
                room=client_id,
            )
        else:
            self._send_error(client_id, "MQTT client not available")
    
    def _handle_mqtt_subscribe(self, client_id: str, content: dict):
        """
        Handle MQTT subscribe request dari client.
        
        Args:
            client_id: Socket ID client
            content: Dictionary berisi topics list
        """
        content = content or {}
        topics = content.get("topics", [])
        
        if not topics:
            self._send_error(client_id, "Topics list is required")
            return
        
        if self.mqtt_client:
            for topic in topics:
                self.mqtt_client.subscribe(topic)
            
            emit(
                "mqtt_subscribe_ack",
                {
                    "topics": topics,
                    "status": "subscribed",
                    "timestamp": datetime.now().isoformat(),
                },
                room=client_id,
            )
        else:
            self._send_error(client_id, "MQTT client not available")

    def _handle_unknown_message(self, client_id: str, message_type: str):
        """
        Handle unknown message type.
        
        Args:
            client_id: Socket ID client
            message_type: Tipe message yang tidak dikenal
        """
        emit(
            "message_received",
            {
                "type": message_type,
                "status": "received",
                "timestamp": datetime.now().isoformat(),
            },
            room=client_id,
        )

    # ==================== PUBLIC EMIT METHODS ====================
    
    def emit_to_all(self, event: str, data: dict):
        """
        Emit event ke semua connected clients.
        
        Args:
            event: Nama event yang akan diemit
            data: Data yang akan dikirim
        """
        if self.socketio:
            self.socketio.emit(event, data)
            log_websocket("EMIT-ALL", "SERVER", f"Event: {event} | Data: {str(data)[:100]}")

    def emit_to_room(self, room: str, event: str, data: dict):
        """
        Emit event ke semua clients dalam room tertentu.
        
        Args:
            room: Nama room target
            event: Nama event yang akan diemit
            data: Data yang akan dikirim
        """
        if self.socketio:
            self.socketio.emit(event, data, room=room)
            log_websocket("EMIT-ROOM", room, f"Event: {event} | Data: {str(data)[:100]}")

    def emit_to_client(self, client_id: str, event: str, data: dict):
        """
        Emit event ke specific client berdasarkan socket ID.
        
        Args:
            client_id: Socket ID client target
            event: Nama event yang akan diemit
            data: Data yang akan dikirim
        """
        if self.socketio:
            self.socketio.emit(event, data, room=client_id)
            log_websocket("EMIT-CLIENT", client_id, f"Event: {event} | Data: {str(data)[:100]}")

    # ==================== PUBLIC BROADCAST METHODS ====================
    
    def broadcast_sensor_data(self, device_id: str, sensor_type: str, value: float, unit: str = None):
        """
        Broadcast data sensor ke semua clients.
        
        Args:
            device_id: ID perangkat sensor
            sensor_type: Tipe sensor (ph, tds, suhu, kelembapan)
            value: Nilai pembacaan sensor
            unit: Satuan nilai (optional)
        """
        data = {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_to_all("sensor_update", data)

    def broadcast_actuator_status(self, device_id: str, actuator: str, status: str):
        """
        Broadcast status actuator ke semua clients.
        
        Args:
            device_id: ID perangkat actuator
            actuator: Nama actuator (lampu, pompa, dll)
            status: Status actuator (on/off)
        """
        data = {
            "device_id": device_id,
            "actuator": actuator,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_to_all("actuator_update", data)

    # ==================== MQTT INTEGRATION ====================
    
    def on_mqtt_message_received(self, topic: str, payload: dict):
        """
        Callback ketika MQTT menerima message.
        Broadcast ke WebSocket clients.
        
        Args:
            topic: Topik MQTT
            payload: Payload data sensor
        """
        # Extract sensor type from topic
        sensor_type = None
        if 'temperature' in topic:
            sensor_type = 'temperature'
        elif 'humidity' in topic:
            sensor_type = 'humidity'
        elif 'pressure' in topic:
            sensor_type = 'pressure'
        elif 'ph' in topic:
            sensor_type = 'ph'
        elif 'tds' in topic:
            sensor_type = 'tds'
        
        # Get value
        value = payload.get('value') or payload.get(sensor_type)
        unit = payload.get('unit')
        
        if sensor_type and value:
            # Broadcast to all WebSocket clients
            self.broadcast_sensor_data(
                device_id="mqtt_device",
                sensor_type=sensor_type,
                value=float(value),
                unit=unit
            )
            
            log_success(f"MQTT data broadcasted via WebSocket: {sensor_type}={value}")

    # ==================== NOTIFICATION METHODS ====================
    
    def send_notification(self, message: str, notification_type: str = "info", target: Union[str, List[str]] = None):
        """
        Send notification ke client(s).
        
        Args:
            message: Pesan notifikasi
            notification_type: Tipe notifikasi (info, success, warning, error)
            target: Target pengiriman:
                - None: Broadcast ke semua client
                - str: Client ID atau "room:room_name"
                - List[str]: List client IDs
        """
        data = {
            "type": notification_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        if target:
            if isinstance(target, str):
                if target.startswith("room:"):
                    room = target[5:]
                    self.emit_to_room(room, "notification", data)
                else:
                    self.emit_to_client(target, "notification", data)
            elif isinstance(target, list):
                for client_id in target:
                    self.emit_to_client(client_id, "notification", data)
        else:
            self.emit_to_all("notification", data)
            log_success(f"Notification broadcasted: {message}")

    # ==================== UTILITY METHODS ====================
    
    def get_stats(self) -> dict:
        """
        Mendapatkan statistik WebSocket.
        
        Returns:
            dict: Statistik koneksi WebSocket
        """
        return {
            "connected_clients": len(self.connected_clients),
            "clients": self.connected_clients,
            "rooms": self.rooms,
        }

    # ==================== SIMULATION METHODS ====================
    
    def _random_data_generator(self):
        """
        Generator data random yang smooth untuk simulasi.
        
        Yields:
            dict: Data sensor dengan nilai yang berubah secara gradual
        """
        sensor_types = ["ph", "tds", "suhu", "kelembapan"]

        last_values = {
            "ph": 6.8,
            "tds": 800,
            "suhu": 28.0,
            "kelembapan": 70,
        }

        index = 0

        while self.simulation_running:
            sensor_type = sensor_types[index % len(sensor_types)]
            prev = last_values[sensor_type]

            # Generate value with delta based on sensor type
            if sensor_type == "ph":
                delta = random.uniform(-0.2, 0.2)
                value = round(prev + delta, 1)
                value = max(5.5, min(8.0, value))
                unit = ""

            elif sensor_type == "tds":
                delta = random.randint(-20, 20)
                value = prev + delta
                value = max(500, min(1200, value))
                unit = "ppm"

            elif sensor_type == "suhu":
                delta = random.uniform(-0.5, 0.5)
                value = round(prev + delta, 1)
                value = max(18, min(40, value))
                unit = "°C"

            else:  # kelembapan
                delta = random.randint(-3, 3)
                value = prev + delta
                value = max(40, min(100, value))
                unit = "%"

            last_values[sensor_type] = value

            yield {
                "device_id": "simulator",
                "sensor_type": sensor_type,
                "value": value,
                "unit": unit,
                "timestamp": datetime.now().isoformat(),
            }

            index += 1
            time.sleep(1)

    def start_simulation(self):
        """
        Memulai simulasi data random.
        
        Simulasi akan mengirim data sensor secara periodik ke semua client.
        Data yang dikirim adalah nilai yang berubah secara gradual.
        """
        if self.simulation_running:
            log_warning("Simulasi sudah berjalan")
            return

        self.simulation_running = True
        log_info("Memulai simulasi data random...")

        def task():
            for data in self._random_data_generator():
                if not self.simulation_running:
                    break

                if self.connected_clients:
                    self.socketio.emit("sensor_update", data)
                else:
                    time.sleep(5)

        self.socketio.start_background_task(task)

    def stop_simulation(self):
        """
        Menghentikan simulasi data random.
        """
        if not self.simulation_running:
            return

        self.simulation_running = False
        log_info("Simulasi data random dihentikan")


# ==================== SINGLETON INSTANCE ====================

# Singleton instance untuk digunakan di seluruh aplikasi
websocket_service = WebSocketService()