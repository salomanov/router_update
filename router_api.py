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
import select
import logging
import logging.handlers
import time
import re
import hashlib
import hmac
import secrets
import shlex
import tempfile
import threading
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import TCPServer, ThreadingMixIn

PORT = 8089
BIND_ADDR = os.environ.get("GROUTER_BIND", "0.0.0.0")
AUTH_FILE = "/opt/etc/router-api.auth"
SESSIONS_FILE = "/opt/etc/router-api.sessions"
LOG_FILE = "/opt/var/log/router_api.log"
PROFILE_FILE = "/opt/etc/grouter/profile.json"
DISABLED_DIR = "/opt/etc/init.d.disabled"
INITIAL_PASSWORD_FILE = "/opt/etc/grouter/initial_password"
# Optional install-time inputs, written by install.sh and removed once hashed
DEFAULT_PASSWORD_FILE = "/opt/etc/grouter/default_password"
RANDOM_PASSWORD_FILE = "/opt/etc/grouter/random_password"

# ttyd listens on loopback only; the public port is served by an authenticated TCP proxy
TTYD_INTERNAL_PORT = 7682
TTYD_PUBLIC_PORT = 7681
SESSION_COOKIE = "grouter_session"

# Fallbacks for local / dev testing
if not os.path.exists("/opt/etc") and not os.path.exists("/opt"):
    AUTH_FILE = os.path.join(os.getcwd(), "router-api.auth")
    SESSIONS_FILE = os.path.join(os.getcwd(), "router-api.sessions")
    LOG_FILE = os.path.join(os.getcwd(), "router_api.log")
    PROFILE_FILE = os.path.join(os.getcwd(), "profile.json")
    DISABLED_DIR = os.path.join(os.getcwd(), "init.d.disabled")
    INITIAL_PASSWORD_FILE = os.path.join(os.getcwd(), "initial_password")
    DEFAULT_PASSWORD_FILE = os.path.join(os.getcwd(), "default_password")
    RANDOM_PASSWORD_FILE = os.path.join(os.getcwd(), "random_password")

# Configure Logging (single rotating handler; stdout is redirected to the same file by the init script)
os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
logger = logging.getLogger("router_api")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    try:
        fh = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=512 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)
    except Exception:
        pass

# Global Locks and Caches
_CACHE_LOCK = threading.Lock()
_VERSIONS_CACHE = {"data": None, "timestamp": 0}
_REPO_VERSIONS_CACHE = {"data": None, "timestamp": 0}
_STATS_CACHE = {"data": None, "timestamp": 0}
_SERVICES_CACHE = {"data": None, "timestamp": 0}
_SERVICE_STATUS_CACHE = {"data": None, "timestamp": 0}
_SESSIONS = {}
_SESSIONS_LOCK = threading.Lock()
_LOGIN_ATTEMPTS = {}
_LOGIN_LOCK = threading.Lock()
_LONG_OP_LOCK = threading.Lock()
_EXEC_LOCK = threading.Lock()

# Master Catalog of Supported Applications & Services
KNOWN_SERVICES = {
    "ttyd": {
        "name": "Web Terminal (ttyd / PuTTY)",
        "desc": "Полноценный веб-терминал SSH/PuTTY в браузере (порт 7681)",
        "script_prefixes": ["S96ttyd"],
        "proc": "ttyd",
        "package": "ttyd",
        "git": "https://github.com/tsl0922/ttyd",
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
        "install_url": "https://raw.githubusercontent.com/salomanov/router_update/main/install_nfqws2.sh",
        "is_core": True
    },
    "tg-ws-proxy": {
        "name": "tg-ws-proxy",
        "desc": "Прокси Telegram MTProto WebSockets (Go)",
        "script_prefixes": ["S99tg-ws-proxy", "S61tg-ws-proxy"],
        "proc": "tg-ws-proxy",
        "package": "tg-ws-proxy",
        "git": "https://github.com/spatiumstas/tg-ws-proxy-go",
        "install_url": "https://raw.githubusercontent.com/salomanov/router_update/main/install_tg_proxy.sh",
        "is_core": True
    },
    "dropbear": {
        "name": "SSH (Dropbear)",
        "desc": "Сервер удаленного доступа SSH",
        "script_prefixes": ["S51dropbear"],
        "proc": "dropbear",
        "package": "dropbear",
        "git": "https://github.com/mkj/dropbear",
        "is_core": True
    },
    "tailscale": {
        "name": "Tailscale VPN",
        "desc": "Mesh VPN / Exit Node для удаленного доступа",
        "script_prefixes": ["S06tailscale", "S06tailscaled"],
        "proc": "tailscaled",
        "package": "tailscale",
        "git": "https://github.com/tailscale/tailscale",
        "install_url": "https://raw.githubusercontent.com/salomanov/router_update/main/install_tailscale.sh",
        "is_core": True
    },
    "mosquitto": {
        "name": "Mosquitto MQTT",
        "desc": "Брокер сообщений для умного дома",
        "script_prefixes": ["S80mosquitto"],
        "proc": "mosquitto",
        "package": "mosquitto-ssl",
        "git": "https://github.com/eclipse-mosquitto/mosquitto",
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
        "install_url": "https://raw.githubusercontent.com/salomanov/router_update/main/install_opds.sh",
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
        "install_url": "https://raw.githubusercontent.com/salomanov/router_update/main/install_tuya_calibrator.sh",
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
        "install_url": "https://raw.githubusercontent.com/salomanov/router_update/main/install_usque.sh",
        "uninstall_pkg": None,
        "is_core": False
    }
}

# --- Authentication Subsystem ---

PBKDF2_ITERATIONS = 100000
MIN_PASSWORD_LEN = 10
MAX_LOGIN_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 300

# Standard password for a home router panel. The owner asked to keep it as the
# default, so it is stored once here and can be overridden per-install:
#   GROUTER_DEFAULT_PASSWORD=<own value>
#   GROUTER_RANDOM_PASSWORD=1     -> generate a random one-time password instead
# The panel always offers a working "change password" action.
DEFAULT_ADMIN_PASSWORD = os.environ.get("GROUTER_DEFAULT_PASSWORD", "Salomanov").strip()
RANDOM_PASSWORD_MODE = os.environ.get("GROUTER_RANDOM_PASSWORD", "").strip().lower() in (
    "1", "true", "yes", "on"
)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return salt, hashed


def read_auth():
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_auth(data):
    tmp = AUTH_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, AUTH_FILE)


def _read_secret_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
        return value
    except Exception:
        return ""


def _init_password_settings():
    """Resolve the initial password mode from install.sh inputs / environment.

    Precedence: GROUTER_RANDOM_PASSWORD / random_password marker, then
    GROUTER_DEFAULT_PASSWORD / default_password file, then the built-in standard one.
    """
    secure = RANDOM_PASSWORD_MODE or os.path.exists(RANDOM_PASSWORD_FILE)
    custom = (os.environ.get("GROUTER_DEFAULT_PASSWORD", "") or "").strip()
    if not custom:
        custom = _read_secret_file(DEFAULT_PASSWORD_FILE)
    return secure, custom


def init_auth():
    """Create the auth file on first start.

    Default mode: the standard password (DEFAULT_ADMIN_PASSWORD, "Salomanov") is
    hashed into AUTH_FILE. No forced change, but the panel keeps a working
    "change password" action.

    Secure mode (GROUTER_RANDOM_PASSWORD=1): a random password is generated into
    INITIAL_PASSWORD_FILE (0600) and must be changed on first login.

    Neither mode has a code-level fallback: verify_credentials() only reads AUTH_FILE.
    """
    if os.path.exists(AUTH_FILE):
        return None

    secure_mode, custom_password = _init_password_settings()
    if secure_mode:
        password = secrets.token_urlsafe(9)
    else:
        password = custom_password or DEFAULT_ADMIN_PASSWORD or "Salomanov"
    salt, hashed = hash_password(password)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(AUTH_FILE)), exist_ok=True)
    except Exception:
        pass
    write_auth({
        "username": "admin",
        "salt": salt,
        "hash": hashed,
        "must_change_password": secure_mode,
        "created_at": time.time(),
    })

    # The plaintext install-time input is no longer needed once hashed
    for path in (DEFAULT_PASSWORD_FILE, RANDOM_PASSWORD_FILE):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    if secure_mode:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(INITIAL_PASSWORD_FILE)), exist_ok=True)
            with open(INITIAL_PASSWORD_FILE, "w", encoding="utf-8") as f:
                f.write(password + "\n")
            os.chmod(INITIAL_PASSWORD_FILE, 0o600)
        except Exception:
            pass
        logger.info("Initial admin password generated. Read it once from %s", INITIAL_PASSWORD_FILE)
        return password

    # Standard-password mode: never leave a stale one-time password file behind
    try:
        if os.path.exists(INITIAL_PASSWORD_FILE):
            os.remove(INITIAL_PASSWORD_FILE)
    except Exception:
        pass
    logger.info(
        "Admin account initialised with the standard password; it can be changed in the panel."
    )
    return None


def verify_credentials(username, password):
    """Verify against the stored PBKDF2 hash. There is no fallback/backdoor path."""
    u_clean = (username or "").strip().lower()
    data = read_auth() or {}
    saved_u = (data.get("username") or "admin").strip().lower()
    salt = data.get("salt") or ""
    expected = data.get("hash") or ""
    if not salt or not expected or not u_clean or not password:
        return False
    if not hmac.compare_digest(saved_u, u_clean):
        return False
    p_clean = (password or "").strip()
    _, computed = hash_password(p_clean, salt)
    return hmac.compare_digest(expected, computed)


def must_change_password():
    data = read_auth() or {}
    return bool(data.get("must_change_password"))


def change_password(old_password, new_password):
    data = read_auth()
    if not data:
        return False, "Файл аутентификации не найден"
    if not verify_credentials(data.get("username", "admin"), old_password):
        return False, "Текущий пароль неверен"
    new_password = (new_password or "").strip()
    if len(new_password) < MIN_PASSWORD_LEN:
        return False, f"Новый пароль должен быть не короче {MIN_PASSWORD_LEN} символов"
    salt, hashed = hash_password(new_password)
    data["salt"] = salt
    data["hash"] = hashed
    data["must_change_password"] = False
    data["changed_at"] = time.time()
    write_auth(data)
    # Password change invalidates every session (including the current one)
    with _SESSIONS_LOCK:
        _SESSIONS.clear()
    save_sessions()
    try:
        if os.path.exists(INITIAL_PASSWORD_FILE):
            os.remove(INITIAL_PASSWORD_FILE)
    except Exception:
        pass
    return True, "Пароль изменён"


def load_sessions():
    global _SESSIONS
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            now = time.time()
            valid = {t: v for t, v in saved.items() if v.get("expires", 0) > now}
            with _SESSIONS_LOCK:
                _SESSIONS = valid
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")


def save_sessions():
    """Persist sessions. MUST NOT be called while _SESSIONS_LOCK is held by this thread."""
    try:
        with _SESSIONS_LOCK:
            now = time.time()
            valid = {t: v for t, v in _SESSIONS.items() if v.get("expires", 0) > now}
        tmp = SESSIONS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(valid, f)
        try:
            os.chmod(tmp, 0o600)
        except Exception:
            pass
        os.replace(tmp, SESSIONS_FILE)
    except Exception as e:
        logger.error(f"Error saving sessions: {e}")


def create_session(username):
    token = secrets.token_hex(24)
    expires = time.time() + (7 * 86400)  # 7 days
    with _SESSIONS_LOCK:
        _SESSIONS[token] = {"username": username, "expires": expires, "ip": ""}
    save_sessions()
    return token, expires


def validate_session(token):
    if not token:
        return False
    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(token)
        if sess and sess.get("expires", 0) > time.time():
            return True
        if sess:
            del _SESSIONS[token]
    return False


def session_username(token):
    """Username behind a session token (for audit logs)."""
    if not token:
        return ""
    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(token)
        if sess and sess.get("expires", 0) > time.time():
            return sess.get("username", "")
    return ""


def revoke_session(token):
    """Remove one session. Fix: never call save_sessions() while holding the lock."""
    with _SESSIONS_LOCK:
        existed = _SESSIONS.pop(token, None) is not None
    if existed:
        save_sessions()
    return existed


def revoke_user_sessions(username):
    with _SESSIONS_LOCK:
        doomed = [t for t, v in _SESSIONS.items() if v.get("username") == username]
        for t in doomed:
            _SESSIONS.pop(t, None)
    if doomed:
        save_sessions()


def check_login_allowed(ip):
    now = time.time()
    with _LOGIN_LOCK:
        rec = _LOGIN_ATTEMPTS.get(ip)
        if not rec:
            return True
        if now - rec["since"] > LOGIN_LOCKOUT_SECONDS:
            _LOGIN_ATTEMPTS.pop(ip, None)
            return True
        return rec["count"] < MAX_LOGIN_FAILURES


def register_login_failure(ip):
    now = time.time()
    with _LOGIN_LOCK:
        rec = _LOGIN_ATTEMPTS.get(ip)
        if not rec or now - rec["since"] > LOGIN_LOCKOUT_SECONDS:
            _LOGIN_ATTEMPTS[ip] = {"count": 1, "since": now}
        else:
            rec["count"] += 1


def reset_login_attempts(ip):
    with _LOGIN_LOCK:
        _LOGIN_ATTEMPTS.pop(ip, None)


def parse_cookie_token(cookie_header):
    if not cookie_header:
        return ""
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name == SESSION_COOKIE:
            return value.strip()
    return ""

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
    """Service status. Process check wins; script output is only a fallback.

    Negative statuses are matched BEFORE positive ones: "usque is not running"
    contains the substring "running", which previously produced false positives.
    """
    if proc_name and get_process_status(proc_name):
        return "running"
    if not script_path or not os.path.exists(script_path):
        return "stopped"
    if not os.access(script_path, os.X_OK):
        return "stopped"
    try:
        res = subprocess.run([script_path, "status"], capture_output=True, text=True, timeout=5)
        out = (res.stdout + res.stderr).lower()
        if ("not running" in out or "stopped" in out or " dead" in out
                or "inactive" in out or "no such process" in out or "is not" in out):
            return "stopped"
        if "running" in out or "alive" in out:
            return "running"
    except Exception:
        pass
    if proc_name and get_process_status(proc_name):
        return "running"
    return "stopped"

def discover_services(force=False):
    """Scans /opt/etc/init.d/ for all services.

    Always returns a dict; entries always carry a 'script' path string.
    Result is cached for a few seconds because /api/status is polled by the UI.
    """
    global _SERVICES_CACHE
    now = time.time()
    with _CACHE_LOCK:
        if (not force and _SERVICES_CACHE["data"] is not None
                and (now - _SERVICES_CACHE["timestamp"] < 3)):
            return _SERVICES_CACHE["data"]

    services = {}
    init_dir = "/opt/etc/init.d"

    try:
        script_files = [f for f in os.listdir(init_dir) if f.startswith("S")]
    except Exception:
        script_files = []

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
            # Custom scripts have no opkg package: uninstall = move script to DISABLED_DIR
            "uninstall_pkg": None,
            "custom": True
        }

    with _CACHE_LOCK:
        _SERVICES_CACHE["data"] = services
        _SERVICES_CACHE["timestamp"] = now
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
            usque_path = resolve_usque_path()
            if os.path.exists(usque_path):
                try:
                    res = subprocess.run([usque_path, "-v"], capture_output=True, text=True, timeout=3)
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

def parse_version(value):
    """Turn 'v0.9.2-1' / '0.7.2' / '1:2.3-4' into a comparable tuple."""
    if not value:
        return ()
    text = str(value).strip().lstrip("vV")
    if ":" in text:
        text = text.split(":", 1)[1]
    if "-" in text:
        text = text.split("-", 1)[0]
    parts = []
    for chunk in re.split(r"[._]", text):
        m = re.match(r"^(\d+)(.*)$", chunk)
        if m:
            parts.append(int(m.group(1)))
            if m.group(2):
                parts.append(m.group(2))
        elif chunk:
            parts.append(chunk)
    return tuple(parts)


def is_newer_version(available, current):
    """True only if `available` is strictly newer than `current`.

    Guards against '0.7.2' vs '0.7.2-1' and 'v0.9.2' vs '0.9.2' false positives.
    """
    if not available or not current:
        return False
    if available == current:
        return False
    try:
        a = parse_version(available)
        c = parse_version(current)
        if a and c and a != c:
            # Compare element-wise, tolerating int/str mismatches
            for x, y in zip(a, c):
                if x == y:
                    continue
                if isinstance(x, int) and isinstance(y, int):
                    return x > y
                return str(x) > str(y)
            return len(a) > len(c)
    except Exception:
        pass
    return False


def get_service_statuses(services, force=False):
    """Status for every discovered service, cached briefly (the UI polls every 6s)."""
    global _SERVICE_STATUS_CACHE
    now = time.time()
    with _CACHE_LOCK:
        if (not force and _SERVICE_STATUS_CACHE["data"] is not None
                and (now - _SERVICE_STATUS_CACHE["timestamp"] < 3)):
            return _SERVICE_STATUS_CACHE["data"]

    statuses = {}
    for s_id, s_info in services.items():
        statuses[s_id] = get_service_status(s_info.get("script"), s_info.get("proc"))

    with _CACHE_LOCK:
        _SERVICE_STATUS_CACHE["data"] = statuses
        _SERVICE_STATUS_CACHE["timestamp"] = now
    return statuses


def load_profile():
    """Read the desired-state profile (packages + services + repo configs)."""
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    def clean_list(key):
        raw = data.get(key) or []
        if not isinstance(raw, list):
            return []
        return [str(x).strip() for x in raw if str(x).strip()]

    return {
        "name": str(data.get("name") or "default"),
        "packages": clean_list("packages"),
        "services": clean_list("services"),
        "repo_conf": clean_list("repo_conf"),
    }


def build_plan():
    """Dry-run diff between the profile and the router state. Changes nothing."""
    profile = load_profile()
    repo_versions = get_all_opkg_repo_versions()
    services = discover_services()
    items = []

    for pkg in profile["packages"]:
        current = get_opkg_package_version(pkg)
        available = repo_versions.get(pkg)
        if current == "unknown":
            state = "missing"
        elif is_newer_version(available, current):
            state = "outdated"
        else:
            state = "ok"
        items.append({
            "name": pkg, "type": "package", "current": current,
            "available": available, "state": state
        })

    known_services = set()
    for info in services.values():
        script = info.get("script") or ""
        known_services.add(os.path.basename(script) if script else "")
        if info.get("package"):
            known_services.add(info["package"])

    for svc in profile["services"]:
        # A profile service entry may be an init script name or a package name
        present = any(svc == n or svc in n for n in known_services if n)
        items.append({
            "name": svc, "type": "service",
            "current": "present" if present else "missing",
            "available": None, "state": "ok" if present else "missing"
        })

    installed_packages = sorted({i["package"] for i in services.values() if i.get("package")})
    extra = [p for p in installed_packages if p not in profile["packages"]]
    summary = {
        "missing": [i["name"] for i in items if i["state"] == "missing"],
        "outdated": [i["name"] for i in items if i["state"] == "outdated"],
        "ok": [i["name"] for i in items if i["state"] == "ok"],
    }
    return {
        "profile": profile,
        "items": items,
        "extra": extra,
        "summary": summary,
        "in_sync": not summary["missing"] and not summary["outdated"],
    }


def download_and_run_script(url, timeout=600):
    """Download an installer to a file, verify it, then run it.

    Piping curl into sh hides download failures (pipeline status belongs to `sh`),
    and BusyBox ash has no `pipefail`.
    """
    if not url or not re.match(r"^https?://", url):
        return False, "Некорректный URL установщика"

    tmp_dir = "/opt/tmp" if os.path.isdir("/opt/tmp") else tempfile.gettempdir()
    try:
        os.makedirs(tmp_dir, exist_ok=True)
    except Exception:
        pass
    script_path = os.path.join(tmp_dir, "grouter-install-%s.sh" % secrets.token_hex(4))

    try:
        download = subprocess.run(
            ["curl", "-fsSL", "--max-time", "120", "-o", script_path, url],
            capture_output=True, text=True, timeout=180
        )
        if download.returncode != 0:
            return False, "Не удалось скачать установщик %s: %s" % (
                url, (download.stderr or "").strip())
        if not os.path.exists(script_path) or os.path.getsize(script_path) == 0:
            return False, "Скачанный установщик пуст: %s" % url

        run = subprocess.run(["sh", script_path], capture_output=True, text=True, timeout=timeout)
        output = (run.stdout + run.stderr).strip()
        return run.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Установщик превысил лимит времени (%ss)" % timeout
    except Exception as e:
        return False, "Ошибка установки: %s" % e
    finally:
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass


def opkg_update_lists():
    """Refresh opkg lists. Best effort: failure is reported, not fatal."""
    if not os.path.exists("/opt/bin/opkg"):
        return False, "opkg не найден"
    try:
        res = subprocess.run(["/opt/bin/opkg", "update"], capture_output=True, text=True, timeout=180)
        return res.returncode == 0, (res.stdout + res.stderr).strip()
    except Exception as e:
        return False, str(e)


def invalidate_caches():
    with _CACHE_LOCK:
        _VERSIONS_CACHE["data"] = None
        _REPO_VERSIONS_CACHE["data"] = None
        _SERVICES_CACHE["data"] = None
        _SERVICE_STATUS_CACHE["data"] = None


def apply_plan(script_timeout=900):
    """Bring the router to the profile state. Idempotent; returns a step report."""
    steps = []
    before = build_plan()
    steps.append({
        "step": "plan", "ok": True,
        "output": "не хватает: %s, устарело: %s" % (
            ", ".join(before["summary"]["missing"]) or "нет",
            ", ".join(before["summary"]["outdated"]) or "нет")
    })

    todo = before["summary"]["missing"] + before["summary"]["outdated"]
    if todo:
        ok, out = opkg_update_lists()
        steps.append({"step": "opkg update", "ok": ok, "output": out[-2000:]})

    for pkg in before["summary"]["missing"]:
        try:
            res = subprocess.run(["/opt/bin/opkg", "install"] + pkg.split(),
                                 capture_output=True, text=True, timeout=300)
            steps.append({"step": "install %s" % pkg, "ok": res.returncode == 0,
                          "output": (res.stdout + res.stderr).strip()[-2000:]})
        except Exception as e:
            steps.append({"step": "install %s" % pkg, "ok": False, "output": str(e)})

    for pkg in before["summary"]["outdated"]:
        try:
            res = subprocess.run(["/opt/bin/opkg", "upgrade"] + pkg.split(),
                                 capture_output=True, text=True, timeout=300)
            steps.append({"step": "upgrade %s" % pkg, "ok": res.returncode == 0,
                          "output": (res.stdout + res.stderr).strip()[-2000:]})
        except Exception as e:
            steps.append({"step": "upgrade %s" % pkg, "ok": False, "output": str(e)})

    # Missing services declared in the profile: run their catalog installer
    services = discover_services(force=True)
    service_names = [i.get("script") or "" for i in services.values()]
    for svc in load_profile()["services"]:
        if any(svc in name for name in service_names if name):
            continue
        meta = KNOWN_SERVICES.get(svc, {})
        url = meta.get("install_url")
        if not url:
            steps.append({"step": "service %s" % svc, "ok": False,
                          "output": "нет установщика в каталоге"})
            continue
        ok, out = download_and_run_script(url, timeout=script_timeout)
        steps.append({"step": "service %s" % svc, "ok": ok, "output": out[-4000:]})
        if not ok:
            break

    invalidate_caches()
    after = build_plan()
    logger.info("apply finished: success=%s missing=%s outdated=%s",
                after["in_sync"], after["summary"]["missing"], after["summary"]["outdated"])
    return {"success": after["in_sync"], "steps": steps, "plan": after,
            "remaining": after["summary"]}


def update_all_packages():
    """Upgrade every package that has a newer version. One failure never aborts the run."""
    results = []
    ok, out = opkg_update_lists()
    results.append({"target": "opkg update", "state": "ok" if ok else "error",
                    "output": out[-1500:]})

    repo_versions = get_all_opkg_repo_versions(force=True)
    services = discover_services()
    targets = {}

    for s_id, info in services.items():
        if info.get("package"):
            targets[info["package"]] = s_id
    for pkg in load_profile()["packages"]:
        targets.setdefault(pkg, None)

    for pkg, s_id in sorted(targets.items()):
        current = get_opkg_package_version(pkg)
        available = repo_versions.get(pkg)
        if not is_newer_version(available, current):
            results.append({"target": pkg, "state": "up-to-date", "current": current,
                            "available": available})
            continue
        try:
            res = subprocess.run(["/opt/bin/opkg", "upgrade"] + pkg.split(),
                                 capture_output=True, text=True, timeout=300)
            results.append({
                "target": pkg,
                "state": "updated" if res.returncode == 0 else "error",
                "current": current,
                "available": available,
                "output": (res.stdout + res.stderr).strip()[-1500:],
            })
            if res.returncode == 0 and s_id:
                script = services.get(s_id, {}).get("script")
                if script:
                    try:
                        subprocess.run([script, "restart"], capture_output=True, timeout=30)
                    except Exception:
                        pass
        except Exception as e:
            results.append({"target": pkg, "state": "error", "current": current,
                            "error": str(e)})

    invalidate_caches()
    summary = {
        "updated": sum(1 for r in results if r["state"] == "updated"),
        "up_to_date": sum(1 for r in results if r["state"] == "up-to-date"),
        "errors": sum(1 for r in results if r["state"] == "error"),
    }
    return {"success": summary["errors"] == 0, "summary": summary, "results": results}


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
        """CORS only for the panel's own origin.

        A wildcard would let any website read the API in the user's browser
        (status, versions, plan). Echo the Origin only when it matches this host.
        """
        origin = (self.headers.get("Origin") or "").strip()
        host = (self.headers.get("Host") or "").strip()
        if not origin or not host:
            return
        if origin in ("http://" + host, "https://" + host):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
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

    def get_auth_token(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1].strip()
        return ""

    def is_authenticated(self):
        """Bearer token for writes; session cookie accepted for GET only.

        Query-string tokens (?token=...) are NOT accepted: they end up in browser
        history, Referer headers and router logs.
        """
        token = self.get_auth_token()
        if token and validate_session(token):
            return True
        if self.command == "GET":
            cookie_token = parse_cookie_token(self.headers.get("Cookie", ""))
            if cookie_token and validate_session(cookie_token):
                return True
        return False

    def password_change_blocked(self, clean_path):
        """While the generated password is unchanged, only a tiny allowlist works."""
        if not must_change_password():
            return False
        return clean_path not in ("/api/password", "/api/auth/check", "/api/status", "/api/logout", "/api/plan")

    def do_GET(self):
        try:
            clean_path = self.path.split("?")[0]
            if clean_path in ["/", "/index.html", "/style.css", "/app.js", "/favicon.ico"]:
                self.handle_static_file(clean_path)
                return

            if not self.is_authenticated():
                self.send_error_response(401, "Unauthorized. Please login.")
                return

            if self.password_change_blocked(clean_path):
                self.send_json_response({
                    "error": "password_change_required",
                    "must_change_password": True
                }, status_code=403)
                return

            if clean_path == "/api/status":
                self.handle_status()
            elif clean_path == "/api/auth/check":
                self.send_json_response({
                    "authenticated": True,
                    "username": (read_auth() or {}).get("username", "admin"),
                    "must_change_password": must_change_password()
                })
            elif clean_path == "/api/plan":
                self.handle_plan()
            elif clean_path == "/api/ttyd/status":
                self.send_json_response({
                    "installed": os.path.exists("/opt/bin/ttyd"),
                    "running": get_process_status("ttyd"),
                    "port": TTYD_PUBLIC_PORT
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

            # All other POST endpoints require a Bearer token (never a cookie)
            if not self.is_authenticated():
                self.send_error_response(401, "Unauthorized. Please login.")
                return

            if self.password_change_blocked(clean_path):
                self.send_json_response({
                    "error": "password_change_required",
                    "must_change_password": True
                }, status_code=403)
                return

            if clean_path == "/api/logout":
                token = self.get_auth_token()
                revoke_session(token)
                cookie_token = parse_cookie_token(self.headers.get("Cookie", ""))
                if cookie_token and cookie_token != token:
                    revoke_session(cookie_token)
                # Clear the session cookie as well
                self.send_json_response_with_cookie({"success": True}, "", 0)
            elif clean_path == "/api/password":
                self.handle_password_change(data)
            elif clean_path == "/api/apply":
                self.handle_apply(data)
            elif clean_path == "/api/update_all":
                self.handle_update_all(data)
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
        ip = self.client_address[0] if self.client_address else "unknown"

        if not username or not password:
            self.send_error_response(400, "Username and password required")
            return

        if not check_login_allowed(ip):
            logger.warning(f"Login blocked (too many failures) from {ip}")
            self.send_error_response(429, "Слишком много попыток входа. Повторите через 5 минут.")
            return

        if verify_credentials(username, password):
            reset_login_attempts(ip)
            token, expires = create_session(username)
            logger.info(f"User '{username}' logged in from {ip}")
            self.send_json_response_with_cookie(
                {
                    "success": True,
                    "token": token,
                    "username": username,
                    "must_change_password": must_change_password(),
                    "expires_in": int(expires - time.time())
                },
                token,
                7 * 86400
            )
        else:
            register_login_failure(ip)
            logger.warning(f"Failed login attempt for user '{username}' from {ip}")
            self.send_error_response(401, "Неверный логин или пароль")

    def handle_password_change(self, data):
        old_password = (data.get("old_password") or "").strip()
        new_password = (data.get("new_password") or "").strip()
        if not old_password or not new_password:
            self.send_error_response(400, "Нужны old_password и new_password")
            return
        ok, message = change_password(old_password, new_password)
        if not ok:
            logger.warning("Password change rejected")
            self.send_error_response(400, message)
            return
        logger.info("Admin password changed; all sessions revoked")
        self.send_json_response({"success": True, "message": message})

    def send_json_response_with_cookie(self, data, token, max_age):
        try:
            response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_cors_headers()
            self.send_header(
                "Set-Cookie",
                f"{SESSION_COOKIE}={token}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Lax"
            )
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            logger.error(f"Failed to send login response: {e}")

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
            os.path.join("/opt/share/router-control-center", filename),
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
        statuses = get_service_statuses(services)
        versions = get_installed_versions()
        repo_versions = get_all_opkg_repo_versions()
        services_status = {}
        services_detailed = []

        for s_id, s_info in services.items():
            status = statuses.get(s_id, "stopped")
            current = versions.get(s_id)
            available = repo_versions.get(s_info.get("package")) if s_info.get("package") else None
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
                "current_version": current,
                "available_version": available,
                "update_available": is_newer_version(available, current),
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
                    "install_url": s_info.get("install_url"),
                    "installable": bool(s_info.get("install_url") or s_info.get("package")),
                    "installed": False,
                    "port": s_info.get("port")
                })

        payload = {
            "system": get_system_stats(),
            "versions": versions,
            "opkg_versions": repo_versions,
            "services": services_status,
            "services_detailed": services_detailed,
            "catalog": catalog,
            "updates_available": sum(1 for d in services_detailed if d["update_available"]),
            "must_change_password": must_change_password()
        }
        self.send_json_response(payload)

    def handle_plan(self):
        try:
            self.send_json_response(build_plan())
        except Exception as e:
            logger.error(f"Plan failed: {e}", exc_info=True)
            self.send_error_response(500, f"Не удалось построить план: {e}")

    def handle_apply(self, data):
        if not _LONG_OP_LOCK.acquire(blocking=False):
            self.send_error_response(409, "Другая длительная операция уже выполняется")
            return
        pause = None
        if isinstance(data, dict):
            try:
                pause = max(60, min(int(data.get("timeout", 900)), 3600))
            except (TypeError, ValueError):
                pause = 900
        try:
            self.send_json_response(apply_plan(script_timeout=pause or 900))
        except Exception as e:
            logger.error(f"Apply failed: {e}", exc_info=True)
            self.send_error_response(500, f"Ошибка применения профиля: {e}")
        finally:
            _LONG_OP_LOCK.release()

    def handle_update_all(self, data):
        if not _LONG_OP_LOCK.acquire(blocking=False):
            self.send_error_response(409, "Другая длительная операция уже выполняется")
            return
        try:
            self.send_json_response(update_all_packages())
        except Exception as e:
            logger.error(f"update_all failed: {e}", exc_info=True)
            self.send_error_response(500, f"Ошибка обновления: {e}")
        finally:
            _LONG_OP_LOCK.release()

    def handle_service_action(self, data):
        service = data.get("service")
        action = data.get("action")

        if not service or not action:
            self.send_error_response(400, "Missing 'service' or 'action'")
            return

        # Only whitelisted services may be acted upon; a client-supplied
        # install command is deliberately ignored (it was a remote-code-execution hole).
        services = discover_services()
        service_info = services.get(service) or KNOWN_SERVICES.get(service)
        if not service_info:
            self.send_error_response(404, f"Unknown service '{service}'")
            return

        logger.info(f"Service action requested: service='{service}', action='{action}'")

        if action == "install":
            url = service_info.get("install_url")
            package = service_info.get("package")

            if url:
                ok, output = download_and_run_script(url)
                invalidate_caches()
                self.send_json_response({"success": ok, "output": output})
                return

            if package:
                pkgs = package.split()
                try:
                    res = subprocess.run(["/opt/bin/opkg", "install"] + pkgs,
                                         capture_output=True, text=True, timeout=300)
                    invalidate_caches()
                    self.send_json_response({
                        "success": res.returncode == 0,
                        "output": (res.stdout + res.stderr).strip()
                    })
                except subprocess.TimeoutExpired:
                    self.send_error_response(504, f"Установка '{service}' превысила лимит (300s)")
                except Exception as e:
                    self.send_error_response(500, f"Install failed: {e}")
                return

            self.send_error_response(400, f"Для '{service}' нет установщика в каталоге")
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
                    res = subprocess.run(["/opt/bin/opkg", "remove", "--autoremove"] + pkg_to_remove.split(),
                                         capture_output=True, text=True, timeout=120)
                    invalidate_caches()
                    self.send_json_response({"success": res.returncode == 0,
                                             "output": (res.stdout + res.stderr).strip()})
                except Exception as e:
                    self.send_error_response(500, f"Uninstall failed: {e}")
            elif service_info.get("custom"):
                # Custom init scripts are disabled, not deleted: the owner can restore them.
                try:
                    os.makedirs(DISABLED_DIR, exist_ok=True)
                    target = os.path.join(DISABLED_DIR, os.path.basename(script))
                    shutil.move(script, target)
                    invalidate_caches()
                    self.send_json_response({
                        "success": True,
                        "output": f"Скрипт перемещён в {target} (можно вернуть обратно)"
                    })
                except Exception as e:
                    self.send_error_response(500, f"Failed to disable {script}: {e}")
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
            try:
                res = subprocess.run(["/opt/bin/opkg", "upgrade"] + pkg.split(),
                                     capture_output=True, text=True, timeout=180)
                if service_info.get("script"):
                    try:
                        subprocess.run([service_info["script"], "restart"], capture_output=True, timeout=30)
                    except Exception:
                        pass
                invalidate_caches()
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
        command = (data.get("command") or "").strip()
        if not command:
            self.send_error_response(400, "Missing 'command' parameter")
            return
        if len(command) > 512:
            self.send_error_response(400, "Команда слишком длинная (максимум 512 символов)")
            return

        try:
            timeout = max(1, min(int(data.get("timeout", 120)), 300))
        except (ValueError, TypeError):
            timeout = 120

        username = session_username(self.get_auth_token()) or "admin"
        ip = self.client_address[0] if self.client_address else "unknown"
        started = time.time()

        if not _EXEC_LOCK.acquire(blocking=False):
            self.send_error_response(409, "Другая команда уже выполняется, дождитесь её завершения")
            return

        try:
            # Resilient chunked opkg update interception
            cmd_strip = command
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
                    invalidate_caches()
                logger.info(
                    "exec user=%s ip=%s exit=%s duration=%.1fs cmd=%r",
                    username, ip, res.returncode, time.time() - started, cmd_strip
                )
                self.send_json_response({
                    "success": res.returncode == 0,
                    "exit_code": res.returncode,
                    "output": output
                })
            except subprocess.TimeoutExpired:
                logger.warning(
                    "exec user=%s ip=%s TIMEOUT duration=%.1fs cmd=%r",
                    username, ip, time.time() - started, cmd_strip
                )
                self.send_json_response({
                    "success": False,
                    "exit_code": -1,
                    "output": f"Команда прервана по таймауту ({timeout} сек)"
                })
            except Exception as e:
                logger.error(f"Command execution error: {e}")
                self.send_error_response(500, f"Execution failed: {e}")
        finally:
            _EXEC_LOCK.release()

def find_init_script(*prefixes):
    """Locate an init.d script by name prefix (init names differ between versions)."""
    init_dir = "/opt/etc/init.d"
    try:
        for entry in sorted(os.listdir(init_dir)):
            for prefix in prefixes:
                if entry.startswith(prefix):
                    return os.path.join(init_dir, entry)
    except Exception:
        pass
    return None


def resolve_usque_path():
    """Single source of truth for the usque binary path.

    Different builds place it in /opt/bin or /opt/usr/bin; the init script is
    authoritative. Falls back to /opt/bin/usque for a fresh install.
    """
    script = find_init_script("S99usque", "S98usque")
    candidates = []
    if script:
        try:
            with open(script, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            candidates.extend(re.findall(r"(/opt/[A-Za-z0-9_./-]*usque)\b", content))
        except Exception:
            pass
    candidates.extend(["/opt/bin/usque", "/opt/usr/bin/usque"])
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return "/opt/bin/usque"


def backup_files(paths):
    backup = {}
    for path in paths:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    backup[path] = f.read()
        except Exception:
            pass
    return backup


def restore_files(backup):
    for path, data in backup.items():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Failed to restore {path}: {e}")


def perform_service_update(service, version, url):
    output = []
    tmp_dir = "/opt/tmp" if os.path.isdir("/opt/tmp") else tempfile.gettempdir()
    try:
        os.makedirs(tmp_dir, exist_ok=True)
    except Exception:
        pass

    if service == "tg-ws-proxy":
        target_path = os.path.join(tmp_dir, f"tg-ws-proxy_{version}.ipk")
        config_paths = ["/opt/etc/tg-ws-proxy/secret.conf", "/opt/etc/tg-ws-proxy/config.conf"]
        output.append(f"Downloading tg-ws-proxy from {url}...")
        res = subprocess.run(["curl", "-fsSL", "--max-time", "120", "-o", target_path, url],
                             capture_output=True, text=True, timeout=150)
        if res.returncode != 0:
            return False, f"Download failed: {res.stderr}"

        # Preserve the working proxy config across --force-reinstall
        saved = backup_files(config_paths)
        output.append("Installing package (config backup: %d file(s))..." % len(saved))
        res_inst = subprocess.run(["/opt/bin/opkg", "install", "--force-reinstall", target_path],
                                  capture_output=True, text=True, timeout=180)
        output.append(res_inst.stdout + res_inst.stderr)
        try:
            os.remove(target_path)
        except Exception:
            pass

        if res_inst.returncode != 0:
            restore_files(saved)
            return False, "\n".join(output) + "\nUpdate failed, config restored."

        restore_files(saved)
        script = find_init_script("S99tg-ws-proxy", "S61tg-ws-proxy")
        if script:
            subprocess.run([script, "restart"], capture_output=True, timeout=30)
        return True, "\n".join(output)

    elif service == "usque":
        target_path = os.path.join(tmp_dir, f"usque_{version}.zip")
        output.append(f"Downloading usque from {url}...")
        res = subprocess.run(["curl", "-fsSL", "--max-time", "120", "-o", target_path, url],
                             capture_output=True, text=True, timeout=150)
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
                if not dest_path.startswith(os.path.abspath(extract_dir) + os.sep):
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
            shutil.rmtree(extract_dir, ignore_errors=True)
            return False, "Binary not found inside zip archive"

        dest_bin = resolve_usque_path()
        script = find_init_script("S99usque", "S98usque")
        if script:
            subprocess.run([script, "stop"], capture_output=True, timeout=15)

        backup_path = dest_bin + ".bak"
        try:
            if os.path.exists(dest_bin):
                shutil.copy2(dest_bin, backup_path)
            shutil.copy2(bin_path, dest_bin)
            os.chmod(dest_bin, 0o755)
            if not os.access(dest_bin, os.X_OK):
                raise Exception("new binary is not executable")
        except Exception as e:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, dest_bin)
            shutil.rmtree(extract_dir, ignore_errors=True)
            return False, f"Failed to install binary to {dest_bin}: {e} (rolled back)"

        if script:
            subprocess.run([script, "restart"], capture_output=True, timeout=30)
        shutil.rmtree(extract_dir, ignore_errors=True)
        try:
            os.remove(target_path)
        except Exception:
            pass
        output.append(f"Usque updated successfully ({dest_bin}).")
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


# --- Authenticated TCP proxy for ttyd ---
# ttyd itself listens on 127.0.0.1 only. This proxy exposes it on the LAN and
# requires a valid panel session cookie, so the terminal is no longer an open
# root shell on a separate port.

def _read_http_head(sock, limit=16384):
    data = b""
    try:
        sock.settimeout(15)
    except Exception:
        pass
    while b"\r\n\r\n" not in data and len(data) < limit:
        try:
            chunk = sock.recv(4096)
        except Exception:
            break
        if not chunk:
            break
        data += chunk
    return data


def _session_from_http_head(head):
    try:
        text = head.decode("latin-1")
    except Exception:
        return False
    for line in text.split("\r\n")[1:]:
        if line.lower().startswith("cookie:"):
            token = parse_cookie_token(line.split(":", 1)[1].strip())
            return bool(token) and validate_session(token)
    return False


def _relay_sockets(left, right):
    sockets = [left, right]
    try:
        while True:
            # No idle timeout: a terminal may legitimately sit unused for hours
            readable, _, _ = select.select(sockets, [], [])
            if not readable:
                return
            for sock in readable:
                chunk = sock.recv(65536)
                if not chunk:
                    return
                (right if sock is left else left).sendall(chunk)
    except Exception:
        return


def _ttyd_proxy_client(client, addr):
    upstream = None
    try:
        head = _read_http_head(client)
        if not head:
            return
        if not _session_from_http_head(head):
            client.sendall(
                b"HTTP/1.1 401 Unauthorized\r\n"
                b"Content-Type: text/plain; charset=utf-8\r\n"
                b"Connection: close\r\n\r\n"
                b"Login required: open the control panel and sign in first.\n"
            )
            return
        upstream = socket.create_connection(("127.0.0.1", TTYD_INTERNAL_PORT), timeout=15)
        upstream.sendall(head)
        # Relay without socket timeouts; short timeouts would kill idle terminals
        try:
            client.settimeout(None)
            upstream.settimeout(None)
        except Exception:
            pass
        _relay_sockets(client, upstream)
    except Exception as e:
        logger.debug(f"ttyd proxy client error: {e}")
    finally:
        for s in (client, upstream):
            try:
                if s:
                    s.close()
            except Exception:
                pass


def start_ttyd_proxy():
    """Start the loopback->LAN authenticated proxy for ttyd."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((BIND_ADDR, TTYD_PUBLIC_PORT))
        srv.listen(16)
    except Exception as e:
        logger.error(f"Cannot bind ttyd proxy on {BIND_ADDR}:{TTYD_PUBLIC_PORT}: {e}")
        try:
            srv.close()
        except Exception:
            pass
        return None

    def accept_loop():
        while True:
            try:
                client, addr = srv.accept()
            except Exception:
                time.sleep(0.5)
                continue
            threading.Thread(
                target=_ttyd_proxy_client, args=(client, addr), daemon=True
            ).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    logger.info(f"ttyd proxy listening on {BIND_ADDR}:{TTYD_PUBLIC_PORT} -> 127.0.0.1:{TTYD_INTERNAL_PORT}")
    return srv


def run_server():
    init_auth()
    load_sessions()
    start_ttyd_proxy()

    # Graceful shutdown handler
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, shutting down cleanly...")
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
    except Exception:
        pass

    server_address = (BIND_ADDR, PORT)
    httpd = SafeHTTPServer(server_address, RouterAPIHandler)
    logger.info(f"GRouter Control Center API listening on {BIND_ADDR}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
