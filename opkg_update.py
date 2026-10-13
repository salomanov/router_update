#!/usr/bin/env python3
"""
Robust Entware Package List Updater
Bypasses ISP/DPI packet drops on large single-stream HTTP transfers by using chunked Range requests.
"""

import sys
import os
import urllib.request
import gzip
import shutil
import subprocess

SOURCES = [
    {
        "name": "entware",
        "url": "http://bin.entware.net/mipselsf-k3.4/Packages.gz",
        "target": "/opt/var/opkg-lists/entware"
    },
    {
        "name": "keendev",
        "url": "http://bin.entware.net/mipselsf-k3.4/keenetic/Packages.gz",
        "target": "/opt/var/opkg-lists/keendev"
    }
]

CHUNK_SIZE = 30000  # 30KB chunks to stay safely under ISP DPI drop threshold (~33KB)

def clean_stale_locks():
    """Kills lingering wget/opkg and removes lock files."""
    try:
        subprocess.run(["killall", "-9", "wget", "opkg"], capture_output=True)
    except Exception:
        pass
    lock_file = "/opt/tmp/opkg.lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except Exception:
            pass

def get_content_length(url):
    """Retrieves file size using HEAD request."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Wget/1.21"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            cl = resp.headers.get("Content-Length")
            if cl:
                return int(cl)
    except Exception:
        pass
    return None

def download_chunked(url, target_path):
    """Downloads a file using sequential Range chunks."""
    total_size = get_content_length(url)
    tmp_path = target_path + ".tmp"
    
    # If size is small or unknown, try simple download first
    if total_size and total_size <= CHUNK_SIZE:
        req = urllib.request.Request(url, headers={"User-Agent": "Wget/1.21"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(tmp_path, "wb") as f:
            f.write(data)
    else:
        # Fallback total size if HEAD fails: 450KB
        max_size = total_size or 500000
        with open(tmp_path, "wb") as f:
            current = 0
            while current < max_size:
                end = min(current + CHUNK_SIZE - 1, max_size - 1) if total_size else current + CHUNK_SIZE - 1
                req = urllib.request.Request(
                    url,
                    headers={
                        "Range": f"bytes={current}-{end}",
                        "User-Agent": "Wget/1.21"
                    }
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        chunk = resp.read()
                        if not chunk:
                            break
                        f.write(chunk)
                        current += len(chunk)
                        # If partial response indicates EOF
                        if total_size and current >= total_size:
                            break
                except urllib.error.HTTPError as e:
                    if e.code == 416:  # Range Not Satisfiable (reached EOF)
                        break
                    raise

    # Verify gzip integrity
    try:
        with gzip.open(tmp_path, "rb") as gz:
            gz.read(1024)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise ValueError(f"Gzip verification failed: {e}")

    # Atomic move
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.move(tmp_path, target_path)
    return os.path.getsize(target_path)

def main():
    clean_stale_locks()
    success_count = 0
    
    for src in SOURCES:
        name = src["name"]
        url = src["url"]
        target = src["target"]
        print(f"Downloading {url}...")
        try:
            size = download_chunked(url, target)
            print(f"Updated list of available packages in {target} ({size} bytes).")
            success_count += 1
        except Exception as e:
            print(f"Failed to download {url}: {e}", file=sys.stderr)
            
    if success_count == len(SOURCES):
        print("Package lists successfully updated!")
        return 0
    elif success_count > 0:
        print("Partially updated package lists.")
        return 0
    else:
        print("Error: Could not update package lists.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
