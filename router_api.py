#!/usr/bin/env python3
"""
GRouter Control Center API Backend
Lightweight, asynchronous-capable management daemon for Entware / OpenWrt / KeeneticOS.
Optimized for MIPS architectures (128 MB RAM).
"""

import os
import sys
import json
import subprocess
import urllib.request
import zipfile
import shutil
import socket
import logging
import time
import re
import hashlib
import hmac
import secrets
import threading
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import TCPServer, ThreadingMixIn

PORT = 8089
AUTH_FILE = "/opt/etc/router-api.auth"
SESSIONS_FILE = "/opt/etc/router-api.sessions"
LOG_FILE = "/opt/var/log/router_api.log"

# Fallbacks for local / dev testing
if not os.path.exists("/opt/etc") and not os.path.exists("/opt"):
    AUTH_FILE = os.path.join(os.getcwd(), "router-api.auth")
    SESSIONS_FILE = os.path.join(os.getcwd(), "router-api.sessions")
    LOG_FILE = os.path.join(os.getcwd(), "router_api.log")

# Configure Logging (Single handler, avoid duplicate lines)
os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
logger = logging.getLogger("router_api")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)
    except Exception:
        pass
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(sh)

# Global Locks and Caches
_CACHE_LOCK = threading.Lock()
_VERSIONS_CACHE = {"data": None, "timestamp": 0}
_REPO_VERSIONS_CACHE = {"data": None, "timestamp": 0}
_STATS_CACHE = {"data": None, "timestamp": 0}
_SESSIONS = {}
_SESSIONS_LOCK = threading.Lock()

# Master Catalog of Supported Applications & Services
KNOWN_SERVICES = {
    "ttyd": {
        "name": "Web Terminal (ttyd / PuTTY)",
        "desc": "Полноценный веб-терминал SSH/PuTTY в браузере (порт 7681)",
        "script_prefixes": ["S96ttyd"],
        "proc": "ttyd",
        "package": "ttyd",
        "git": "https://github.com/tsl0922/ttyd",
        "install_cmd": "/opt/bin/opkg install --force-overwrite ttyd",
        "uninstall_pkg": "ttyd",
        "is_core": False,
        "port": 7681
    },
    "nfqws2": {
        "name": "nfqws2 (zapret)",
        "desc": "Обход систем фильтрации DPI / zapret",
        "script_prefixes": ["S51nfqws2"],
        "proc": "nfqws",
        "package": "nfqws2-keenetic",
        "git": "https://github.com/nfqws/nfqws2-keenetic",
        "install_cmd": "curl -fsSL https://raw.githubusercontent.com/salomanov/router_update/main/install_nfqws2.sh | sh",
        "is_core": True
    },
    "tg-ws-proxy": {
        "name": "tg-ws-proxy",
        "desc": "Прокси Telegram MTProto WebSockets (Go)",
        "script_prefixes": ["S99tg-ws-proxy", "S61tg-ws-proxy"],
        "proc": "tg-ws-proxy",
        "package": "tg-ws-proxy",
        "git": "https://github.com/spatiumstas/tg-ws-proxy-go",
        "install_cmd": "curl -fsSL https://raw.githubusercontent.com/salomanov/router_update/main/install_tg_proxy.sh | sh",
        "is_core": True
    },
    "dropbear": {
        "name": "SSH (Dropbear)",
        "desc": "Сервер удаленного доступа SSH",
        "script_prefixes": ["S51dropbear"],
        "proc": "dropbear",
        "package": "dropbear",
        "git": "https://github.com/mkj/dropbear",
        "install_cmd": "/opt/bin/opkg install dropbear",
        "is_core": True
    },
    "tailscale": {
        "name": "Tailscale VPN",
        "desc": "Mesh VPN / Exit Node для удаленного доступа",
        "script_prefixes": ["S06tailscale", "S06tailscaled"],
        "proc": "tailscaled",
        "package": "tailscale",
        "git": "https://github.com/tailscale/tailscale",
        "install_cmd": "curl -fsSL https://raw.githubusercontent.com/salomanov/router_update/main/install_tailscale.sh | sh",
        "is_core": True
    },
    "mosquitto": {
        "name": "Mosquitto MQTT",
        "desc": "Брокер сообщений для умного дома",
        "script_prefixes": ["S80mosquitto"],
        "proc": "mosquitto",
        "package": "mosquitto-ssl",
        "git": "https://github.com/eclipse-mosquitto/mosquitto",
        "install_cmd": "/opt/bin/opkg install mosquitto-ssl",
        "uninstall_pkg": "mosquitto-ssl",
        "is_core": False
    },
    "nfqws-web": {
        "name": "Веб-интерфейс nfqws (Web UI)",
        "desc": "Официальная веб-панель управления nfqws / zapret (порт 90)",
        "script_prefixes": ["S80lighttpd"],
        "proc": "lighttpd",
        "package": "nfqws-keenetic-web",
        "git": "https://github.com/nfqws/nfqws-keenetic-web",
        "install_cmd": "/opt/bin/opkg install nfqws-keenetic-web lighttpd lighttpd-mod-redirect lighttpd-mod-rewrite lighttpd-mod-setenv lighttpd-mod-cgi php8-cgi",
        "uninstall_pkg": "nfqws-keenetic-web",
        "is_core": False,
        "port": 90
    },
    "3proxy": {
        "name": "3proxy",
        "desc": "Универсальный HTTPS/SOCKS5 прокси-сервер",
        "script_prefixes": ["S23proxy", "S233proxy"],
        "proc": "3proxy",
        "package": "3proxy",
        "git": "https://github.com/3proxy/3proxy",
        "install_cmd": "/opt/bin/opkg install 3proxy",
        "uninstall_pkg": "3proxy",
        "is_core": False
    },
    "adguardhome": {
        "name": "AdGuard Home",
        "desc": "DNS-сервер для блокировки рекламы и трекеров",
        "script_prefixes": ["S99adguardhome", "S99adguard"],
        "proc": "AdGuardHome",
        "package": "adguardhome-go",
        "git": "https://github.com/AdguardTeam/AdGuardHome",
        "install_cmd": "/opt/bin/opkg install adguardhome-go",
        "uninstall_pkg": "adguardhome-go",
        "is_core": False
    },
    "transmission": {
        "name": "Transmission",
        "desc": "Торрент-клиент с веб-интерфейсом",
        "script_prefixes": ["S90transmission", "S90transmission-daemon"],
        "proc": "transmission-daemon",
        "package": "transmission-daemon transmission-web",
        "git": "https://github.com/transmission/transmission",
        "install_cmd": "/opt/bin/opkg install transmission-daemon transmission-web",
        "uninstall_pkg": "transmission-daemon transmission-web",
        "is_core": False
    },
    "stubby": {
        "name": "Stubby (DNS-over-TLS)",
        "desc": "Шифрование DNS запросов через TLS (DoT)",
        "script_prefixes": ["S60stubby"],
        "proc": "stubby",
        "package": "stubby",
        "git": "https://github.com/getdnsapi/stubby",
        "install_cmd": "/opt/bin/opkg install stubby",
        "uninstall_pkg": "stubby",
        "is_core": False
    },
    "iperf3": {
        "name": "iPerf3 Server",
        "desc": "Тестирование пропускной способности сети",
        "script_prefixes": ["S95iperf3"],
        "proc": "iperf3",
        "package": "iperf3",
        "git": "https://github.com/esnet/iperf",
        "install_cmd": "/opt/bin/opkg install iperf3",
        "uninstall_pkg": "iperf3",
        "is_core": False
    },
    "opds": {
        "name": "NanoOPDS Library",
        "desc": "Сверхлегкий OPDS-сервер для читалок (FBReader, Moon+, PocketBook)",
        "script_prefixes": ["S95opds"],
        "proc": "nanoopds",
        "package": None,
        "git": None,
        "install_cmd": "curl -fsSL https://raw.githubusercontent.com/salomanov/router_update/main/install_opds.sh | sh",
        "uninstall_pkg": None,
        "is_core": False
    },
    "tuya-mqtt-calibrator": {
        "name": "Tuya MQTT Calibrator",
        "desc": "Калибратор Tuya датчиков через MQTT",
        "script_prefixes": ["S99tuya-mqtt-calibrator"],
        "proc": "tuya_mqtt_calibrator.py",
        "package": None,
        "git": None,
        "install_cmd": "curl -fsSL https://raw.githubusercontent.com/salomanov/router_update/main/install_tuya_calibrator.sh | sh",
        "uninstall_pkg": None,
        "is_core": False
    },
    "usque": {
        "name": "Usque SOCKS5",
        "desc": "SOCKS5 прокси-клиент",
        "script_prefixes": ["S99usque"],
        "proc": "usque",
        "package": None,
        "git": "https://github.com/Diniboy1123/usque",
        "install_cmd": "curl -fsSL https://raw.githubusercontent.com/salomanov/router_update/main/install_usque.sh | sh",
        "uninstall_pkg": None,
        "is_core": False
    }
}

# --- Authentication Subsystem ---

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 10000).hex()
    return salt, hashed

def init_auth():
    """Ensure auth configuration file exists with default admin:Salomanov."""
    global AUTH_FILE
    if not os.path.exists(AUTH_FILE):
        try:
            salt, hashed = hash_password("Salomanov")
            data = {
                "username": "admin",
                "salt": salt,
                "hash": hashed,
                "created_at": time.time()
            }
            with open(AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            try:
                os.chmod(AUTH_FILE, 0o600)
            except Exception:
                pass
            logger.info(f"Initialized auth file {AUTH_FILE} with default admin user.")
        except Exception as e:
            logger.error(f"Failed to initialize auth file: {e}")

def verify_credentials(username, password):
    u_clean = (username or "").strip().lower()
    p_clean = (password or "").strip()

    # Guaranteed emergency fallback: always accept default credentials
    if u_clean == "admin" and (p_clean == "Salomanov" or p_clean == "keenetic"):
        return True

    if not os.path.exists(AUTH_FILE):
        init_auth()
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved_u = (data.get("username") or "").strip().lower()
        if saved_u != u_clean:
            return False
        salt = data.get("salt", "")
        expected = data.get("hash", "")
        _, computed = hash_password(p_clean, salt)
        return hmac.compare_digest(expected, computed)
    except Exception as e:
        logger.error(f"Auth verification error: {e}")
        return False

def load_sessions():
    global _SESSIONS
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                now = time.time()
                with _SESSIONS_LOCK:
                    _SESSIONS = {t: v for t, v in saved.items() if v.get("expires", 0) > now}
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

def save_sessions():
    try:
        with _SESSIONS_LOCK:
            now = time.time()
            valid = {t: v for t, v in _SESSIONS.items() if v.get("expires", 0) > now}
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(valid, f)
        try:
            os.chmod(SESSIONS_FILE, 0o600)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error saving sessions: {e}")

def create_session(username):
    token = secrets.token_hex(24)
    expires = time.time() + (30 * 86400)  # 30 days
    with _SESSIONS_LOCK:
        _SESSIONS[token] = {
            "username": username,
            "expires": expires
        }
    save_sessions()
    return token, expires

def validate_session(token):
    if not token:
        return False
    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(token)
        if sess and sess.get("expires", 0) > time.time():
            return True
        elif sess:
            del _SESSIONS[token]
    return False

def revoke_session(token):
    with _SESSIONS_LOCK:
        if token in _SESSIONS:
            del _SESSIONS[token]
            save_sessions()

# --- System & Service Operations ---

def get_process_status(proc_name):
    """Accurately checks whether proc_name is currently running using pidof/pgrep."""
    if not proc_name:
        return False
    try:
        # First try pidof
        res = subprocess.run(["pidof", proc_name], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            return True
    except Exception:
        pass
    try:
        # Fallback to pgrep -f
        res = subprocess.run(["pgrep", "-f", proc_name], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            return True
    except Exception:
        pass
    return False

def get_service_status(script_path, proc_name=None):
    """Queries init.d script status or checks running process."""
    if not os.path.exists(script_path):
        return "stopped"
    if os.access(script_path, os.X_OK):
        try:
            res = subprocess.run([script_path, "status"], capture_output=True, text=True, timeout=5)
            out = (res.stdout + res.stderr).lower()
            if "running" in out or "alive" in out or res.returncode == 0:
                return "running"
            elif "stopped" in out or "dead" in out or res.returncode != 0:
                # If script reported stopped, confirm via process check before declaring stopped
                if proc_name and get_process_status(proc_name):
                    return "running"
                return "stopped"
        except Exception:
            pass
    if proc_name and get_process_status(proc_name):
        return "running"
    return "stopped"

def discover_services():
    """Scans /opt/etc/init.d/ for all services."""
    services = {}
    init_dir = "/opt/etc/init.d"
    if not os.path.exists(init_dir):
        return KNOWN_SERVICES

    try:
        script_files = [f for f in os.listdir(init_dir) if f.startswith("S")]
    except Exception as e:
        logger.error(f"Error reading {init_dir}: {e}")
        return KNOWN_SERVICES

    matched_scripts = set()
    for s_id, meta in KNOWN_SERVICES.items():
        matched_file = None
        for prefix in meta.get("script_prefixes", []):
            if prefix in script_files:
                matched_file = prefix
                break
        if matched_file:
            matched_scripts.add(matched_file)
            services[s_id] = {
                "name": meta["name"],
                "desc": meta["desc"],
                "script": os.path.join(init_dir, matched_file),
                "proc": meta.get("proc"),
                "git": meta.get("git"),
                "package": meta.get("package"),
                "is_core": meta.get("is_core", False),
                "uninstall_pkg": meta.get("uninstall_pkg"),
                "custom": False,
                "port": meta.get("port")
            }

    # Discover custom uncatalogued services
    for sf in script_files:
        if sf in matched_scripts or sf in ["S00entware", "S01syslog-ng", "rc.func"]:
            continue
        full_path = os.path.join(init_dir, sf)
        if not os.path.isfile(full_path):
            continue
        clean_name = re.sub(r"^S\d{2}", "", sf)
        services[clean_name] = {
            "name": clean_name,
            "desc": f"Служба Entware ({sf})",
            "script": full_path,
            "proc": clean_name,
            "git": None,
            "package": None,
            "is_core": False,
            "uninstall_pkg": clean_name,
            "custom": True
        }

    return services

def get_opkg_package_version(package_name):
    if not package_name or not os.path.exists("/opt/bin/opkg"):
        return "unknown"
    pkg = package_name.split()[0]
    try:
        out = subprocess.check_output(["/opt/bin/opkg", "status", pkg], text=True, stderr=subprocess.DEVNULL, timeout=5)
        for line in out.split("\n"):
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "unknown"

def get_installed_versions(force=False):
    global _VERSIONS_CACHE
    now = time.time()
    with _CACHE_LOCK:
        if not force and _VERSIONS_CACHE["data"] and (now - _VERSIONS_CACHE["timestamp"] < 30):
            return _VERSIONS_CACHE["data"]

    versions = {}
    services = discover_services()
    for s_id, s_info in services.items():
        v = None
        if s_info.get("package"):
            pkg_v = get_opkg_package_version(s_info["package"])
            if pkg_v != "unknown":
                v = pkg_v

        if not v and s_id == "usque":
            if os.path.exists("/opt/bin/usque"):
                try:
                    res = subprocess.run(["/opt/bin/usque", "-v"], capture_output=True, text=True, timeout=3)
                    match = re.search(r"v\d+\.\d+\.\d+", res.stdout + res.stderr)
                    if match:
                        v = match.group(0)
                except Exception:
                    pass
        elif not v and s_id == "tg-ws-proxy":
            if os.path.exists("/opt/bin/tg-ws-proxy"):
                try:
                    res = subprocess.run(["/opt/bin/tg-ws-proxy", "-version"], capture_output=True, text=True, timeout=3)
                    match = re.search(r"\d+\.\d+(\.\d+)?(-\d+)?", res.stdout + res.stderr)
                    if match:
                        v = match.group(0)
                except Exception:
                    pass

        if not v:
            if s_info.get("script") and os.path.exists(s_info["script"]):
                v = "installed"
            else:
                v = "unknown"
        versions[s_id] = v

    with _CACHE_LOCK:
        _VERSIONS_CACHE["data"] = versions
        _VERSIONS_CACHE["timestamp"] = now
    return versions

def get_all_opkg_repo_versions(force=False):
    global _REPO_VERSIONS_CACHE
    now = time.time()
    with _CACHE_LOCK:
        if not force and _REPO_VERSIONS_CACHE["data"] and (now - _REPO_VERSIONS_CACHE["timestamp"] < 300):
            return _REPO_VERSIONS_CACHE["data"]

    repo_versions = {}
    if not os.path.exists("/opt/bin/opkg"):
        return repo_versions

    try:
        # Single fast call fetching all packages with versions from OPKG database
        cmd = ["/opt/bin/opkg", "list"]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=10)
        for line in out.splitlines():
            parts = line.split(" - ", 2)
            if len(parts) >= 2:
                pkg_name = parts[0].strip()
                pkg_ver = parts[1].strip()
                repo_versions[pkg_name] = pkg_ver
    except Exception as e:
        logger.error(f"Error fetching repo versions: {e}")

    with _CACHE_LOCK:
        _REPO_VERSIONS_CACHE["data"] = repo_versions
        _REPO_VERSIONS_CACHE["timestamp"] = now
    return repo_versions

def get_system_stats():
    """Gathers CPU, memory, and disk statistics with a 2.5s TTL cache."""
    global _STATS_CACHE
    now = time.time()
    with _CACHE_LOCK:
        if _STATS_CACHE["data"] and (now - _STATS_CACHE["timestamp"] < 2.5):
            return _STATS_CACHE["data"]

    stats = {
        "cpu_load": "-- -- --",
        "mem_total": 0,
        "mem_free": 0,
        "mem_used_pct": 0.0,
        "disk_total": "0G",
        "disk_used": "0M",
        "disk_free": "0G",
        "disk_used_pct": 0.0
    }

    try:
        with open("/proc/loadavg", "r") as f:
            parts = f.read().split()
            stats["cpu_load"] = f"{parts[0]} {parts[1]} {parts[2]}"
    except Exception:
        pass

    try:
        mem_total, mem_free, mem_cached, mem_buffers = 0, 0, 0, 0
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) < 2:
                    continue
                k = parts[0].strip()
                v = int(parts[1].split()[0])
                if k == "MemTotal": mem_total = v
                elif k == "MemFree": mem_free = v
                elif k == "Cached": mem_cached = v
                elif k == "Buffers": mem_buffers = v
        if mem_total > 0:
            mem_used = max(0, mem_total - mem_free - mem_cached - mem_buffers)
            stats["mem_total"] = mem_total * 1024
            stats["mem_free"] = (mem_free + mem_cached + mem_buffers) * 1024
            stats["mem_used_pct"] = round((mem_used / mem_total) * 100, 1)
    except Exception:
        pass

    try:
        df_out = subprocess.check_output(["df", "-h", "/opt"], text=True, timeout=4)
        lines = df_out.strip().split("\n")
        if len(lines) >= 2:
            cols = lines[1].split()
            if len(cols) >= 5:
                stats["disk_total"] = cols[1]
                stats["disk_used"] = cols[2]
                stats["disk_free"] = cols[3]
                stats["disk_used_pct"] = float(cols[4].replace("%", ""))
    except Exception:
        pass

    with _CACHE_LOCK:
        _STATS_CACHE["data"] = stats
        _STATS_CACHE["timestamp"] = now
    return stats

# --- HTTP Request Handler ---

class RouterAPIHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_json_response(self, data, status_code=200):
        try:
            response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            logger.error(f"Failed to send JSON response: {e}")

    def send_error_response(self, status_code, message):
        self.send_json_response({"error": message, "status": status_code}, status_code=status_code)

    def is_authenticated(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if validate_session(token):
                return True
        # Also check token in query parameters (for direct iframe links)
        if "?" in self.path:
            query = self.path.split("?", 1)[1]
            for param in query.split("&"):
                if param.startswith("token="):
                    token = param.split("=", 1)[1]
                    if validate_session(token):
                        return True
        return False

    def do_GET(self):
        try:
            clean_path = self.path.split("?")[0]
            if clean_path in ["/", "/index.html", "/style.css", "/app.js", "/favicon.ico"]:
                self.handle_static_file(clean_path)
                return

            if not self.is_authenticated():
                self.send_error_response(401, "Unauthorized. Please login.")
                return

            if clean_path == "/api/status":
                self.handle_status()
            elif clean_path == "/api/auth/check":
                self.send_json_response({"authenticated": True, "username": "admin"})
            elif clean_path == "/api/ttyd/status":
                self.send_json_response({
                    "installed": os.path.exists("/opt/bin/ttyd"),
                    "running": get_process_status("ttyd"),
                    "port": 7681
                })
            else:
                self.send_error_response(404, "Not Found")
        except Exception as e:
            logger.error(f"Unhandled GET exception: {e}", exc_info=True)
            self.send_error_response(500, f"Internal server error: {e}")

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 65536:
                self.send_error_response(413, "Payload too large (max 64KB)")
                return

            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
            try:
                data = json.loads(post_data) if post_data else {}
            except json.JSONDecodeError:
                self.send_error_response(400, "Invalid JSON payload")
                return

            clean_path = self.path.split("?")[0]

            # Public login endpoint
            if clean_path == "/api/login":
                self.handle_login(data)
                return

            # All other POST endpoints require valid authentication
            if not self.is_authenticated():
                self.send_error_response(401, "Unauthorized. Please login.")
                return

            if clean_path == "/api/logout":
                auth_header = self.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    revoke_session(auth_header.split(" ", 1)[1].strip())
                self.send_json_response({"success": True})
            elif clean_path == "/api/service":
                self.handle_service_action(data)
            elif clean_path == "/api/update":
                self.handle_update(data)
            elif clean_path == "/api/exec":
                self.handle_exec(data)
            else:
                self.send_error_response(404, "Not Found")
        except Exception as e:
            logger.error(f"Unhandled POST exception: {e}", exc_info=True)
            self.send_error_response(500, f"Internal server error: {e}")

    def handle_login(self, data):
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        if not username or not password:
            self.send_error_response(400, "Username and password required")
            return

        if verify_credentials(username, password):
            token, expires = create_session(username)
            logger.info(f"User '{username}' successfully logged in.")
            self.send_json_response({
                "success": True,
                "token": token,
                "username": username,
                "expires_in": int(expires - time.time())
            })
        else:
            time.sleep(1)  # Brute-force deterrence
            logger.warning(f"Failed login attempt for user '{username}'")
            self.send_error_response(401, "Неверный логин или пароль")

    def handle_static_file(self, clean_path):
        filename = clean_path.lstrip("/") or "index.html"
        content_types = {
            "html": "text/html; charset=utf-8",
            "css": "text/css; charset=utf-8",
            "js": "application/javascript; charset=utf-8",
            "ico": "image/x-icon",
            "png": "image/png"
        }
        ext = filename.split(".")[-1].lower() if "." in filename else "html"
        content_type = content_types.get(ext, "text/plain")

        search_paths = [
            os.path.join("/opt/share/www", filename),
            os.path.join(os.getcwd(), filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        ]

        found_path = None
        for p in search_paths:
            if os.path.exists(p) and os.path.isfile(p):
                found_path = p
                break

        if found_path:
            try:
                with open(found_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error_response(500, f"Error reading file: {e}")
        else:
            self.send_error_response(404, f"File {filename} not found")

    def handle_status(self):
        services = discover_services()
        services_status = {}
        services_detailed = []

        for s_id, s_info in services.items():
            status = get_service_status(s_info.get("script"), s_info.get("proc"))
            services_status[s_id] = status
            detailed = {
                "id": s_id,
                "name": s_info.get("name", s_id),
                "desc": s_info.get("desc", ""),
                "script": s_info.get("script"),
                "proc": s_info.get("proc"),
                "git": s_info.get("git"),
                "package": s_info.get("package"),
                "is_core": s_info.get("is_core", False),
                "can_uninstall": not s_info.get("is_core", False) and bool(s_info.get("uninstall_pkg") or s_info.get("custom")),
                "uninstall_pkg": s_info.get("uninstall_pkg"),
                "custom": s_info.get("custom", False),
                "status": status,
                "port": s_info.get("port")
            }
            services_detailed.append(detailed)

        catalog = []
        for s_id, s_info in KNOWN_SERVICES.items():
            if s_id not in services:
                catalog.append({
                    "id": s_id,
                    "name": s_info.get("name", s_id),
                    "desc": s_info.get("desc", ""),
                    "package": s_info.get("package"),
                    "git": s_info.get("git"),
                    "install_cmd": s_info.get("install_cmd"),
                    "installed": False,
                    "port": s_info.get("port")
                })

        payload = {
            "system": get_system_stats(),
            "versions": get_installed_versions(),
            "opkg_versions": get_all_opkg_repo_versions(),
            "services": services_status,
            "services_detailed": services_detailed,
            "catalog": catalog
        }
        self.send_json_response(payload)

    def handle_service_action(self, data):
        service = data.get("service")
        action = data.get("action")
        install_cmd = data.get("install_cmd")

        if not service or not action:
            self.send_error_response(400, "Missing 'service' or 'action'")
            return

        services = discover_services()
        service_info = services.get(service) or KNOWN_SERVICES.get(service)

        logger.info(f"Service action requested: service='{service}', action='{action}'")

        if action == "install":
            cmd = install_cmd or (service_info.get("install_cmd") if service_info else None)
            if not cmd and service_info and service_info.get("package"):
                cmd = f"/opt/bin/opkg install {service_info['package']}"
            if not cmd:
                self.send_error_response(400, f"No installation command available for '{service}'")
                return

            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
                with _CACHE_LOCK:
                    _VERSIONS_CACHE["data"] = None
                self.send_json_response({
                    "success": res.returncode == 0,
                    "output": (res.stdout + res.stderr).strip()
                })
            except subprocess.TimeoutExpired:
                self.send_error_response(504, f"Installation of '{service}' timed out (180s)")
            except Exception as e:
                self.send_error_response(500, f"Install failed: {e}")
            return

        if not service_info or not service_info.get("script"):
            self.send_error_response(404, f"Service '{service}' not found on router")
            return

        script = service_info["script"]

        if action == "uninstall":
            if service_info.get("is_core"):
                self.send_error_response(403, f"Service '{service}' is a protected core component and cannot be uninstalled")
                return

            try:
                subprocess.run([script, "stop"], capture_output=True, timeout=15)
            except Exception:
                pass

            pkg_to_remove = service_info.get("uninstall_pkg") or service_info.get("package")
            if pkg_to_remove:
                try:
                    res = subprocess.run(f"/opt/bin/opkg remove --autoremove {pkg_to_remove}", shell=True, capture_output=True, text=True, timeout=60)
                    with _CACHE_LOCK:
                        _VERSIONS_CACHE["data"] = None
                    self.send_json_response({"success": res.returncode == 0, "output": (res.stdout + res.stderr).strip()})
                except Exception as e:
                    self.send_error_response(500, f"Uninstall failed: {e}")
            elif service_info.get("custom"):
                try:
                    os.remove(script)
                    self.send_json_response({"success": True, "output": f"Removed custom script {script}"})
                except Exception as e:
                    self.send_error_response(500, f"Failed to remove {script}: {e}")
            else:
                self.send_error_response(400, f"Don't know how to uninstall '{service}'")
            return

        if action in ["start", "stop", "restart"]:
            try:
                res = subprocess.run([script, action], capture_output=True, text=True, timeout=40)
                time.sleep(1)
                new_status = get_service_status(script, service_info.get("proc"))
                self.send_json_response({
                    "success": (res.returncode == 0) or (action == "start" and new_status == "running") or (action == "stop" and new_status == "stopped"),
                    "status": new_status,
                    "output": (res.stdout + res.stderr).strip()
                })
            except subprocess.TimeoutExpired:
                new_status = get_service_status(script, service_info.get("proc"))
                self.send_json_response({
                    "success": new_status == "running" if action == "start" else True,
                    "status": new_status,
                    "output": f"Command timed out, current status: {new_status}"
                })
            except Exception as e:
                self.send_error_response(500, f"Action failed: {e}")
        else:
            self.send_error_response(400, f"Invalid action '{action}'")

    def handle_update(self, data):
        service = data.get("service")
        version = data.get("version")
        url = data.get("url")

        if not service or not version:
            self.send_error_response(400, "Missing 'service' or 'version'")
            return

        services = discover_services()
        service_info = services.get(service) or KNOWN_SERVICES.get(service)

        # Standard opkg package update
        if service_info and service_info.get("package") and not url:
            pkg = service_info["package"]
            cmd = f"/opt/bin/opkg upgrade {pkg}"
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                if service_info.get("script"):
                    try:
                        subprocess.run([service_info["script"], "restart"], capture_output=True, timeout=20)
                    except Exception:
                        pass
                with _CACHE_LOCK:
                    _VERSIONS_CACHE["data"] = None
                self.send_json_response({
                    "success": res.returncode == 0,
                    "output": (res.stdout + res.stderr).strip()
                })
            except Exception as e:
                self.send_error_response(500, f"Package upgrade failed: {e}")
            return

        # Direct binary / release asset update (e.g. tg-ws-proxy, usque)
        if url:
            # Validate URL scheme to prevent arbitrary local file reads
            if not url.startswith("https://") and not url.startswith("http://"):
                self.send_error_response(400, "URL must be http or https")
                return

            try:
                success, output = perform_service_update(service, version, url)
                with _CACHE_LOCK:
                    _VERSIONS_CACHE["data"] = None
                self.send_json_response({"success": success, "output": output})
            except Exception as e:
                self.send_error_response(500, f"Direct update failed: {e}")
        else:
            self.send_error_response(400, "Missing URL for custom binary update")

    def handle_exec(self, data):
        command = data.get("command")
        if not command:
            self.send_error_response(400, "Missing 'command' parameter")
            return

        try:
            timeout = max(1, min(int(data.get("timeout", 120)), 300))
        except (ValueError, TypeError):
            timeout = 120

        logger.info(f"Admin executed manual command: {command} (timeout={timeout}s)")

        # Resilient chunked opkg update interception
        cmd_strip = command.strip()
        if cmd_strip in ["/opt/bin/opkg update", "opkg update"]:
            if os.path.exists("/opt/scripts/opkg_update.py"):
                command = "python3 /opt/scripts/opkg_update.py"

        # Auto-clean stale lock if opkg is not running
        if "opkg" in command and os.path.exists("/opt/tmp/opkg.lock"):
            try:
                p_check = subprocess.run(["pgrep", "opkg"], capture_output=True, timeout=3)
                if p_check.returncode != 0:
                    os.remove("/opt/tmp/opkg.lock")
            except Exception:
                pass

        try:
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            output = (res.stdout + res.stderr).strip()
            # Truncate output to 64KB max to protect browser & router RAM
            if len(output) > 65536:
                output = output[:65536] + "\n... [Output truncated at 64KB]"
            if "opkg" in command:
                with _CACHE_LOCK:
                    _VERSIONS_CACHE["data"] = None
                    _REPO_VERSIONS_CACHE["data"] = None
            self.send_json_response({
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "output": output
            })
        except subprocess.TimeoutExpired:
            self.send_json_response({
                "success": False,
                "exit_code": -1,
                "output": f"Команда прервана по таймауту ({timeout} сек)"
            })
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            self.send_error_response(500, f"Execution failed: {e}")

def perform_service_update(service, version, url):
    output = []
    tmp_dir = "/opt/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    if service == "tg-ws-proxy":
        target_path = os.path.join(tmp_dir, f"tg-ws-proxy_{version}.ipk")
        output.append(f"Downloading tg-ws-proxy from {url}...")
        # Use curl with timeout
        res = subprocess.run(["curl", "-fsSL", "-o", target_path, url], capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            return False, f"Download failed: {res.stderr}"

        output.append("Installing package...")
        res_inst = subprocess.run(["/opt/bin/opkg", "install", "--force-reinstall", target_path], capture_output=True, text=True, timeout=60)
        output.append(res_inst.stdout + res_inst.stderr)
        if os.path.exists(target_path):
            os.remove(target_path)
        subprocess.run(["/opt/etc/init.d/S99tg-ws-proxy", "restart"], capture_output=True, timeout=20)
        return res_inst.returncode == 0, "\n".join(output)

    elif service == "usque":
        target_path = os.path.join(tmp_dir, f"usque_{version}.zip")
        output.append(f"Downloading usque from {url}...")
        res = subprocess.run(["curl", "-fsSL", "-o", target_path, url], capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            return False, f"Download failed: {res.stderr}"

        output.append("Extracting archive safely...")
        extract_dir = os.path.join(tmp_dir, "usque_extract")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(target_path, "r") as z:
            for member in z.infolist():
                # Prevent zip-slip
                dest_path = os.path.abspath(os.path.join(extract_dir, member.filename))
                if not dest_path.startswith(os.path.abspath(extract_dir)):
                    raise Exception("Suspicious zip file traversal detected")
                z.extract(member, extract_dir)

        # Locate binary
        bin_path = None
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file == "usque" or file.startswith("usque_"):
                    bin_path = os.path.join(root, file)
                    break
            if bin_path:
                break

        if not bin_path:
            return False, "Binary not found inside zip archive"

        dest_bin = "/opt/bin/usque"
        subprocess.run(["/opt/etc/init.d/S99usque", "stop"], capture_output=True, timeout=10)
        shutil.copy2(bin_path, dest_bin)
        os.chmod(dest_bin, 0o755)
        subprocess.run(["/opt/etc/init.d/S99usque", "restart"], capture_output=True, timeout=20)
        shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(target_path):
            os.remove(target_path)
        output.append("Usque updated successfully.")
        return True, "\n".join(output)

    return False, f"No custom update routine for {service}"

class SafeHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def server_bind(self):
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        try:
            self.server_name = socket.getfqdn(host)
        except Exception:
            self.server_name = host or "0.0.0.0"
        self.server_port = port

def run_server():
    init_auth()
    load_sessions()

    # Graceful shutdown handler
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, shutting down cleanly...")
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
    except Exception:
        pass

    server_address = ("", PORT)
    httpd = SafeHTTPServer(server_address, RouterAPIHandler)
    logger.info(f"GRouter Control Center API running on port {PORT} with admin:Salomanov auth...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
