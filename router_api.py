#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import urllib.request
import zipfile
import shutil
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

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

# Map of service display names to init.d scripts and process names
SERVICES = {
    "dropbear": {"script": "/opt/etc/init.d/S51dropbear", "proc": "dropbear"},
    "nfqws2": {"script": "/opt/etc/init.d/S51nfqws2", "proc": "nfqws"},
    "tg-ws-proxy": {"script": "/opt/etc/init.d/S61tg-ws-proxy", "proc": "tg-ws-proxy"},
    "mosquitto": {"script": "/opt/etc/init.d/S80mosquitto", "proc": "mosquitto"},
    "lighttpd": {"script": "/opt/etc/init.d/S80lighttpd", "proc": "lighttpd"},
    "tuya-mqtt-calibrator": {"script": "/opt/etc/init.d/S99tuya-mqtt-calibrator", "proc": "tuya_mqtt_calibrator.py"},
    "usque": {"script": "/opt/etc/init.d/S99usque", "proc": "usque"}
}

def get_process_status(proc_name):
    """Checks if a process is running by searching the active processes."""
    try:
        # Check running processes using ps
        ps_output = subprocess.check_output(["ps", "-w"]).decode("utf-8", errors="ignore")
        for line in ps_output.splitlines():
            if proc_name in line and "router_api.py" not in line and "ps" not in line:
                return "running"
        return "stopped"
    except Exception as e:
        logging.error(f"Error checking process {proc_name}: {e}")
        return "unknown"

def get_service_status(service_name):
    """Retrieves current status of a service using its init script and process status."""
    info = SERVICES.get(service_name)
    if not info:
        return "unknown"
    
    script_path = info["script"]
    proc_name = info["proc"]
    
    # First, try to run init script status command if it exists
    if os.path.exists(script_path):
        try:
            res = subprocess.run([script_path, "status"], capture_output=True, text=True, timeout=5)
            output = (res.stdout + res.stderr).lower()
            if "running" in output or "alive" in output or "started" in output:
                return "running"
            elif "stopped" in output or "not running" in output:
                return "stopped"
        except Exception:
            pass
            
    # Fallback to checking active processes
    return get_process_status(proc_name)

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
    return None

def get_installed_versions():
    """Retrieves installed versions of major packages."""
    versions = {}
    
    # 1. tg-ws-proxy
    tg_ver = get_opkg_package_version("tg-ws-proxy")
    if not tg_ver:
        # Check if the binary is executable and check --version
        try:
            out = subprocess.check_output(["/opt/bin/tg-ws-proxy", "--version"], stderr=subprocess.STDOUT, text=True)
            tg_ver = out.strip()
        except Exception:
            tg_ver = "unknown"
    versions["tg-ws-proxy"] = tg_ver

    # 2. usque (custom binary version command)
    try:
        if os.path.exists("/opt/usr/bin/usque"):
            out = subprocess.check_output(["/opt/usr/bin/usque", "version"], stderr=subprocess.STDOUT, text=True)
            # Example output: usque version: v3.0.0
            for line in out.splitlines():
                if "version:" in line:
                    versions["usque"] = line.split("version:")[1].strip()
                    break
            if "usque" not in versions:
                versions["usque"] = out.strip().split("\n")[0]
        else:
            versions["usque"] = "not installed"
    except Exception as e:
        logging.error(f"Error checking usque version: {e}")
        versions["usque"] = "unknown"

    # 3. mosquitto (registers as mosquitto-ssl in Entware/Keenetic)
    mosq_ver = get_opkg_package_version("mosquitto-ssl")
    if not mosq_ver:
        mosq_ver = get_opkg_package_version("mosquitto")
    versions["mosquitto"] = mosq_ver or "unknown"

    # 4. lighttpd
    versions["lighttpd"] = get_opkg_package_version("lighttpd") or "unknown"

    # 5. dropbear
    versions["dropbear"] = get_opkg_package_version("dropbear") or "unknown"

    # 6. nfqws2 (registers as nfqws2-keenetic or nfqws-keenetic-web in Entware)
    nfqws_ver = get_opkg_package_version("nfqws2-keenetic")
    if not nfqws_ver:
        nfqws_ver = get_opkg_package_version("nfqws-keenetic-web")
    if not nfqws_ver:
        nfqws_ver = get_opkg_package_version("nfqws2")
    versions["nfqws2"] = nfqws_ver or "unknown"

    # 7. tuya-mqtt-calibrator
    if os.path.exists("/opt/scripts/tuya_mqtt_calibrator.py") or os.path.exists("/opt/usr/bin/tuya_mqtt_calibrator.py"):
        versions["tuya-mqtt-calibrator"] = "installed"
    else:
        versions["tuya-mqtt-calibrator"] = "not installed"

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

    def handle_status(self):
        logging.info("Status endpoint requested")
        
        # Build list of services with current statuses
        service_statuses = {}
        for srv in SERVICES.keys():
            service_statuses[srv] = get_service_status(srv)
            
        # Build OPKG repository versions list
        opkg_versions = {}
        opkg_versions["tg-ws-proxy"] = get_opkg_repo_version("tg-ws-proxy")
        opkg_versions["mosquitto"] = get_opkg_repo_version("mosquitto-ssl") or get_opkg_repo_version("mosquitto")
        opkg_versions["lighttpd"] = get_opkg_repo_version("lighttpd")
        opkg_versions["dropbear"] = get_opkg_repo_version("dropbear")
        
        nfqws_ver = get_opkg_repo_version("nfqws2-keenetic")
        if not nfqws_ver:
            nfqws_ver = get_opkg_repo_version("nfqws-keenetic-web")
        if not nfqws_ver:
            nfqws_ver = get_opkg_repo_version("nfqws2")
        opkg_versions["nfqws2"] = nfqws_ver
            
        response = {
            "system": get_system_stats(),
            "versions": get_installed_versions(),
            "opkg_versions": opkg_versions,
            "services": service_statuses
        }
        self.send_json_response(response)

    def handle_service_action(self, data):
        service = data.get("service")
        action = data.get("action")
        
        if not service or not action:
            self.send_error_response(400, "Missing 'service' or 'action' parameter")
            return
            
        if service not in SERVICES:
            self.send_error_response(404, f"Service '{service}' is not managed")
            return
            
        if action not in ["start", "stop", "restart", "status"]:
            self.send_error_response(400, f"Unsupported action '{action}'")
            return
            
        script_path = SERVICES[service]["script"]
        logging.info(f"Service action requested: {service} -> {action}")
        
        if not os.path.exists(script_path):
            self.send_error_response(500, f"Init script for {service} not found at {script_path}")
            return
            
        try:
            res = subprocess.run([script_path, action], capture_output=True, text=True, timeout=15)
            output = res.stdout + res.stderr
            success = res.returncode == 0
            
            # Recheck status
            new_status = get_service_status(service)
            
            self.send_json_response({
                "success": success,
                "exit_code": res.returncode,
                "output": output.strip(),
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
            
        logging.info(f"Executing manual command on router: {command}")
        try:
            # Run command inside shell with 30s timeout
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = res.stdout + res.stderr
            self.send_json_response({
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "output": output.strip()
            })
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

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, RouterAPIHandler)
    logging.info(f"Router API running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutting down.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
