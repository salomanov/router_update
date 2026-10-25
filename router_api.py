#!/usr/bin/env python3
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
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import TCPServer, ThreadingMixIn

_VERSIONS_CACHE = {"data": None, "timestamp": 0}
_REPO_VERSIONS_CACHE = {"data": None, "timestamp": 0}

# Configure Logging
LOG_FILE = "/opt/var/log/router_api.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# Also log to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)

PORT = 8089

# Master Catalog of Supported Applications & Services
KNOWN_SERVICES = {
    "nfqws2": {
        "name": "nfqws2 (zapret)",
        "desc": "Обход систем фильтрации DPI / zapret",
        "script_prefixes": ["S51nfqws2"],
        "proc": "nfqws",
        "package": "nfqws2-keenetic",
        "git": "https://github.com/bol-van/zapret",
        "install_cmd": "curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_nfqws2.sh | sh",
        "is_core": True
    },
    "tg-ws-proxy": {
        "name": "tg-ws-proxy",
        "desc": "Прокси Telegram MTProto WebSockets (Go)",
        "script_prefixes": ["S99tg-ws-proxy", "S61tg-ws-proxy"],
        "proc": "tg-ws-proxy",
        "package": "tg-ws-proxy",
        "git": "https://github.com/spatiumstas/tg-ws-proxy-go",
        "install_cmd": "curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_tg_proxy.sh | sh",
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
        "install_cmd": "curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_tailscale.sh | sh",
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
    "lighttpd": {
        "name": "Lighttpd",
        "desc": "Веб-сервер роутера",
        "script_prefixes": ["S80lighttpd"],
        "proc": "lighttpd",
        "package": "lighttpd",
        "git": "https://github.com/lighttpd/lighttpd1.4",
        "install_cmd": "/opt/bin/opkg install lighttpd",
        "uninstall_pkg": "lighttpd",
        "is_core": False
    },
    "3proxy": {
        "name": "3proxy",
        "desc": "Универсальный HTTPS/SOCKS5 прокси-сервер",
        "script_prefixes": ["S23proxy"],
        "proc": "3proxy",
        "package": "3proxy",
        "git": "https://github.com/3proxy/3proxy",
        "install_cmd": "/opt/bin/opkg install 3proxy",
        "uninstall_pkg": "3proxy",
        "is_core": False
    },
    "usque": {
        "name": "Usque SOCKS5",
        "desc": "SOCKS5 прокси-клиент",
        "script_prefixes": ["S99usque"],
        "proc": "usque",
        "package": None,
        "git": "https://github.com/Diniboy1123/usque",
        "install_cmd": None,
        "is_core": False
    },
    "tuya-mqtt-calibrator": {
        "name": "Tuya MQTT Calibrator",
        "desc": "Калибратор Tuya датчиков через MQTT",
        "script_prefixes": ["S99tuya-mqtt-calibrator"],
        "proc": "tuya_mqtt_calibrator.py",
        "package": None,
        "is_core": False
    },
    "opds": {
        "name": "NanoOPDS Library",
        "desc": "Сверхлегкий OPDS-сервер для читалок (FBReader, Moon+, PocketBook)",
        "script_prefixes": ["S95opds"],
        "proc": "nanoopds",
        "package": None,
        "is_core": False
    },
    "adguardhome": {
        "name": "AdGuard Home",
        "desc": "DNS-сервер для блокировки рекламы и трекеров",
        "script_prefixes": ["S99adguardhome", "S90adguardhome"],
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
        "script_prefixes": ["S88transmission", "S90transmission"],
        "proc": "transmission-daemon",
        "package": "transmission-daemon",
        "git": "https://github.com/transmission/transmission",
        "install_cmd": "/opt/bin/opkg install transmission-daemon transmission-web",
        "uninstall_pkg": "transmission-daemon transmission-web",
        "is_core": False
    },
    "stubby": {
        "name": "Stubby (DNS-over-TLS)",
        "desc": "Шифрование DNS запросов через TLS (DoT)",
        "script_prefixes": ["S24stubby"],
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
        "script_prefixes": ["S99iperf3", "S90iperf3"],
        "proc": "iperf3",
        "package": "iperf3",
        "git": "https://github.com/esnet/iperf",
        "install_cmd": "/opt/bin/opkg install iperf3",
        "uninstall_pkg": "iperf3",
        "is_core": False
    }
}

# Dynamic registry populated by discover_services()
SERVICES = {}

def get_process_status(proc_name):
    """Checks if a process is running by searching the active processes."""
    if not proc_name:
        return "unknown"
    try:
        ps_output = subprocess.check_output(["ps", "-w"]).decode("utf-8", errors="ignore")
        for line in ps_output.splitlines():
            if proc_name in line and "router_api.py" not in line and "ps" not in line:
                return "running"
        return "stopped"
    except Exception as e:
        logging.error(f"Error checking process {proc_name}: {e}")
        return "unknown"

def get_service_status(script_path, proc_name=None):
    """Retrieves current status of a service using its init script and process status."""
    if script_path and os.path.exists(script_path):
        try:
            res = subprocess.run([script_path, "status"], capture_output=True, text=True, timeout=5)
            output = (res.stdout + res.stderr).lower()
            if "not running" in output or "stopped" in output or "dead" in output or "inactive" in output:
                return "stopped"
            elif "running" in output or "alive" in output or "started" in output or "active" in output:
                return "running"
        except Exception:
            pass
            
    if proc_name:
        return get_process_status(proc_name)
    return "unknown"

def discover_services():
    """
    Scans /opt/etc/init.d/ for all installed service scripts.
    Returns:
      installed: dict of { service_id: metadata }
      catalog: list of known services that are NOT currently installed
    """
    global SERVICES
    init_dir = "/opt/etc/init.d"
    installed = {}
    matched_known = set()

    if os.path.exists(init_dir):
        for fname in sorted(os.listdir(init_dir)):
            # Only match S* init scripts, ignore rc.* and S90router-api
            if not fname.startswith("S") or fname in ["S90router-api"]:
                continue
            script_path = os.path.join(init_dir, fname)
            if not os.path.isfile(script_path) or not os.access(script_path, os.X_OK):
                continue
            
            # Match against KNOWN_SERVICES
            matched_id = None
            for s_id, meta in KNOWN_SERVICES.items():
                prefixes = meta.get("script_prefixes", [])
                if any(fname == p or fname.startswith(p) for p in prefixes):
                    matched_id = s_id
                    break
            
            if matched_id:
                meta = KNOWN_SERVICES[matched_id]
                matched_known.add(matched_id)
                installed[matched_id] = {
                    "id": matched_id,
                    "name": meta["name"],
                    "desc": meta["desc"],
                    "script": script_path,
                    "proc": meta.get("proc"),
                    "git": meta.get("git"),
                    "package": meta.get("package"),
                    "is_core": meta.get("is_core", False),
                    "can_uninstall": not meta.get("is_core", False) and bool(meta.get("uninstall_pkg")),
                    "uninstall_pkg": meta.get("uninstall_pkg")
                }
            else:
                # Custom/third-party Entware service (e.g. S23redsocks, S50avahi, etc.)
                clean_name = re.sub(r"^S\d+", "", fname)
                service_id = clean_name.lower()
                installed[service_id] = {
                    "id": service_id,
                    "name": clean_name,
                    "desc": f"Служба Entware ({fname})",
                    "script": script_path,
                    "proc": clean_name,
                    "git": None,
                    "is_core": False,
                    "can_uninstall": True,
                    "custom": True
                }

    # Also check if tuya-mqtt-calibrator is installed via script if no init script
    if "tuya-mqtt-calibrator" not in installed and (os.path.exists("/opt/scripts/tuya_mqtt_calibrator.py") or os.path.exists("/opt/usr/bin/tuya_mqtt_calibrator.py")):
        meta = KNOWN_SERVICES["tuya-mqtt-calibrator"]
        installed["tuya-mqtt-calibrator"] = {
            "id": "tuya-mqtt-calibrator",
            "name": meta["name"],
            "desc": meta["desc"],
            "script": "/opt/etc/init.d/S99tuya-mqtt-calibrator" if os.path.exists("/opt/etc/init.d/S99tuya-mqtt-calibrator") else None,
            "proc": meta.get("proc"),
            "git": None,
            "is_core": False,
            "can_uninstall": False
        }
        matched_known.add("tuya-mqtt-calibrator")

    # Catalog of available known services that are NOT installed
    catalog = []
    for s_id, meta in KNOWN_SERVICES.items():
        if s_id not in matched_known:
            catalog.append({
                "id": s_id,
                "name": meta["name"],
                "desc": meta["desc"],
                "package": meta.get("package"),
                "git": meta.get("git"),
                "install_cmd": meta.get("install_cmd"),
                "installed": False
            })

    SERVICES = installed
    return installed, catalog

def get_opkg_package_version(package_name):
    """Queries opkg status for a package and parses its version."""
    try:
        opkg_out = subprocess.check_output(["/opt/bin/opkg", "status", package_name], text=True)
        for line in opkg_out.splitlines():
            if line.startswith("Version:"):
                return line.replace("Version:", "").strip()
    except Exception:
        pass
    return None

def get_opkg_repo_version(package_name):
    """Queries opkg info for a package and parses the repository version (not-installed status or first match)."""
    try:
        opkg_out = subprocess.check_output(["/opt/bin/opkg", "info", package_name], text=True)
        blocks = opkg_out.strip().split("\n\n")
        repo_ver = None
        for block in blocks:
            lines = block.splitlines()
            ver = None
            status_not_installed = False
            for line in lines:
                if line.startswith("Version:"):
                    ver = line.replace("Version:", "").strip()
                elif line.startswith("Status:"):
                    status = line.replace("Status:", "").strip()
                    if "not-installed" in status:
                        status_not_installed = True
            if ver and status_not_installed:
                return ver
            if ver and not repo_ver:
                repo_ver = ver # fallback to first block
        return repo_ver
    except Exception:
        pass
def get_all_opkg_repo_versions(force=False):
    """Queries OPKG repo versions for managed packages (cached for 300s)."""
    now = time.time()
    if not force and _REPO_VERSIONS_CACHE["data"] and (now - _REPO_VERSIONS_CACHE["timestamp"] < 300):
        return _REPO_VERSIONS_CACHE["data"]

    opkg_versions = {}
    for s_id, meta in KNOWN_SERVICES.items():
        pkg = meta.get("package")
        if pkg:
            ver = get_opkg_repo_version(pkg)
            if ver:
                opkg_versions[s_id] = ver
                
    # Check alternate package names
    if "nfqws2" not in opkg_versions or not opkg_versions["nfqws2"]:
        opkg_versions["nfqws2"] = get_opkg_repo_version("nfqws2-keenetic") or get_opkg_repo_version("nfqws-keenetic-web") or get_opkg_repo_version("nfqws2")
    if "mosquitto" not in opkg_versions or not opkg_versions["mosquitto"]:
        opkg_versions["mosquitto"] = get_opkg_repo_version("mosquitto-ssl") or get_opkg_repo_version("mosquitto")

    _REPO_VERSIONS_CACHE["data"] = opkg_versions
    _REPO_VERSIONS_CACHE["timestamp"] = now
    return opkg_versions

def get_installed_versions(force=False):
    """Retrieves installed versions of major packages (cached for 60s)."""
    now = time.time()
    if not force and _VERSIONS_CACHE["data"] and (now - _VERSIONS_CACHE["timestamp"] < 60):
        return _VERSIONS_CACHE["data"]

    versions = {}
    installed_dict, _ = discover_services()
    
    for s_id in installed_dict.keys():
        if s_id == "tg-ws-proxy":
            tg_ver = get_opkg_package_version("tg-ws-proxy")
            if not tg_ver:
                try:
                    out = subprocess.check_output(["/opt/bin/tg-ws-proxy", "--version"], stderr=subprocess.STDOUT, text=True)
                    tg_ver = out.strip()
                except Exception:
                    tg_ver = "unknown"
            versions["tg-ws-proxy"] = tg_ver
        elif s_id == "usque":
            try:
                if os.path.exists("/opt/usr/bin/usque"):
                    out = subprocess.check_output(["/opt/usr/bin/usque", "version"], stderr=subprocess.STDOUT, text=True)
                    for line in out.splitlines():
                        if "version:" in line:
                            versions["usque"] = line.split("version:")[1].strip()
                            break
                    if "usque" not in versions:
                        versions["usque"] = out.strip().split("\n")[0]
                else:
                    versions["usque"] = "not installed"
            except Exception:
                versions["usque"] = "unknown"
        elif s_id == "tuya-mqtt-calibrator":
            versions["tuya-mqtt-calibrator"] = "installed"
        else:
            meta = KNOWN_SERVICES.get(s_id)
            pkg = meta.get("package") if meta else s_id
            ver = get_opkg_package_version(pkg) if pkg else None
            if not ver and s_id == "nfqws2":
                ver = get_opkg_package_version("nfqws2-keenetic") or get_opkg_package_version("nfqws-keenetic-web") or get_opkg_package_version("nfqws2")
            if not ver and s_id == "mosquitto":
                ver = get_opkg_package_version("mosquitto-ssl") or get_opkg_package_version("mosquitto")
            versions[s_id] = ver or "installed"

    _VERSIONS_CACHE["data"] = versions
    _VERSIONS_CACHE["timestamp"] = now
    return versions

def get_system_stats():
    """Gathers system stats (CPU, memory, disk)."""
    stats = {
        "cpu_load": "0.00 0.00 0.00",
        "mem_total": 0,
        "mem_free": 0,
        "mem_used_pct": 0.0,
        "disk_total": "0G",
        "disk_used": "0G",
        "disk_free": "0G",
        "disk_used_pct": 0.0
    }
    
    # CPU load
    try:
        with open("/proc/loadavg", "r") as f:
            stats["cpu_load"] = " ".join(f.read().split()[:3])
    except Exception:
        pass
        
    # Memory usage
    try:
        mem_total, mem_free, mem_cached, mem_buffers = 0, 0, 0, 0
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                key = parts[0].replace(":", "")
                val = int(parts[1])
                if key == "MemTotal":
                    mem_total = val
                elif key == "MemFree":
                    mem_free = val
                elif key == "Cached":
                    mem_cached = val
                elif key == "Buffers":
                    mem_buffers = val
        if mem_total > 0:
            # Active memory = Total - Free - Cached - Buffers
            mem_used = mem_total - mem_free - mem_cached - mem_buffers
            stats["mem_total"] = mem_total * 1024  # convert to bytes
            stats["mem_free"] = (mem_free + mem_cached + mem_buffers) * 1024
            stats["mem_used_pct"] = round((mem_used / mem_total) * 100, 1)
    except Exception as e:
        logging.error(f"Error parsing /proc/meminfo: {e}")

    # Disk usage
    try:
        # Check disk space of /opt
        df_out = subprocess.check_output(["df", "-h", "/opt"], text=True)
        lines = df_out.strip().split("\n")
        if len(lines) >= 2:
            cols = lines[1].split()
            if len(cols) >= 5:
                # Cols: Filesystem, Size, Used, Available, Use%, Mounted on
                stats["disk_total"] = cols[1]
                stats["disk_used"] = cols[2]
                stats["disk_free"] = cols[3]
                stats["disk_used_pct"] = float(cols[4].replace("%", ""))
    except Exception as e:
        logging.error(f"Error executing df: {e}")

    return stats

class RouterAPIHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        """Helper to append CORS headers to all responses."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self.handle_status()
        elif self.path in ["/", "/index.html", "/style.css", "/app.js"]:
            self.handle_static_file()
        else:
            self.send_error_response(404, "Not Found")

    def do_POST(self):
        # Read content length
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON payload")
            return

        if self.path == "/api/service":
            self.handle_service_action(data)
        elif self.path == "/api/update":
            self.handle_update(data)
        elif self.path == "/api/exec":
            self.handle_exec(data)
        else:
            self.send_error_response(404, "Not Found")

    def send_json_response(self, data, status_code=200):
        try:
            response_bytes = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            logging.error(f"Error sending JSON response: {e}")

    def send_error_response(self, status_code, message):
        self.send_json_response({"error": message}, status_code)

    def handle_static_file(self):
        filename = self.path
        if filename == "/":
            filename = "/index.html"
            
        file_path = os.path.join("/opt/share/router-control-center", filename.lstrip("/"))
        
        if not os.path.exists(file_path):
            self.send_error_response(404, f"File {filename} not found")
            return
            
        content_type = "text/plain"
        if filename.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif filename.endswith(".css"):
            content_type = "text/css; charset=utf-8"
        elif filename.endswith(".js"):
            content_type = "application/javascript; charset=utf-8"
            
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logging.error(f"Error serving static file {filename}: {e}")
            self.send_error_response(500, f"Error reading file: {str(e)}")

    def handle_status(self):
        logging.info("Status endpoint requested")
        
        installed_dict, catalog = discover_services()
        
        # Build list of services with current statuses
        service_statuses = {}
        services_detailed = []
        for s_id, s_info in installed_dict.items():
            status = get_service_status(s_info.get("script"), s_info.get("proc"))
            service_statuses[s_id] = status
            s_copy = dict(s_info)
            s_copy["status"] = status
            services_detailed.append(s_copy)
            
        # Build OPKG repository versions list (cached)
        opkg_versions = get_all_opkg_repo_versions()
            
        response = {
            "system": get_system_stats(),
            "versions": get_installed_versions(),
            "opkg_versions": opkg_versions,
            "services": service_statuses,
            "services_detailed": services_detailed,
            "catalog": catalog
        }
        self.send_json_response(response)

    def handle_service_action(self, data):
        service = data.get("service")
        action = data.get("action")
        
        if not service or not action:
            self.send_error_response(400, "Missing 'service' or 'action' parameter")
            return
            
        installed_dict, _ = discover_services()
        if service not in installed_dict:
            self.send_error_response(404, f"Service '{service}' is not installed")
            return
            
        s_info = installed_dict[service]

        if action == "uninstall":
            uninstall_pkg = s_info.get("uninstall_pkg")
            logging.info(f"Uninstall requested for {service} (pkg: {uninstall_pkg})")
            output_lines = []
            
            # Stop service first if running
            script_path = s_info.get("script")
            if script_path and os.path.exists(script_path):
                subprocess.run([script_path, "stop"], capture_output=True)
                output_lines.append(f"Служба {service} остановлена.")
                
            if uninstall_pkg:
                cmd = ["/opt/bin/opkg", "remove"] + uninstall_pkg.split()
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                output_lines.append(res.stdout + res.stderr)
                success = res.returncode == 0
            else:
                if script_path and os.path.exists(script_path):
                    os.chmod(script_path, 0o644)
                    output_lines.append(f"Скрипт {script_path} отключен.")
                success = True

            # Invalidate caches
            _VERSIONS_CACHE["data"] = None
            _REPO_VERSIONS_CACHE["data"] = None
            
            self.send_json_response({
                "success": success,
                "output": "\n".join(output_lines).strip(),
                "new_status": "not_installed"
            })
            return

        if action not in ["start", "stop", "restart", "status"]:
            self.send_error_response(400, f"Unsupported action '{action}'")
            return
            
        script_path = s_info.get("script")
        logging.info(f"Service action requested: {service} -> {action}")
        
        if not script_path or not os.path.exists(script_path):
            self.send_error_response(500, f"Init script for {service} not found")
            return
            
        # start/restart scripts can block up to 30s (e.g. usque wait_for_ip loop)
        cmd_timeout = 40 if action in ("start", "restart") else 10

        try:
            res = subprocess.run([script_path, action], capture_output=True, text=True, timeout=cmd_timeout)
            output = res.stdout + res.stderr
            success = res.returncode == 0

            # Recheck status
            new_status = get_service_status(script_path, s_info.get("proc"))

            self.send_json_response({
                "success": success,
                "exit_code": res.returncode,
                "output": output.strip(),
                "new_status": new_status
            })
        except subprocess.TimeoutExpired:
            # Script timed out (e.g. start blocked on wait_for_ip).
            # The service may already be running — check actual process status.
            logging.warning(f"Service action '{action}' on '{service}' timed out after {cmd_timeout}s — checking real status")
            new_status = get_service_status(script_path, s_info.get("proc"))
            self.send_json_response({
                "success": new_status == "running",
                "exit_code": -1,
                "output": f"Скрипт завершён по таймауту ({cmd_timeout}с). Реальный статус: {new_status}.",
                "new_status": new_status
            })
        except Exception as e:
            logging.error(f"Failed to execute service action {action} on {service}: {e}")
            self.send_error_response(500, f"Execution failed: {str(e)}")

    def handle_update(self, data):
        service = data.get("service")
        version = data.get("version")
        url = data.get("url")
        
        if not service or not version or not url:
            self.send_error_response(400, "Missing 'service', 'version', or 'url' parameter")
            return
            
        if service not in ["tg-ws-proxy", "usque"]:
            self.send_error_response(400, f"Updates not supported for service '{service}'")
            return
            
        logging.info(f"Update triggered for {service} to version {version} from {url}")
        
        # Run update in a helper function
        success, output = perform_service_update(service, version, url)
        
        self.send_json_response({
            "success": success,
            "output": output,
            "new_versions": get_installed_versions()
        })

    def handle_exec(self, data):
        command = data.get("command")
        if not command:
            self.send_error_response(400, "Missing 'command' parameter")
            return
            
        timeout = int(data.get("timeout", 180))
        logging.info(f"Executing manual command on router: {command} (timeout={timeout}s)")
        
        # Intercept opkg update to use resilient chunked updater
        cmd_strip = command.strip()
        if cmd_strip in ["/opt/bin/opkg update", "opkg update"]:
            if os.path.exists("/opt/scripts/opkg_update.py"):
                command = "python3 /opt/scripts/opkg_update.py"

        # Check for stale opkg.lock if opkg command
        if "opkg" in command:
            if os.path.exists("/opt/tmp/opkg.lock"):
                try:
                    res_p = subprocess.run(["pgrep", "opkg"], capture_output=True)
                    if res_p.returncode != 0:
                        os.remove("/opt/tmp/opkg.lock")
                except Exception:
                    pass

        # If running opkg install and package lists are missing/empty, run opkg update first
        if "opkg install" in command:
            lists_dir = "/opt/var/opkg-lists"
            has_lists = os.path.exists(lists_dir) and len(os.listdir(lists_dir)) > 0
            if not has_lists:
                if os.path.exists("/opt/scripts/opkg_update.py"):
                    subprocess.run(["python3", "/opt/scripts/opkg_update.py"], capture_output=True, timeout=120)
                else:
                    subprocess.run(["/opt/bin/opkg", "update"], capture_output=True, timeout=60)

        try:
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            output = res.stdout + res.stderr
            # If opkg command was run, invalidate cache
            if "opkg" in command:
                _VERSIONS_CACHE["data"] = None
                _REPO_VERSIONS_CACHE["data"] = None
            self.send_json_response({
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "output": output.strip()
            })
        except subprocess.TimeoutExpired as te:
            logging.error(f"Command '{command}' timed out after {timeout}s: {te}")
            try:
                subprocess.run(["killall", "-9", "wget", "opkg"], capture_output=True)
            except Exception:
                pass
            if os.path.exists("/opt/tmp/opkg.lock"):
                try:
                    os.remove("/opt/tmp/opkg.lock")
                except Exception:
                    pass
            self.send_json_response({
                "success": False,
                "exit_code": -1,
                "output": f"Команда прервана по таймауту ({timeout}с): {te}"
            }, status_code=200)
        except Exception as e:
            logging.error(f"Failed to execute manual command {command}: {e}")
            self.send_error_response(500, f"Execution failed: {str(e)}")

def perform_service_update(service, version, url):
    """Executes the specific upgrade logic for the requested service."""
    output = []
    
    def log_and_accumulate(msg):
        logging.info(msg)
        output.append(msg)

    # Make sure download dir exists
    tmp_dir = "/opt/tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    
    if service == "tg-ws-proxy":
        # Check download extension (.ipk)
        target_path = os.path.join(tmp_dir, f"tg-ws-proxy_{version}.ipk")
        log_and_accumulate(f"Downloading tg-ws-proxy package from {url}...")
        
        try:
            # We use urllib to download, or curl if urllib fails
            urllib.request.urlretrieve(url, target_path)
            log_and_accumulate(f"Download complete: {target_path}")
        except Exception as e:
            log_and_accumulate(f"urllib download failed ({e}), attempting curl fallback...")
            try:
                subprocess.run(["curl", "-L", "-o", target_path, url], check=True, capture_output=True)
                log_and_accumulate(f"Download complete via curl: {target_path}")
            except Exception as curl_err:
                log_and_accumulate(f"curl download failed: {curl_err}")
                return False, "\n".join(output)

        log_and_accumulate("Installing package using opkg...")
        try:
            # Check backup config files first to preserve secret.conf
            backup_configs = {}
            secret_conf_path = "/opt/etc/tg-ws-proxy/secret.conf"
            config_conf_path = "/opt/etc/tg-ws-proxy/config.conf"
            
            if os.path.exists(secret_conf_path):
                with open(secret_conf_path, "r") as f:
                    backup_configs["secret.conf"] = f.read()
            if os.path.exists(config_conf_path):
                with open(config_conf_path, "r") as f:
                    backup_configs["config.conf"] = f.read()
            
            # Install package
            res = subprocess.run(["/opt/bin/opkg", "install", target_path], capture_output=True, text=True, timeout=60)
            log_and_accumulate(res.stdout)
            if res.stderr:
                log_and_accumulate("opkg Warnings/Errors:\n" + res.stderr)
                
            if res.returncode != 0:
                log_and_accumulate(f"opkg install exited with code {res.returncode}")
                return False, "\n".join(output)

            # Restore configurations if they were wiped or modified
            if backup_configs:
                os.makedirs("/opt/etc/tg-ws-proxy", exist_ok=True)
                if "secret.conf" in backup_configs:
                    with open(secret_conf_path, "w") as f:
                        f.write(backup_configs["secret.conf"])
                    os.chmod(secret_conf_path, 0o600)
                    log_and_accumulate("Restored secret.conf configuration backup.")
                if "config.conf" in backup_configs:
                    with open(config_conf_path, "w") as f:
                        f.write(backup_configs["config.conf"])
                    log_and_accumulate("Restored config.conf configuration backup.")

            # Restart the service
            script_path = SERVICES["tg-ws-proxy"]["script"]
            if os.path.exists(script_path):
                log_and_accumulate("Restarting tg-ws-proxy service...")
                restart_res = subprocess.run([script_path, "restart"], capture_output=True, text=True)
                log_and_accumulate(restart_res.stdout + restart_res.stderr)
            
            # Clean up ipk file
            if os.path.exists(target_path):
                os.remove(target_path)
                
            log_and_accumulate("tg-ws-proxy successfully updated!")
            return True, "\n".join(output)
            
        except Exception as ex:
            log_and_accumulate(f"Installation error: {str(ex)}")
            return False, "\n".join(output)

    elif service == "usque":
        target_path = os.path.join(tmp_dir, f"usque_{version}.zip")
        log_and_accumulate(f"Downloading usque archive from {url}...")
        
        try:
            urllib.request.urlretrieve(url, target_path)
            log_and_accumulate(f"Download complete: {target_path}")
        except Exception as e:
            log_and_accumulate(f"urllib download failed ({e}), attempting curl fallback...")
            try:
                subprocess.run(["curl", "-L", "-o", target_path, url], check=True, capture_output=True)
                log_and_accumulate(f"Download complete via curl: {target_path}")
            except Exception as curl_err:
                log_and_accumulate(f"curl download failed: {curl_err}")
                return False, "\n".join(output)

        log_and_accumulate("Extracting usque binary from archive...")
        extract_dir = os.path.join(tmp_dir, f"usque_extracted_{version}")
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(target_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            log_and_accumulate("Extraction completed.")
        except Exception as zip_err:
            log_and_accumulate(f"Failed to extract zip file: {zip_err}")
            return False, "\n".join(output)
            
        # Locate usque binary in extracted dir
        binary_src = None
        for root, dirs, files in os.walk(extract_dir):
            if "usque" in files:
                binary_src = os.path.join(root, "usque")
                break
                
        if not binary_src:
            log_and_accumulate("Could not find 'usque' binary in the extracted archive structure.")
            # Clean up
            shutil.rmtree(extract_dir, ignore_errors=True)
            if os.path.exists(target_path):
                os.remove(target_path)
            return False, "\n".join(output)

        log_and_accumulate("Stopping usque service...")
        script_path = SERVICES["usque"]["script"]
        if os.path.exists(script_path):
            subprocess.run([script_path, "stop"], capture_output=True)

        # Backup old binary
        binary_dest = "/opt/usr/bin/usque"
        backup_dest = f"{binary_dest}.bak"
        if os.path.exists(binary_dest):
            log_and_accumulate(f"Creating backup of existing binary to {backup_dest}...")
            shutil.copy2(binary_dest, backup_dest)

        log_and_accumulate(f"Replacing binary at {binary_dest}...")
        try:
            shutil.copy2(binary_src, binary_dest)
            os.chmod(binary_dest, 0o755)
            log_and_accumulate("New binary copied and permissions set.")
        except Exception as copy_err:
            log_and_accumulate(f"Copying binary failed: {copy_err}. Attempting rollback from backup...")
            if os.path.exists(backup_dest):
                shutil.copy2(backup_dest, binary_dest)
                os.chmod(binary_dest, 0o755)
            shutil.rmtree(extract_dir, ignore_errors=True)
            if os.path.exists(target_path):
                os.remove(target_path)
            return False, "\n".join(output)

        log_and_accumulate("Starting usque service...")
        if os.path.exists(script_path):
            restart_res = subprocess.run([script_path, "start"], capture_output=True, text=True)
            log_and_accumulate(restart_res.stdout + restart_res.stderr)

        # Cleanup
        shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(target_path):
            os.remove(target_path)
            
        log_and_accumulate("usque successfully updated!")
        return True, "\n".join(output)

    return False, "Unknown service update logic"

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
    server_address = ('', PORT)
    httpd = SafeHTTPServer(server_address, RouterAPIHandler)
    logging.info(f"Router API running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutting down.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
