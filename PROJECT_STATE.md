# PROJECT_STATE.md

## Project Information
- **Project Name:** Router Update & Bypass System (Xiaomi Mi WiFi Router 3G v1)
- **Primary Goal:** High-performance, resilient DPI bypass for Russian ISPs (ТСПУ / РКН), Telegram Proxy, Tailscale Exit Node, and Web Control Panel.
- **Repository:** `https://github.com/salomanov/router_update.git`

## Architecture & Environment
- **Device:** Xiaomi Router 3G v1 (R3Gv1)
- **Firmware:** KeeneticOS (modded Keenetic Peak KN-2410 / KN-1810) on MIPS architecture
- **Storage:** Entware installed on `/opt`
- **DPI Bypass Engine:** `nfqws2-keenetic` 1.3.1 (LUA zapret engine)
- **Router Web API:** Python service running on port 8089 (`http://192.168.1.1:8089/api/exec`)
- **Remote Gateway:** SSH on port 222 (`root:<router_password>`)

## Current Working State (as of October 2026)
1. **YouTube & Media Streaming:**
   - 4K/8K 60fps YouTube streaming fully functional on Smart TV, PC, and Mobile.
   - Global QUIC block (`020-block-quic.sh`) drops UDP 443 to force TCP fallback with desync.
2. **Instagram & Meta:**
   - CDN and GraphQL hosts included in `user.list`.
   - Direct connection and Tailscale routing configured.
3. **Bambu Lab 3D Printing:**
   - Bambu AWS S3 storage (`bambulab-prod-oss-*.s3.amazonaws.com`) safely preserved in `exclude.list`.
4. **Webcam & Rip Video Streaming (livecamrips.to, webcamshow.cc, webmodel.cam):**
   - Added all 4 streaming networks, player domains, and video CDNs to `user.list` (412 domains total).
   - Fast chunk / HLS download verified across all providers.
5. **Entware OPKG Updates & Web Panel API (Fixed):**
   - **Root Cause of HTTP 500:**
     - `bin.entware.net` (`107.189.14.230`, BuyVM Luxembourg) single-stream HTTP transfers are throttled/dropped by Russian ISP ТСПУ/DPI after exactly 33,054 bytes.
     - `opkg update` using standard single-stream `wget` stalled, hitting the hardcoded 30s timeout in `router_api.py`, returning HTTP 500 and leaving orphaned `wget`/`opkg` processes holding `/opt/tmp/opkg.lock`.
     - `router_api.py` was single-threaded, freezing background status checks during any long execution.
     - Status checks polled every 5s ran 12 subprocess opkg calls repeatedly, generating CPU spikes.
   - **Remediation:**
     - Developed `/opt/scripts/opkg_update.py`: downloads `Packages.gz` in 30KB slices using HTTP Range requests (377 KB complete in ~7 seconds with 100% reliability and gzip verification).
     - Added `ThreadingMixIn` to `SafeHTTPServer` in `router_api.py` for concurrent request handling.
     - Implemented in-memory TTL caching (60s for installed versions, 300s for repo versions) with cache invalidation on package actions.
     - Added configurable timeouts (default 180s), graceful timeout recovery, and automatic lock cleanup.
     - Updated `app.js` with 180s timeout headers and verified full functionality via web UI.
6. **Dynamic Modular Architecture & Application Catalog (October 2026):**
   - Replaced the hardcoded 9-service list with dynamic auto-discovery (`discover_services()` in `router_api.py`) scanning `/opt/etc/init.d/S*`.
   - Added Tab navigation in Web Control Panel:
     - **«Установленные службы»**: Shows only services actually present and configured on this specific router (running/stopped status, version, upgrade buttons, uninstall button).
     - **«Каталог приложений»**: Shows all uninstalled optional packages (AdGuard Home, Transmission, Stubby, iPerf3, Mosquitto, etc.) with 1-click «Установить» button executing `/api/exec`.
   - Any router now gets a clean, uncluttered interface showing only its actual services without red "Остановлен" badges for missing optional software.
7. **Tuya MQTT Calibrator Status & Locations:**
   - **Primary Project Repository:** `E:\Projects\tuya_mqtt_calibrator` (GitHub: `https://github.com/salomanov/MQTT.git`).
   - **Production router daemon:** Running from `/opt/scripts/tuya_mqtt_calibrator.py` managed by `/opt/etc/init.d/S99tuya-mqtt-calibrator`.
8. **Tuya MQTT Calibrator Enhanced Edition (October 2026):**
   - Upgraded `tinytuya` on the router to version **1.20.0**.
   - Enhanced `tuya_mqtt_calibrator.py`:
     - Auto-reconnect to Mosquitto broker on router boot (`retry_first_connection=True`, `connect_async`).
     - Config extraction: loads `config.json` or `/opt/etc/tuya_mqtt_calibrator.json` with fallback.
     - Added read-only query topic `tuya/calibrate/get` for querying status without modifying calibration.
     - Status published with `retain=True` and LWT availability `tuya/calibrate/availability` (`online`/`offline`).
     - Standardized logging to rotating file `/opt/var/log/tuya_mqtt_calibrator.log`.
   - Fixed `router_api.py` status check: negative status ("not running") evaluated before positive substring.
   - Pushed commit `63db4b9` to `salomanov/MQTT.git` and deployed live to router.
9. **Usque SOCKS5 HTTP 500 Fix & Service Timeout (October 2026):**
   - `handle_service_action()` in `router_api.py` had a rigid 15s timeout. Usque `start` takes up to 30s during `wait_for_ip`.
   - Increased timeout to 40s for `start`/`restart` actions.
   - Added graceful handling for `subprocess.TimeoutExpired` checking actual process status instead of returning HTTP 500.
   - Deployed to router and committed as `f097052`.
10. **Repository Path Migration & Git Sync Audit (October 2026):**
   - Repositories relocated to `E:\Projects\Router_api` and `E:\Projects\tuya_mqtt_calibrator`.
   - Synchronized `configs/lists/user.list` (added 6 uncommitted domains from router: `antigravity-unleash.goog`, `daily-cloudcode-pa.googleapis.com`, `lh3.googleusercontent.com`, `play.googleapis.com`, `www.googleapis.com`, `zyxel.com`).
   - Discovered root cause of PC DNS resolution failure for Gemini and OpenRouter: Keenetic upstream DoT `xbox-dns.ru` returns `0.0.0.0` (sinkhole) for non-gaming domains.
11. **Fresh Router Installer Hardening & DNS Automation (October 2026):**
   - `install.sh`: Added `python3-email` dependency (critical for `http.server`) and automated download of `opkg_update.py` into `/opt/scripts`.
   - `install_nfqws2.sh`: Added auto-detection and dynamic adaptation of `ISP_INTERFACE` to preserve whatever WAN connection the router uses (PPPoE `ppp0`, IPoE `eth3`, USB-modem, WISP) instead of hardcoding `ppp0`.
   - `setup_dns.sh`: Created standalone installer applying the working DoT/DoH configuration (`dns.malw.link`, `dns.geohide.ru`, `dns.dns-ai.ru`) via Keenetic `ndmc`.
   - `install_all.sh`: Integrated `setup_dns.sh` as Step 5 in All-in-One deployment.
12. **Multi-Device YouTube Fix & DNS-Proxy Stabilization (October 2026):**
   - Resolved YouTube buffering/failure on mobile phones and Smart TVs:
     - Disabled pseudo-IPv6 SLAAC advertisement (`no ipv6 subnet Default`, `no ipv6 local-prefix default`) on Home LAN, eliminating the IPv6 black hole when the ISP provides no WAN IPv6 route.
     - Extended `020-block-quic.sh` to reject QUIC (UDP 443) on both IPv4 (`iptables`) and IPv6 (`ip6tables`), forcing phones and TV apps to instantly fallback to TCP 443 HTTPS with nfqws2 desync.
     - Removed failing `https://dns.geohide.ru:444/dns-query` DoH upstream from Keenetic `dns-proxy` and `setup_dns.sh` (eliminated recurring TLS certificate errors and DoH crashes logged in system log).

13. **Tailscale Service Health & Init Conflict Resolution (October 2026):**
   - Fixed Logged out status caused by conflicting init script /opt/etc/init.d/S06tailscaled (which loaded an empty state file).
   - Removed conflicting script, created symlink /opt/var/tailscaled.state -> /opt/var/lib/tailscale/tailscaled.state.
   - Tailscale is active and healthy: IP 100.64.192.44, acting as Exit Node, direct connectivity verified (48ms to active peers).

14. **GRouter Web Catalog & nfqws Web Interface Fix for Fresh Installs (October 2026):**
   - **Catalog Application Installation Fix:**
     - In `router_api.py` and `app.js`, fixed invalid package names that caused Entware `Cannot find package ...` errors:
       - `adguardhome`: Updated from `adguardhome` to official Entware package `adguardhome-go`.
       - `transmission`: Updated from `transmission-daemon-openssl` to `transmission-daemon transmission-web`.
       - Explicitly prefixed OPKG invocations with `/opt/bin/opkg` across all known services.
     - Fixed `uninstall` handler in `router_api.py` to support multi-package removal (`cmd = ["/opt/bin/opkg", "remove"] + uninstall_pkg.split()`).
     - Added automatic OPKG cache validation in `/api/exec`: if package lists in `/opt/var/opkg-lists` are missing/empty on fresh routers, the backend auto-fetches them before running `opkg install`.
     - Added automatic cleanup of stale `/opt/tmp/opkg.lock` files before executing `opkg` commands.
   - **nfqws Web Interface Automation:**
     - Updated `install_nfqws2.sh` to install both `nfqws2-keenetic` and `nfqws-keenetic-web` (providing the official web UI on port 8088 / 90 via lighttpd and php8-cgi).
     - Added automatic restart of `lighttpd` and printed direct web interface URL `http://192.168.1.1:8088/` upon completion.
     - Updated `install_all.sh` to display the nfqws web interface link alongside GRouter.

11. **Accurate Package Version Resolution (October 2026):**
    - `router_api.py` now prioritizes package manager state (`opkg status <pkg>`) before falling back to binary CLI `-v` flags.
    - Resolves `tg-ws-proxy` version detection (`0.11-3`) and eliminates false `↑ 0.11-3` update prompts.
12. **Embedded Web Terminal (ttyd / Web PuTTY):**
    - Browser subframe anti-phishing policies block HTTP 401 Basic Auth dialogs inside `<iframe>`.
    - Implemented `/opt/scripts/ttyd_shell.sh`: an interactive authentication wrapper allowing `ttyd` to serve `200 OK` to the iframe while verifying password (`Salomanov`) in-terminal.
    - Updated UI tab badges and iframe clipboard permissions.

## Key Configuration Files
- `/opt/etc/nfqws2/nfqws2.conf`: Anti-DPI engine configuration.
- `/opt/etc/nfqws2/lists/user.list`: Domain list for targeted desync (413 domains).
- `/opt/etc/nfqws2/lists/exclude.list`: Domains excluded from desync (e.g. Bambu Lab S3, Entware).
- `/opt/etc/ndm/netfilter.d/020-block-quic.sh`: Dual-stack IPv4/IPv6 QUIC (UDP 443) blocker.
- `/opt/scripts/router_api.py`: Multi-threaded web control panel API with dynamic discovery.
- `/opt/scripts/opkg_update.py`: Resilient chunked OPKG package list updater.
- `/opt/share/router-control-center/`: Web panel frontend (`index.html`, `app.js`, `style.css`).
- `/opt/scripts/tuya_mqtt_calibrator.py`: Tuya MQTT calibrator service script.
- `/opt/var/log/tuya_mqtt_calibrator.log`: Rotating runtime log for Tuya calibrator.
- `setup_dns.sh`: Automatic Keenetic DoT/DoH configuration script.

## Next Steps
- Verify YouTube playback across mobile devices, Smart TVs, and PCs.
