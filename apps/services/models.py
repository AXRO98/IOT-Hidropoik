"""
Module      : apps.models.sensor_models
Author      : Keyfin Suratman
Description : Fungsi model untuk menyimpan dan mengelola data sensor
"""

import sqlite3
from flask import current_app
from datetime import datetime
import json
from typing import List, Dict, Any, Optional
from apps.models import connect_db


# ==========================
# TABLE INITIALIZATION
# ==========================
def init_sensor_tables():
    """
    Inisialisasi tabel-tabel yang diperlukan untuk menyimpan data sensor
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Tabel untuk menyimpan data sensor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            topic TEXT,
            raw_data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel untuk menyimpan data sensor perangkat (multiple sensors in one device)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            sensor_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel untuk menyimpan data sensor terbaru (cache)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS latest_sensor_data (
            sensor_type TEXT PRIMARY KEY,
            value REAL NOT NULL,
            unit TEXT,
            topic TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel untuk menyimpan history alert
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_type TEXT NOT NULL,
            value REAL NOT NULL,
            alert_type TEXT,
            alert_message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


# ==========================
# SENSOR DATA OPERATIONS
# ==========================
class SensorDataModel:
    """Model untuk operasi data sensor"""
    
    @staticmethod
    def save_sensor_data(sensor_type: str, value: float, unit: str = None, 
                        topic: str = None, raw_data: Dict = None) -> int:
        """
        Menyimpan data sensor ke database
        
        Args:
            sensor_type: Tipe sensor (temperature, humidity, pressure, dll)
            value: Nilai sensor
            unit: Satuan (optional)
            topic: Topik MQTT (optional)
            raw_data: Data mentah dari MQTT (optional)
            
        Returns:
            int: ID dari data yang disimpan
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        # Konversi raw_data ke JSON string
        raw_data_json = json.dumps(raw_data) if raw_data else None
        
        cursor.execute('''
            INSERT INTO sensor_data (sensor_type, value, unit, topic, raw_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (sensor_type, value, unit, topic, raw_data_json))
        
        sensor_id = cursor.lastrowid
        
        # Update latest data
        cursor.execute('''
            INSERT OR REPLACE INTO latest_sensor_data (sensor_type, value, unit, topic, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (sensor_type, value, unit, topic, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return sensor_id
    
    @staticmethod
    def save_device_sensor_data(device_id: str, sensor_type: str, 
                                value: float, unit: str = None) -> int:
        """
        Menyimpan data sensor perangkat
        
        Args:
            device_id: ID perangkat
            sensor_type: Tipe sensor
            value: Nilai sensor
            unit: Satuan
            
        Returns:
            int: ID dari data yang disimpan
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_sensor_data (device_id, sensor_type, value, unit)
            VALUES (?, ?, ?, ?)
        ''', (device_id, sensor_type, value, unit))
        
        sensor_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return sensor_id
    
    @staticmethod
    def get_latest_sensor_data(sensor_type: str = None) -> Dict[str, Any]:
        """
        Mendapatkan data sensor terbaru
        
        Args:
            sensor_type: Tipe sensor (optional, jika None maka semua sensor)
            
        Returns:
            Dict: Data sensor terbaru
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        if sensor_type:
            cursor.execute('''
                SELECT sensor_type, value, unit, topic, updated_at
                FROM latest_sensor_data
                WHERE sensor_type = ?
            ''', (sensor_type,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
        else:
            cursor.execute('''
                SELECT sensor_type, value, unit, topic, updated_at
                FROM latest_sensor_data
                ORDER BY updated_at DESC
            ''')
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
    
    @staticmethod
    def get_sensor_history(sensor_type: str = None, limit: int = 100, 
                          start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Mendapatkan history data sensor
        
        Args:
            sensor_type: Tipe sensor (optional)
            limit: Batas jumlah data
            start_date: Tanggal mulai (format: YYYY-MM-DD)
            end_date: Tanggal akhir (format: YYYY-MM-DD)
            
        Returns:
            List[Dict]: List history data sensor
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, sensor_type, value, unit, topic, timestamp, created_at
            FROM sensor_data
            WHERE 1=1
        '''
        params = []
        
        if sensor_type:
            query += " AND sensor_type = ?"
            params.append(sensor_type)
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    @staticmethod
    def get_sensor_statistics(sensor_type: str, start_date: str = None, 
                             end_date: str = None) -> Dict[str, Any]:
        """
        Mendapatkan statistik data sensor
        
        Args:
            sensor_type: Tipe sensor
            start_date: Tanggal mulai
            end_date: Tanggal akhir
            
        Returns:
            Dict: Statistik (min, max, avg, count)
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                MIN(value) as min_value,
                MAX(value) as max_value,
                AVG(value) as avg_value,
                COUNT(*) as total_count,
                unit
            FROM sensor_data
            WHERE sensor_type = ?
        '''
        params = [sensor_type]
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None




# ==========================
# BULK OPERATIONS
# ==========================
class SensorBulkOperations:
    """Operasi bulk untuk data sensor"""
    
    @staticmethod
    def save_multiple_sensors(sensors_data: List[Dict]) -> List[int]:
        """
        Menyimpan multiple data sensor sekaligus
        
        Args:
            sensors_data: List dictionary data sensor
            
        Returns:
            List[int]: List ID yang tersimpan
        """
        saved_ids = []
        
        for sensor in sensors_data:
            sensor_id = SensorDataModel.save_sensor_data(
                sensor_type=sensor.get('sensor_type'),
                value=sensor.get('value'),
                unit=sensor.get('unit'),
                topic=sensor.get('topic'),
                raw_data=sensor.get('raw_data')
            )
            saved_ids.append(sensor_id)
        
        return saved_ids
    
    @staticmethod
    def cleanup_old_data(days: int = 30) -> int:
        """
        Membersihkan data lama
        
        Args:
            days: Jumlah hari data yang disimpan
            
        Returns:
            int: Jumlah data yang dihapus
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM sensor_data
            WHERE datetime(timestamp) < datetime('now', ?)
        ''', (f'-{days} days',))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count


# ==========================
# DEVICE SPECIFIC OPERATIONS
# ==========================
class DeviceSensorModel:
    """Model untuk data sensor per device"""
    
    @staticmethod
    def get_device_latest_data(device_id: str) -> List[Dict]:
        """
        Mendapatkan data terbaru untuk suatu device
        
        Args:
            device_id: ID device
            
        Returns:
            List[Dict]: List data sensor device
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_id, sensor_type, value, unit, timestamp
            FROM device_sensor_data
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (device_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    @staticmethod
    def get_device_sensor_history(device_id: str, sensor_type: str = None, 
                                  limit: int = 100) -> List[Dict]:
        """
        Mendapatkan history sensor untuk device
        
        Args:
            device_id: ID device
            sensor_type: Tipe sensor (optional)
            limit: Batas jumlah data
            
        Returns:
            List[Dict]: List history sensor
        """
        conn = connect_db()
        cursor = conn.cursor()
        
        query = '''
            SELECT device_id, sensor_type, value, unit, timestamp
            FROM device_sensor_data
            WHERE device_id = ?
        '''
        params = [device_id]
        
        if sensor_type:
            query += " AND sensor_type = ?"
            params.append(sensor_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]