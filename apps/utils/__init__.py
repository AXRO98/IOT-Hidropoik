"""
File        : __init__.py
Author      : Keyfin Agustio Suratman
Description : Utility functions for IoT Hidroponik
Created     : 2026-03-16
Updated     : 2026-03-23
"""

import sys
from datetime import datetime
from colorama import init, Fore, Back, Style

# Import fungsi-fungsi yang sudah ada
from .logger import (
    log_request,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_server_event,
    print_startup_banner
)

# Initialize Colorama
init(autoreset=True)

def log_mqtt(direction, topic, message=""):
    """Log MQTT messages with custom formatting"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Map directions to Colorama colors
    colors = {
        'CONNECTING': Fore.GREEN,
        'CONNECTED': Fore.GREEN,
        'DISCONNECT': Fore.RED,
        'SEND': Fore.BLUE,
        'RECV': Fore.GREEN,
        'PUB-ACK': Fore.YELLOW,
        'ERROR': Fore.RED,
        'RESET': Style.RESET_ALL
    }
    
    color = colors.get(direction, Style.RESET_ALL)
    direction_str = f"[MQTT-{direction}]"
    
    # Truncate long messages
    if len(message) > 200:
        message = message[:200] + "..."
    
    print(f"{Fore.WHITE}[{timestamp}] {color}{direction_str:<15} {topic:<30} {message}{Style.RESET_ALL}")
    sys.stdout.flush()  # Force flush untuk real-time logging

def log_websocket(action, client_id, details="", username=None):
    """Log WebSocket messages with Colorama"""
    timestamp = datetime.now().strftime("%H:%M:%S")

    colors = {
        'CONNECT': Fore.GREEN,
        'DISCONNECT': Fore.RED,
        'JOIN': Fore.BLUE,
        'LEAVE': Fore.YELLOW,
        'MESSAGE': Fore.MAGENTA,
        'EMIT-ALL': Fore.CYAN,
        'EMIT-ROOM': Fore.CYAN,
        'EMIT-CLIENT': Fore.CYAN,
        'RESET': Style.RESET_ALL
    }
    
    color = colors.get(action, Style.RESET_ALL)
    action_str = f"[SOCKET-{action}]"

    client_short = client_id
    user_str = f"[{username}]" if username else ""

    print(f"{Fore.WHITE}[{timestamp}] {color}{action_str:<15} {client_short:<15} {user_str} {details}{Style.RESET_ALL}")
    sys.stdout.flush()


# Export semua fungsi
__all__ = [
    'log_request',
    'log_info',
    'log_success',
    'log_warning',
    'log_error',
    'log_server_event',
    'print_startup_banner',
    'log_mqtt',
    'log_websocket'
]