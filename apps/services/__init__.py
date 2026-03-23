"""
File        : __init__.py
Author      : Keyfin Agustio Suratman
Description : Inisialisasi semua services untuk IoT Hidroponik
Created     : 2026-03-20
"""

from datetime import datetime
from apps.utils import log_info, log_success, log_warning

from apps.services.websocket_service import websocket_service, WebSocketService

def init_services(app):
    """Initialize all services except MQTT (already done separately)"""
    log_info("Initializing services...")
    
    # Initialize WebSocket service
    from apps.services.websocket_service import websocket_service
    websocket_service.init_app(app)
    
    # Debug: cek nilai ENABLE_SIMULATION
    sim_enabled = app.config.get('ENABLE_SIMULATION', False)
    log_info(f"ENABLE_SIMULATION = {sim_enabled} (type: {type(sim_enabled)})")
    
    # Optional: start simulation if enabled
    if sim_enabled:
        websocket_service.start_simulation()
        log_info("Simulasi data random via WebSocket dimulai")
    else:
        log_info("Simulasi data random TIDAK dimulai")
    
    log_success("All services initialized")
    print()


__all__ = [
    'init_services',
    'websocket_service',
    'WebSocketService'
]