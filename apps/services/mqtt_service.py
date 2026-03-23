"""
Module      : apps.services.mqtt_service
Author      : Keyfin Suratman
Description : Service untuk mengelola data sensor dari MQTT
Created     : 2026-03-23
Updated     : 2026-03-24
"""

import json
from datetime import datetime
from typing import Dict, Any

# Perbaiki import model
from apps.services.models import SensorDataModel
from apps.utils import log_mqtt, log_info, log_success, log_warning, log_error

# Dictionary untuk menyimpan data sensor terbaru (in-memory cache)
sensor_data_cache = {
    'temperature': None,
    'humidity': None,
    'pressure': None,
    'ph': None,
    'tds': None,
    'water_level': None,
    'last_update': None,
    'all_sensors': {}
}

def process_sensor_data(topic, data):

    """
    Proses data sensor yang diterima dari MQTT
    """
    try:
        # Extract sensor type from topic
        sensor_type = extract_sensor_type(topic)
        
        # Get value from data
        value = data.get('value') or data.get(sensor_type)
        
        if value and sensor_type:
            # Save to database
            sensor_id = SensorDataModel.save_sensor_data(
                sensor_type=sensor_type,
                value=float(value),
                unit=data.get('unit'),
                topic=topic,
                raw_data=data
            )
            
            log_success(f"Sensor data saved to DB [ID: {sensor_id}] - {sensor_type}: {value} {data.get('unit', get_default_unit(sensor_type))}")
            log_mqtt("PROCESS", topic, f"Saved to DB: {sensor_type}={value}")
            
            # Broadcast via WebSocket
            try:
                from apps.services.websocket_service import websocket_service
                # Pastikan websocket_service sudah diinisialisasi
                if websocket_service and websocket_service.socketio:
                    websocket_service.on_mqtt_message_received(topic, data)
                    log_mqtt("BROADCAST", topic, "Data sent to WebSocket clients")
                else:
                    log_warning("WebSocket service not ready, broadcast skipped")
            except Exception as e:
                log_error(f"Failed to broadcast to WebSocket: {e}")
        
        # Store in cache
        sensor_data_cache['last_update'] = datetime.now()
        
        if sensor_type:
            sensor_data_cache[sensor_type] = {
                'value': value,
                'unit': data.get('unit', get_default_unit(sensor_type)),
                'timestamp': datetime.now().isoformat(),
                'raw_data': data
            }
        
        sensor_data_cache['all_sensors'][datetime.now().isoformat()] = {
            'topic': topic,
            'data': data,
            'sensor_type': sensor_type
        }
        
        # Keep only last 100 records in cache
        if len(sensor_data_cache['all_sensors']) > 100:
            oldest_key = min(sensor_data_cache['all_sensors'].keys())
            del sensor_data_cache['all_sensors'][oldest_key]
        
        log_info(f"Processed MQTT data: {sensor_type} = {value} (from topic: {topic})")
        
    except Exception as e:
        error_msg = str(e)
        log_error(f"Error processing sensor data: {error_msg}")
        log_mqtt("ERROR", topic, f"Processing error: {error_msg}")

def extract_sensor_type(topic: str) -> str:
    """Extract sensor type from MQTT topic"""
    if 'temperature' in topic:
        return 'temperature'
    elif 'humidity' in topic:
        return 'humidity'
    elif 'pressure' in topic:
        return 'pressure'
    elif 'ph' in topic or 'pH' in topic:
        return 'ph'
    elif 'tds' in topic or 'ppm' in topic:
        return 'tds'
    elif 'water' in topic or 'level' in topic:
        return 'water_level'
    else:
        # Try to extract from topic parts
        parts = topic.split('/')
        if len(parts) >= 2:
            return parts[-1]  # Last part as sensor type
        return 'unknown'

def get_default_unit(sensor_type: str) -> str:
    """Get default unit for sensor type"""
    units = {
        'temperature': '°C',
        'humidity': '%',
        'pressure': 'hPa',
        'ph': 'pH',
        'tds': 'ppm',
        'water_level': 'cm',
        'unknown': ''
    }
    return units.get(sensor_type, '')

def get_latest_sensor_data() -> Dict[str, Any]:
    """Get latest sensor data from cache"""
    return {
        'temperature': sensor_data_cache.get('temperature'),
        'humidity': sensor_data_cache.get('humidity'),
        'pressure': sensor_data_cache.get('pressure'),
        'ph': sensor_data_cache.get('ph'),
        'tds': sensor_data_cache.get('tds'),
        'water_level': sensor_data_cache.get('water_level'),
        'last_update': sensor_data_cache.get('last_update'),
        'status': 'active' if sensor_data_cache['last_update'] else 'no_data'
    }

def get_sensor_history(limit: int = 50) -> list:
    """Get sensor history from cache"""
    history = []
    for timestamp, data in sorted(sensor_data_cache['all_sensors'].items(), reverse=True)[:limit]:
        history.append({
            'timestamp': timestamp,
            **data
        })
    return history

def publish_command(topic: str, command: str, value: Any = None):
    """
    Publish command to MQTT broker
    
    Args:
        topic: Target topic
        command: Command name
        value: Command value
        
    Returns:
        bool: True jika publish berhasil
    """
    from apps.services.mqtt_client import mqtt_client
    
    payload = {
        'command': command,
        'value': value,
        'timestamp': datetime.now().isoformat()
    }
    
    log_mqtt("SEND", topic, f"Command: {command}={value}")
    
    success = mqtt_client.publish(topic, payload)
    
    if success:
        log_success(f"Command published: {command}={value} to topic {topic}")
        log_mqtt("PUB-ACK", topic, f"Command sent successfully")
    else:
        log_error(f"Failed to publish command to topic {topic}")
        log_mqtt("ERROR", topic, f"Failed to send command: {command}")
    
    return success

def clear_sensor_cache():
    """Clear sensor data cache"""
    sensor_data_cache['temperature'] = None
    sensor_data_cache['humidity'] = None
    sensor_data_cache['pressure'] = None
    sensor_data_cache['ph'] = None
    sensor_data_cache['tds'] = None
    sensor_data_cache['water_level'] = None
    sensor_data_cache['last_update'] = None
    sensor_data_cache['all_sensors'] = {}
    log_info("Sensor cache cleared")
    log_mqtt("CLEAR", "cache", "Sensor cache cleared")