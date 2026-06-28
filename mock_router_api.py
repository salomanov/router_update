#!/usr/bin/env python3
import json
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8089

# Mock state
mock_data = {
    "system": {
        "cpu_load": "0.10 0.15 0.12",
        "mem_total": 268435456,  # 256 MB
        "mem_free": 134217728,   # 128 MB
        "mem_used_pct": 50.0,
        "disk_total": "14.2G",
        "disk_used": "0.8G",
        "disk_free": "13.4G",
        "disk_used_pct": 5.6
    },
    "versions": {
        "tg-ws-proxy": "0.5-1",
        "usque": "v2.0.1"
    },
    "services": {
        "dropbear": "running",
        "nfqws2": "running",
        "tg-ws-proxy": "running",
        "mosquitto": "running",
        "lighttpd": "running",
        "tuya-mqtt-calibrator": "running",
        "usque": "stopped"
    }
}

class MockRouterAPIHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self.handle_status()
        else:
            self.send_error_response(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON payload")
            return

        if self.path == "/api/service":
            self.handle_service(data)
        elif self.path == "/api/update":
            self.handle_update(data)
        else:
            self.send_error_response(404, "Not Found")

    def send_json_response(self, data, status_code=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_error_response(self, status_code, message):
        self.send_json_response({"error": message}, status_code)

    def handle_status(self):
        # Slightly fluctuate stats to make it look alive
        mock_data["system"]["cpu_load"] = f"{round(random.uniform(0.05, 0.45), 2)} {round(random.uniform(0.08, 0.35), 2)} {round(random.uniform(0.1, 0.25), 2)}"
        used_mem = random.randint(100, 180) * 1024 * 1024
        mock_data["system"]["mem_free"] = mock_data["system"]["mem_total"] - used_mem
        mock_data["system"]["mem_used_pct"] = round((used_mem / mock_data["system"]["mem_total"]) * 100, 1)
        
        self.send_json_response(mock_data)

    def handle_service(self, data):
        service = data.get("service")
        action = data.get("action")
        
        if not service or not action:
            self.send_error_response(400, "Missing parameters")
            return
            
        if service not in mock_data["services"]:
            self.send_error_response(404, "Service not found")
            return

        print(f"[MOCK] Action: {action} on {service}")
        
        if action == "start":
            mock_data["services"][service] = "running"
            output = f"Starting mock service {service}... done."
        elif action == "stop":
            mock_data["services"][service] = "stopped"
            output = f"Stopping mock service {service}... done."
        elif action == "restart":
            mock_data["services"][service] = "running"
            output = f"Restarting mock service {service}...\nStopping... done.\nStarting... done."
        else:
            output = f"Status check: {mock_data['services'][service]}"

        self.send_json_response({
            "success": True,
            "exit_code": 0,
            "output": output,
            "new_status": mock_data["services"][service]
        })

    def handle_update(self, data):
        service = data.get("service")
        version = data.get("version")
        url = data.get("url")
        
        if not service or not version or not url:
            self.send_error_response(400, "Missing parameters")
            return

        print(f"[MOCK] Update {service} to {version} from {url}")
        
        output = [
            f"Downloading {service} package from {url}...",
            "Download complete (100%)",
            f"Installing version {version}...",
            "Post-install script running...",
            "Restoring backup configs...",
            "Restarting service...",
            f"Service {service} successfully updated!"
        ]
        
        # Update mock versions
        mock_data["versions"][service] = version
        mock_data["services"][service] = "running"
        
        self.send_json_response({
            "success": True,
            "output": "\n".join(output),
            "new_versions": mock_data["versions"]
        })

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MockRouterAPIHandler)
    print(f"Mock Router API server running on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
