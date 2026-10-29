#!/usr/bin/env python3
"""
Robust Entware package list updater.

Some ISPs/DPI setups drop large single-stream HTTP transfers. This script
downloads Packages.gz in small Range chunks, verifies the gzip archive and
atomically replaces the list. All configured repositories are updated, not a
hardcoded pair, so extra feeds (feedly, nfqws*, etc.) stay consistent.
"""

import gzip
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

CHUNK_SIZE = 30000  # 30KB chunks to stay under the DPI drop threshold (~33KB)
CHUNK_RETRIES = 3
RETRY_PAUSE = 1.5
USER_AGENT = "Wget/1.21"
FALLBACK_MAX_SIZE = 2 * 1024 * 1024

CONF_DIR = "/opt/etc/opkg"
CONF_FILE = "/opt/etc/opkg.conf"
LIST_DIR = "/opt/var/opkg-lists"

DEFAULT_SOURCES = [
    {
        "name": "entware",
        "url": "http://bin.entware.net/mipselsf-k3.4/Packages.gz",
        "target": os.path.join(LIST_DIR, "entware"),
    },
    {
        "name": "keendev",
        "url": "http://bin.entware.net/mipselsf-k3.4/keenetic/Packages.gz",
        "target": os.path.join(LIST_DIR, "keendev"),
    },
]


class RangeNotSupported(Exception):
    """Server returned 200 for a Range request (it ignored the header)."""


def clean_stale_locks():
    """Remove a stale opkg lock, but never kill somebody else's opkg process."""
    lock_file = "/opt/tmp/opkg.lock"
    if not os.path.exists(lock_file):
        return
    try:
        res = subprocess.run(["pgrep", "opkg"], capture_output=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            print("opkg is already running; leaving the lock file alone.", file=sys.stderr)
            return
    except Exception:
        pass
    try:
        os.remove(lock_file)
        print("Removed stale lock %s" % lock_file)
    except Exception:
        pass


def parse_sources():
    """Read every `src/gz NAME URL` line from the opkg configuration."""
    confs = []
    if os.path.isfile(CONF_FILE):
        confs.append(CONF_FILE)
    try:
        confs.extend(
            sorted(os.path.join(CONF_DIR, f) for f in os.listdir(CONF_DIR) if f.endswith(".conf"))
        )
    except Exception:
        pass

    sources = []
    seen = set()
    for path in confs:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = re.match(r"^\s*src/\S+\s+(\S+)\s+(\S+)", line)
                    if not match:
                        continue
                    name, url = match.group(1), match.group(2)
                    if name in seen:
                        continue
                    seen.add(name)
                    if not url.endswith("Packages.gz"):
                        url = url.rstrip("/") + "/Packages.gz"
                    sources.append({
                        "name": name,
                        "url": url,
                        "target": os.path.join(LIST_DIR, name),
                    })
        except Exception as e:
            print("Cannot read %s: %s" % (path, e), file=sys.stderr)

    return sources or list(DEFAULT_SOURCES)


def get_content_length(url):
    """Retrieve file size via HEAD (None if unavailable)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            length = resp.headers.get("Content-Length")
            if length:
                return int(length)
    except Exception:
        pass
    return None


def _open(url, headers=None, timeout=20):
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=request_headers), timeout=timeout)


def _simple_download(url, tmp_path):
    """Plain download with retries (used for small files or Range-less servers)."""
    last_error = None
    for attempt in range(1, CHUNK_RETRIES + 1):
        try:
            with _open(url) as resp:
                data = resp.read()
            if not data:
                raise ValueError("empty response body")
            with open(tmp_path, "wb") as f:
                f.write(data)
            return
        except Exception as e:
            last_error = e
            if attempt < CHUNK_RETRIES:
                time.sleep(RETRY_PAUSE * attempt)
    raise last_error


def _ranged_download(url, tmp_path, total_size):
    """Sequential Range chunks, with a retry per chunk."""
    max_size = total_size or FALLBACK_MAX_SIZE
    current = 0

    with open(tmp_path, "wb") as f:
        while current < max_size:
            end = current + CHUNK_SIZE - 1
            if total_size:
                end = min(end, total_size - 1)

            chunk = None
            last_error = None
            for attempt in range(1, CHUNK_RETRIES + 1):
                try:
                    with _open(url, {"Range": "bytes=%d-%d" % (current, end)}) as resp:
                        status = getattr(resp, "status", None) or resp.getcode()
                        body = resp.read()
                    if status != 206:
                        # Server ignored Range: appending would duplicate data.
                        raise RangeNotSupported("server returned %s instead of 206" % status)
                    chunk = body
                    break
                except RangeNotSupported:
                    raise
                except urllib.error.HTTPError as e:
                    if e.code == 416:  # requested range past EOF
                        return
                    last_error = e
                except Exception as e:
                    last_error = e
                if attempt < CHUNK_RETRIES:
                    time.sleep(RETRY_PAUSE * attempt)

            if chunk is None:
                raise last_error or IOError("chunk download failed")
            if not chunk:
                break

            f.write(chunk)
            current += len(chunk)
            if total_size and current >= total_size:
                break


def download_chunked(url, target_path):
    """Download one Packages.gz and atomically replace the opkg list."""
    total_size = get_content_length(url)
    tmp_path = target_path + ".tmp"

    try:
        if total_size and total_size <= CHUNK_SIZE:
            _simple_download(url, tmp_path)
        else:
            try:
                _ranged_download(url, tmp_path, total_size)
            except RangeNotSupported as e:
                print("Range not supported (%s); falling back to a full download." % e)
                _simple_download(url, tmp_path)

        try:
            with gzip.open(tmp_path, "rb") as gz:
                gz.read(1024)
        except Exception as e:
            raise ValueError("gzip verification failed: %s" % e)

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.move(tmp_path, target_path)
        return os.path.getsize(target_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def main():
    clean_stale_locks()
    sources = parse_sources()
    failures = 0

    for src in sources:
        print("Downloading %s..." % src["url"])
        try:
            size = download_chunked(src["url"], src["target"])
            print("Updated list of available packages in %s (%d bytes)." % (src["target"], size))
        except Exception as e:
            failures += 1
            print("Failed to download %s: %s" % (src["url"], e), file=sys.stderr)

    if failures:
        print("Error: %d of %d package lists could not be updated."
              % (failures, len(sources)), file=sys.stderr)
        return 1

    print("Package lists successfully updated (%d sources)." % len(sources))
    return 0


if __name__ == "__main__":
    sys.exit(main())
