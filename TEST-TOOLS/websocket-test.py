#!/usr/bin/env python3
"""
File        : socketio_tester.py
Author      : Keyfin Agustio Suratman
Description : Socket.IO Tester untuk IoT Hidroponik (menggunakan python-socketio)
Created     : 2026-03-23
Modified    : 2026-03-23 (Added authentication support - direct cookie & login)
"""

import sys
import json
import time
import threading
import argparse
from datetime import datetime
from urllib.parse import urlparse

try:
    import socketio
    import requests
    from colorama import init, Fore, Style
    init()
except ImportError:
    print("Please install required packages:")
    print("pip install python-socketio[client] colorama requests")
    sys.exit(1)


class SocketIOTester:
    """Socket.IO Tester dengan fitur interaktif dan autentikasi"""

    def __init__(self, url: str, verbose: bool = True, cookies: dict = None):
        """
        Inisialisasi Socket.IO Tester.
        
        Args:
            url: Socket.IO server URL
            verbose: Enable verbose output
            cookies: Session cookies untuk autentikasi
        """
        self.url = url
        self.verbose = verbose
        self.cookies = cookies or {}
        
        # SocketIO client
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False
        )
        self.connected = False
        self.running = True
        self.stats = {
            'messages_received': 0,
            'messages_sent': 0,
            'connection_time': None
        }
        self.latest_data = {}

        # Register event handlers
        self._register_handlers()

    def _log(self, msg: str, level: str = 'info'):
        """Log message dengan warna."""
        if not self.verbose:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == 'success':
            print(f"{Fore.GREEN}[{timestamp}] ✓ {msg}{Style.RESET_ALL}")
        elif level == 'error':
            print(f"{Fore.RED}[{timestamp}] ✗ {msg}{Style.RESET_ALL}")
        elif level == 'warning':
            print(f"{Fore.YELLOW}[{timestamp}] ⚠ {msg}{Style.RESET_ALL}")
        elif level == 'notification':
            print(f"{Fore.MAGENTA}[{timestamp}] 🔔 {msg}{Style.RESET_ALL}")
        elif level == 'sensor':
            print(f"{Fore.BLUE}[{timestamp}] 📊 {msg}{Style.RESET_ALL}")
        elif level == 'actuator':
            print(f"{Fore.CYAN}[{timestamp}] 🔧 {msg}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}[{timestamp}] ℹ {msg}{Style.RESET_ALL}")

    def _register_handlers(self):
        """Register semua event handlers Socket.IO."""
        
        @self.sio.event
        def connect():
            self.connected = True
            self.stats['connection_time'] = datetime.now()
            self._log(f"Connected to {self.url}", 'success')
            # Kirim ping awal
            self.send_event('message', {'type': 'ping', 'content': {'message': 'Tester connected'}})

        @self.sio.event
        def disconnect():
            self.connected = False
            self._log("Disconnected", 'warning')

        @self.sio.event
        def connect_error(data):
            self._log(f"Connection error: {data}", 'error')

        @self.sio.on('notification')
        def on_notification(data):
            self.stats['messages_received'] += 1
            self._log("NOTIFICATION", 'notification')
            self._pretty_print(data)

        @self.sio.on('sensor_update')
        def on_sensor_update(data):
            self.stats['messages_received'] += 1
            self._log("SENSOR_UPDATE", 'sensor')
            self._pretty_print(data)
            # Simpan data terakhir
            sensor_type = data.get('sensor_type')
            if sensor_type:
                self.latest_data[sensor_type] = data

        @self.sio.on('actuator_update')
        def on_actuator_update(data):
            self.stats['messages_received'] += 1
            self._log("ACTUATOR_UPDATE", 'actuator')
            self._pretty_print(data)

        @self.sio.on('connected')
        def on_connected(data):
            self.stats['messages_received'] += 1
            self._log("CONNECTED (server ack)", 'success')
            self._pretty_print(data)

        @self.sio.on('joined')
        def on_joined(data):
            self.stats['messages_received'] += 1
            self._log("JOINED room", 'success')
            self._pretty_print(data)

        @self.sio.on('left')
        def on_left(data):
            self.stats['messages_received'] += 1
            self._log("LEFT room", 'info')
            self._pretty_print(data)

        @self.sio.on('pong')
        def on_pong(data):
            self.stats['messages_received'] += 1
            self._log("PONG", 'info')
            self._pretty_print(data)

        @self.sio.on('sensor_data')
        def on_sensor_data(data):
            self.stats['messages_received'] += 1
            self._log("SENSOR_DATA response", 'info')
            self._pretty_print(data)

        @self.sio.on('command_ack')
        def on_command_ack(data):
            self.stats['messages_received'] += 1
            self._log("COMMAND_ACK", 'success')
            self._pretty_print(data)

        @self.sio.on('error')
        def on_error(data):
            self.stats['messages_received'] += 1
            self._log("SERVER ERROR", 'error')
            self._pretty_print(data)

        @self.sio.on('*')
        def catch_all(event, data):
            self.stats['messages_received'] += 1
            self._log(f"UNKNOWN EVENT: {event}", 'warning')
            self._pretty_print(data)

    def _pretty_print(self, data):
        """Pretty print JSON data."""
        try:
            print(f"   {Fore.WHITE}{json.dumps(data, indent=2)}{Style.RESET_ALL}")
        except:
            print(f"   {Fore.WHITE}{data}{Style.RESET_ALL}")

    def parse_cookie_string(self, cookie_string: str) -> dict:
        """
        Parse cookie string menjadi dictionary.
        
        Args:
            cookie_string: String cookie format "key1=value1; key2=value2"
            
        Returns:
            dict: Dictionary cookies
        """
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def set_cookies(self, cookie_input):
        """
        Set cookies dari berbagai format input.
        
        Args:
            cookie_input: Bisa berupa string cookie atau dictionary
        """
        if isinstance(cookie_input, dict):
            self.cookies = cookie_input
        elif isinstance(cookie_input, str):
            self.cookies = self.parse_cookie_string(cookie_input)
        else:
            raise ValueError("Cookie input must be dict or string")
        
        self._log(f"Cookies set: {list(self.cookies.keys())}", 'success')
        return True

    def login_with_credentials(self, username: str, password: str, login_url: str = None) -> bool:
        """
        Login dengan username/password.
        
        Args:
            username: Username atau email
            password: Password
            login_url: URL endpoint login (default: /login)
            
        Returns:
            bool: True jika login berhasil
        """
        if login_url is None:
            # Ambil base URL
            if '/socket.io' in self.url:
                base_url = self.url.split('/socket.io')[0]
            else:
                base_url = self.url.rstrip('/')
            login_url = f"{base_url}/login"
        else:
            # Format login_url
            if not login_url.startswith('http'):
                if '/socket.io' in self.url:
                    base_url = self.url.split('/socket.io')[0]
                else:
                    base_url = self.url.rstrip('/')
                login_url = f"{base_url}{login_url}" if login_url.startswith('/') else f"{base_url}/{login_url}"

        self._log(f"Logging in to {login_url}", 'info')
        self._log(f"Username: {username}", 'info')
        
        try:
            session = requests.Session()
            
            # Coba dengan form data terlebih dahulu
            data = {'username': username, 'password': password}
            resp = session.post(login_url, data=data, allow_redirects=False, timeout=10)
            
            # Jika gagal, coba dengan JSON
            if resp.status_code != 302 and resp.status_code != 200:
                self._log("Trying JSON login...", 'info')
                json_data = {'email': username, 'password': password}
                resp = session.post(login_url, json=json_data, allow_redirects=False, timeout=10)
            
            # Handle response
            if resp.status_code in [200, 302]:
                # Ambil cookies
                self.cookies = session.cookies.get_dict()
                
                if self.cookies:
                    self._log(f"Login successful! Cookies: {list(self.cookies.keys())}", 'success')
                    return True
                else:
                    # Cek response body untuk token
                    try:
                        resp_json = resp.json()
                        if resp_json.get('success') and resp_json.get('token'):
                            # Jika menggunakan token-based auth
                            self.cookies = {'token': resp_json['token']}
                            self._log("Login successful! Using token authentication", 'success')
                            return True
                        else:
                            self._log(f"Login failed: {resp_json.get('message', 'Unknown error')}", 'error')
                            return False
                    except:
                        self._log(f"No cookies received. Response: {resp.text[:200]}", 'error')
                        return False
            else:
                self._log(f"Login failed with status {resp.status_code}", 'error')
                if resp.text:
                    try:
                        resp_json = resp.json()
                        self._log(f"Message: {resp_json.get('message', resp.text[:200])}", 'error')
                    except:
                        self._log(f"Response: {resp.text[:200]}", 'error')
                return False
                
        except requests.exceptions.Timeout:
            self._log(f"Login timeout after 10 seconds", 'error')
            return False
        except requests.exceptions.ConnectionError:
            self._log(f"Cannot connect to login endpoint", 'error')
            return False
        except Exception as e:
            self._log(f"Login error: {e}", 'error')
            return False

    def connect(self):
        """
        Connect ke Socket.IO server dengan cookies.
        """
        try:
            # Format cookie string untuk header
            if self.cookies:
                cookie_string = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
                self._log(f"Connecting with cookies: {list(self.cookies.keys())}", 'info')
                # Connect dengan cookie header
                self.sio.connect(
                    self.url, 
                    wait_timeout=5, 
                    transports=['websocket', 'polling'],
                    headers={'Cookie': cookie_string}
                )
            else:
                self._log("Connecting without authentication", 'info')
                self.sio.connect(
                    self.url, 
                    wait_timeout=5, 
                    transports=['websocket', 'polling']
                )
            return True
        except Exception as e:
            self._log(f"Connection failed: {e}", 'error')
            return False

    def disconnect(self):
        """Disconnect dari Socket.IO server."""
        if self.sio.connected:
            self.sio.disconnect()
        self.running = False

    def send_event(self, event: str, data: dict) -> bool:
        """
        Kirim event ke server.
        
        Args:
            event: Nama event
            data: Data yang dikirim
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        if not self.sio.connected:
            self._log("Not connected, cannot send", 'error')
            return False
        try:
            self.sio.emit(event, data)
            self.stats['messages_sent'] += 1
            self._log(f"Emitted {event}: {json.dumps(data)[:100]}", 'success')
            return True
        except Exception as e:
            self._log(f"Failed to emit: {e}", 'error')
            return False

    def send_notification(self, message: str, notif_type: str = 'info') -> bool:
        """Send notification to server."""
        return self.send_event('notification', {
            'message': message,
            'type': notif_type
        })

    def send_sensor_request(self, device_id: str = None, sensor_type: str = None) -> bool:
        """Request sensor data from server."""
        content = {}
        if device_id:
            content['device_id'] = device_id
        if sensor_type:
            content['sensor_type'] = sensor_type
        return self.send_event('message', {'type': 'sensor_request', 'content': content})

    def send_actuator_command(self, device_id: str, actuator: str, command: str) -> bool:
        """Send actuator command to server."""
        return self.send_event('message', {
            'type': 'actuator_command',
            'content': {
                'device_id': device_id,
                'actuator': actuator,
                'command': command
            }
        })

    def send_join_room(self, room: str) -> bool:
        """Join a room."""
        return self.send_event('join', {'room': room})

    def send_leave_room(self, room: str) -> bool:
        """Leave a room."""
        return self.send_event('leave', {'room': room})

    def show_stats(self):
        """Show connection statistics."""
        print("\n" + "="*60)
        print(f"{Fore.CYAN}Socket.IO Connection Statistics{Style.RESET_ALL}")
        print("="*60)
        print(f"URL: {self.url}")
        print(f"Connected: {self.sio.connected}")
        if self.stats['connection_time']:
            duration = datetime.now() - self.stats['connection_time']
            print(f"Connection Duration: {duration}")
        print(f"Messages Received: {self.stats['messages_received']}")
        print(f"Messages Sent: {self.stats['messages_sent']}")
        print(f"\nLatest Sensor Data:")
        if self.latest_data:
            for sensor, data in self.latest_data.items():
                print(f"  {sensor}: {data.get('value')} {data.get('unit', '')} @ {data.get('timestamp', 'N/A')[:19]}")
        else:
            print("  No sensor data received yet")
        print("="*60 + "\n")

    def show_help(self):
        """Show help menu."""
        print("\n" + "="*60)
        print(f"{Fore.CYAN}Socket.IO Interactive Tester Commands{Style.RESET_ALL}")
        print("="*60)
        print("  stats           - Show connection statistics")
        print("  sensor [id]     - Request sensor data (id optional)")
        print("  actuator <id> <act> <cmd> - Send actuator command")
        print("  notif <msg>     - Send info notification")
        print("  warning <msg>   - Send warning notification")
        print("  error <msg>     - Send error notification")
        print("  success <msg>   - Send success notification")
        print("  join <room>     - Join a room")
        print("  leave <room>    - Leave a room")
        print("  send <json>     - Send custom JSON as 'message' event")
        print("  ping            - Send ping to server")
        print("  clear           - Clear screen")
        print("  help            - Show this help")
        print("  quit/exit       - Exit tester")
        print("="*60 + "\n")

    def interactive_loop(self):
        """Main interactive command loop."""
        self.show_help()
        
        while self.running:
            try:
                cmd = input(f"{Fore.GREEN}socketio> {Style.RESET_ALL}").strip()
                if not cmd:
                    continue
                    
                parts = cmd.split()
                command = parts[0].lower()

                if command in ('quit', 'exit'):
                    self.disconnect()
                    break
                    
                elif command == 'stats':
                    self.show_stats()
                    
                elif command == 'sensor':
                    device_id = parts[1] if len(parts) > 1 else None
                    self.send_sensor_request(device_id)
                    
                elif command == 'actuator':
                    if len(parts) >= 4:
                        _, device_id, actuator, cmd_str = parts[:4]
                        self.send_actuator_command(device_id, actuator, cmd_str)
                    else:
                        print("Usage: actuator <device_id> <actuator> <command>")
                        
                elif command in ('notif', 'notification'):
                    if len(parts) >= 2:
                        message = ' '.join(parts[1:])
                        self.send_notification(message, 'info')
                    else:
                        print("Usage: notif <message>")
                        
                elif command == 'warning':
                    if len(parts) >= 2:
                        message = ' '.join(parts[1:])
                        self.send_notification(message, 'warning')
                    else:
                        print("Usage: warning <message>")
                        
                elif command == 'error':
                    if len(parts) >= 2:
                        message = ' '.join(parts[1:])
                        self.send_notification(message, 'error')
                    else:
                        print("Usage: error <message>")
                        
                elif command == 'success':
                    if len(parts) >= 2:
                        message = ' '.join(parts[1:])
                        self.send_notification(message, 'success')
                    else:
                        print("Usage: success <message>")
                        
                elif command == 'join':
                    if len(parts) >= 2:
                        self.send_join_room(parts[1])
                    else:
                        print("Usage: join <room>")
                        
                elif command == 'leave':
                    if len(parts) >= 2:
                        self.send_leave_room(parts[1])
                    else:
                        print("Usage: leave <room>")
                        
                elif command == 'ping':
                    self.send_event('message', {'type': 'ping', 'content': {}})
                    
                elif command == 'send':
                    if len(parts) >= 2:
                        try:
                            data = json.loads(' '.join(parts[1:]))
                            self.send_event('message', data)
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON: {e}")
                    else:
                        print("Usage: send <json>")
                        
                elif command == 'clear':
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self.show_help()
                    
                elif command == 'help':
                    self.show_help()
                    
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n")
                self.disconnect()
                break
            except EOFError:
                print("\n")
                self.disconnect()
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Socket.IO Tester for IoT Hidroponik with Authentication Support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic connection (no auth)
  python socketio_tester.py http://localhost:5000
  
  # Using direct cookie (copy from browser)
  python socketio_tester.py --cookie "session=abc123; user_id=5"
  
  # Using cookie from file
  python socketio_tester.py --cookie-file cookies.txt
  
  # Interactive mode with login
  python socketio_tester.py --login --interactive
  
  # Send single command with login
  python socketio_tester.py --login --command "sensor"
  
  # Test connection with custom credentials
  python socketio_tester.py --login --username admin --password secret --test
  
  # Use custom login endpoint
  python socketio_tester.py --login --login-url /api/auth/login
        """
    )
    
    parser.add_argument('url', nargs='?', default='http://localhost:5000',
                       help='Socket.IO URL (default: http://localhost:5000)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Quiet mode (minimal output)')
    parser.add_argument('-c', '--command', type=str,
                       help='Send a single command and exit')
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Start interactive mode')
    parser.add_argument('-t', '--test', action='store_true',
                       help='Run connection test and exit')
    
    # Authentication options - Method 1: Direct cookie
    parser.add_argument('--cookie', type=str,
                       help='Direct cookie string (e.g., "session=abc123; user_id=5")')
    parser.add_argument('--cookie-file', type=str,
                       help='File containing cookie string')
    
    # Authentication options - Method 2: Login with credentials
    parser.add_argument('-l', '--login', action='store_true',
                       help='Perform login before connecting')
    parser.add_argument('-u', '--username', type=str, default='admin',
                       help='Username/email for login (default: admin)')
    parser.add_argument('-p', '--password', type=str, default='password',
                       help='Password for login (default: password)')
    parser.add_argument('--login-url', type=str, default=None,
                       help='Custom login endpoint URL (e.g., /api/login)')

    args = parser.parse_args()
    
    # Determine verbose mode
    verbose = not args.quiet and (args.verbose or args.interactive or not args.command or args.test)
    
    # Create tester instance
    tester = SocketIOTester(args.url, verbose=verbose)
    
    # Method 1: Set cookie directly
    if args.cookie:
        tester.set_cookies(args.cookie)
    elif args.cookie_file:
        try:
            with open(args.cookie_file, 'r') as f:
                cookie_string = f.read().strip()
                tester.set_cookies(cookie_string)
        except Exception as e:
            print(f"{Fore.RED}Error reading cookie file: {e}{Style.RESET_ALL}")
            sys.exit(1)
    
    # Method 2: Login with credentials
    elif args.login:
        if not tester.login_with_credentials(args.username, args.password, args.login_url):
            print(f"{Fore.RED}Authentication failed. Exiting.{Style.RESET_ALL}")
            sys.exit(1)
    
    # Connect to WebSocket
    if not tester.connect():
        if args.test:
            print(f"{Fore.RED}Connection test failed!{Style.RESET_ALL}")
            sys.exit(1)
        sys.exit(1)
    
    # Handle different modes
    if args.test:
        # Test mode: wait for a few messages then show stats
        time.sleep(3)
        print(f"{Fore.GREEN}Connection test successful!{Style.RESET_ALL}")
        tester.show_stats()
        tester.disconnect()
        
    elif args.command:
        # Single command mode
        parts = args.command.split()
        cmd = parts[0].lower()
        
        if cmd == 'sensor':
            device_id = parts[1] if len(parts) > 1 else None
            tester.send_sensor_request(device_id)
        elif cmd == 'actuator' and len(parts) >= 4:
            tester.send_actuator_command(parts[1], parts[2], parts[3])
        elif cmd == 'notif' and len(parts) >= 2:
            message = ' '.join(parts[1:])
            tester.send_notification(message, 'info')
        elif cmd == 'warning' and len(parts) >= 2:
            message = ' '.join(parts[1:])
            tester.send_notification(message, 'warning')
        elif cmd == 'error' and len(parts) >= 2:
            message = ' '.join(parts[1:])
            tester.send_notification(message, 'error')
        elif cmd == 'success' and len(parts) >= 2:
            message = ' '.join(parts[1:])
            tester.send_notification(message, 'success')
        elif cmd == 'join' and len(parts) >= 2:
            tester.send_join_room(parts[1])
        elif cmd == 'leave' and len(parts) >= 2:
            tester.send_leave_room(parts[1])
        elif cmd == 'ping':
            tester.send_event('message', {'type': 'ping', 'content': {}})
        elif args.command.startswith('{'):
            try:
                data = json.loads(args.command)
                tester.send_event('message', data)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}")
        else:
            print(f"Unknown command: {cmd}")
        
        # Wait for response
        time.sleep(2)
        tester.disconnect()
        
    else:
        # Interactive mode
        try:
            tester.interactive_loop()
        except KeyboardInterrupt:
            pass
        finally:
            tester.disconnect()


if __name__ == "__main__":
    main()