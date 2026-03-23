"""
File        : logger.py
Author      : Keyfin Agustio Suratman
Description : Modul logger untuk aplikasi IoT Hidroponik
Created     : 2026-03-19
"""

import os
import datetime
import socket
import subprocess
import platform
from apps.utils import init, Fore, Back, Style


# Konfigurasi file log - folder logs di root project (2 level ke atas)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "log-flask.txt")

# Buat folder logs jika belum ada
os.makedirs(LOG_DIR, exist_ok=True)


# -------------------------------------------------
# Get Local IP Address Function
# -------------------------------------------------

def get_local_ip():
    """Mendapatkan IP lokal di jaringan WiFi/LAN"""
    try:
        # Cara 1: Menggunakan socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            # Cara 2: Fallback dengan perintah system (untuk WiFi)
            if platform.system() == "Windows":
                # Windows
                result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if "Wireless" in line or "WiFi" in line or "Wi-Fi" in line:
                        # Cari IPv4 address beberapa baris setelahnya
                        for j in range(i, min(i+10, len(lines))):
                            if "IPv4" in lines[j] and ":" in lines[j]:
                                ip = lines[j].split(":")[1].strip()
                                return ip
            else:
                # Linux/Mac
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                if ips:
                    return ips[0]  # Ambil IP pertama
        except:
            pass
    
    return "Unknown"


# -------------------------------------------------
# File Logging Functions
# -------------------------------------------------

def write_to_file(level, message, ip=None, method=None, path=None, status=None, device=None, response_time=None):
    """Write log entry to file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        if level == "REQUEST":
            # Format untuk request log dengan response time jika ada
            if response_time:
                log_line = f"[{timestamp}] [{ip}] {method} {path} | {status} | {response_time:.3f}s | Device: {device}\n"
            else:
                log_line = f"[{timestamp}] [{ip}] {method} {path} | {status} | Device: {device}\n"
        else:
            # Format untuk info/warning/error/success
            log_line = f"[{timestamp}] [{level}] {message}\n"
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        # Fallback ke console jika gagal write file
        print(f"{Fore.RED}[ERROR] Failed to write to log file: {e}{Style.RESET_ALL}")


# -------------------------------------------------
# Colored Console Logging Functions
# -------------------------------------------------

def log_request(ip, method, path, status, device, response_time=None):
    """Print colored request log to console and save to file"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Warna berdasarkan method HTTP
    method_colors = {
        'GET': Fore.GREEN,
        'POST': Fore.YELLOW,
        'PUT': Fore.BLUE,
        'DELETE': Fore.RED,
        'PATCH': Fore.MAGENTA,
        'HEAD': Fore.CYAN,
        'OPTIONS': Fore.WHITE,
    }
    method_color = method_colors.get(method, Fore.WHITE)
    
    # Warna berdasarkan kode status
    if status < 200:
        status_color = Fore.WHITE  # Informational
    elif status < 300:
        status_color = Fore.GREEN   # Success
    elif status < 400:
        status_color = Fore.CYAN     # Redirection
    elif status < 500:
        status_color = Fore.YELLOW   # Client Error
    else:
        status_color = Fore.RED       # Server Error
    
    # Format khusus untuk redirect (302, 301) dan error
    if status in [301, 302, 303, 307, 308]:
        status_display = f"{Fore.CYAN}{Back.BLACK} {status} {Style.RESET_ALL}"
    elif status >= 400:
        status_display = f"{Back.RED}{Fore.WHITE} {status} {Style.RESET_ALL}"
    else:
        status_display = f"{status_color}{status}{Style.RESET_ALL}"
    
    # Format response time
    if response_time:
        if response_time < 0.1:
            time_color = Fore.GREEN
        elif response_time < 0.5:
            time_color = Fore.YELLOW
        else:
            time_color = Fore.RED
        time_display = f"{time_color}{response_time:.3f}s{Style.RESET_ALL}"
    else:
        time_display = f"{Fore.LIGHTBLACK_EX}---{Style.RESET_ALL}"
    
    # Truncate path if too long
    path_display = path[:50] + "..." if len(path) > 50 else path
    
    # Truncate device string if too long
    device_display = device[:30] + "..." if len(device) > 30 else device
    
    # Format baris log untuk console
    log_line = (
        f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} "
        f"{Fore.LIGHTBLACK_EX}{ip:15}{Style.RESET_ALL} "
        f"{method_color}{method:7}{Style.RESET_ALL} "
        f"{Fore.LIGHTCYAN_EX}{path_display:50}{Style.RESET_ALL} "
        f"{status_display} "
        f"{time_display:8} "
        f"{Fore.LIGHTBLACK_EX}{device_display}{Style.RESET_ALL}"
    )
    print(log_line)
    
    # Simpan ke file (SELALU simpan, termasuk static files)
    write_to_file("REQUEST", None, ip, method, path, status, device, response_time)


def log_info(message):
    """Print info message with blue color and save to file"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {Fore.BLUE}[INFO]{Style.RESET_ALL} {message}")
    write_to_file("INFO", message)


def log_success(message):
    """Print success message with green color and save to file"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")
    write_to_file("SUCCESS", message)


def log_warning(message):
    """Print warning message with yellow color and save to file"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}")
    write_to_file("WARNING", message)


def log_error(message):
    """Print error message with red color and save to file"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {Fore.RED}[ERROR]{Style.RESET_ALL} {message}")
    write_to_file("ERROR", message)


def log_server_event(event_type, details=None):
    """Log server events like start/stop"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if event_type == "START":
        message = "=" * 70
        write_to_file("INFO", message)
        write_to_file("INFO", f"SERVER STARTED - {details}" if details else "SERVER STARTED")
        write_to_file("INFO", message)
        
        # Tampilkan di console
        print()
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🚀 SERVER STARTED{Style.RESET_ALL} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print()
        
    elif event_type == "STOP":
        message = "=" * 70
        write_to_file("INFO", message)
        write_to_file("INFO", f"SERVER STOPPED - {details}" if details else "SERVER STOPPED")
        write_to_file("INFO", message)
        
        # Tampilkan di console
        print()
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🛑 SERVER STOPPED{Style.RESET_ALL} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if details:
            print(f"{Fore.CYAN}📋 Details:{Style.RESET_ALL} {details}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print()


# -------------------------------------------------
# Banner Function with Network Info
# -------------------------------------------------

def print_startup_banner(config_mode, DEBUG, PORT, VERSION=None, AUTHOR=None):
    """Print beautiful startup banner with app information including network IPs"""
    
    # Get current time for startup
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get local IP addresses
    local_ip = get_local_ip()
    hostname = socket.gethostname()
    
    # Get all network interfaces IPs (attempt)
    all_ips = []
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if "IPv4" in line and ":" in line:
                    ip = line.split(":")[1].strip()
                    if ip and ip not in all_ips:
                        all_ips.append(ip)
        else:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            all_ips = result.stdout.strip().split()
    except:
        all_ips = [local_ip] if local_ip != "Unknown" else []
    
    # Absolute path to log file for display
    abs_log_path = os.path.abspath(LOG_FILE)
    
    banner = f"""
{Fore.CYAN}┌{'─'*80}┐{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.YELLOW}{'🌱 IoT HIDROPONIK DASHBOARD':^77}{Style.RESET_ALL} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}├{'─'*80}┤{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.GREEN}👤 Author   :{Style.RESET_ALL} {AUTHOR:64} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.GREEN}🔢 Version  :{Style.RESET_ALL} {VERSION:64} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.GREEN}📅 Created  :{Style.RESET_ALL} {'2026-03-16':64} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.GREEN}🕐 Started  :{Style.RESET_ALL} {start_time:64} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}├{'─'*80}┤{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.MAGENTA}⚙️ Mode     :{Style.RESET_ALL} {config_mode} {Fore.LIGHTBLACK_EX}({'Development' if DEBUG else 'Production'}){Style.RESET_ALL:49} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.MAGENTA}🔌 Port     :{Style.RESET_ALL} {PORT:<64} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.MAGENTA}🐍 Debug    :{Style.RESET_ALL} {str(DEBUG):<64} {Fore.CYAN}│{Style.RESET_ALL}
"""

    # Tambahkan semua IP yang ditemukan
    for i, ip in enumerate(all_ips):
        if ip != local_ip:
            banner += f"{Fore.CYAN}│{Style.RESET_ALL} {Fore.CYAN}   Network IP:{Style.RESET_ALL} {ip:<52} {Fore.CYAN}│{Style.RESET_ALL}\n"
    
    banner += f"""{Fore.CYAN}├{'─'*80}┤{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL} {Fore.GREEN}🌍 Access URLs:{Style.RESET_ALL:67} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL}    • Local    : http://localhost:{PORT:<45} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}│{Style.RESET_ALL}    • Network  : http://{local_ip}:{PORT:<40} {Style.RESET_ALL} {Fore.CYAN}│{Style.RESET_ALL}
{Fore.CYAN}└{'─'*80}┘{Style.RESET_ALL}
"""

    # Tambahkan semua network URLs
    for i, ip in enumerate(all_ips):
        if ip != local_ip and ip != "127.0.0.1" and not ip.startswith("169.254"):
            banner += f"{Fore.CYAN}│{Style.RESET_ALL}              http://{ip}:{PORT} {Fore.CYAN}│{Style.RESET_ALL}\n"
    
    print(banner)
    