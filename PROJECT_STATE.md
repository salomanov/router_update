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
- **Router Web API:** Python Bottle service running on port 8089 (`http://192.168.1.1:8089/api/exec`)
- **Remote Gateway:** SSH on port 222 (`root:keenetic`)

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
   - **Root Cause of Video Stalling:**
     - `webcamshow.cc` and `webmodel.cam` embed iframes pointing to `mxdrop.sx`, which redirect (`302`) to `mxdrop.top`. Without `mxdrop.top` in `user.list`, Cloudflare/ISP DPI dropped packets mid-stream after ~25KB, stalling the player initialization before video URLs were requested.
     - Video deliveries for MixDrop are served directly from `*.mxcontent.net` (`ebij8ni1d.mxcontent.net`, `30xplewoo.mxcontent.net`, `usx2f826m.mxcontent.net`).
     - `livecamrips.to` utilizes 4 distinct embedded streaming providers:
       1. MixDrop alias (`mdzsmutpcvykb.net` -> `mxdrop.top` -> `*.mxcontent.net`)
       2. Uqload (`uqload.vc`, `*.uqload.vc` / `strm*.uqload.vc` HLS)
       3. Vidara (`vidara.to` -> `97bf1.com` / `s*.97bf1.com` HLS + `s1q2105.com` thumbnails)
       4. StreamCash (`streamcash.to` -> `cdn.streamcash.to` HLS `.ts` segments)
   - **Remediation:**
     - Added all 4 streaming networks, player domains, and video CDNs to `user.list` (407 domains total).
     - Verified fast chunk / HLS download across all 4 providers.

## Key Configuration Files
- `/opt/etc/nfqws2/nfqws2.conf`: Anti-DPI engine configuration.
- `/opt/etc/nfqws2/lists/user.list`: Domain list for targeted desync (407 domains).
- `/opt/etc/nfqws2/lists/exclude.list`: Domains excluded from desync (e.g. Bambu Lab S3).
- `/opt/etc/ndm/netfilter.d/020-block-quic.sh`: QUIC UDP 443 reject script.
- `/opt/etc/ndm/netfilter.d/010-tailscale.sh`: Tailscale iptables rules.

## Next Steps
- Verify user playback across all three sites in web browsers.
- Maintain sync between local Git repository and router.
