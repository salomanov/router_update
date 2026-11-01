#!/bin/sh

# ==========================================================
# GRouter Full Auto-Setup (Полная установка всех компонентов)
# Wrapper around install.sh --all
# ==========================================================

REPO_RAW="https://raw.githubusercontent.com/salomanov/router_update/main"
CACHE_BUST="?nocache=$(date +%s)$$"
TMP_FILE="/opt/tmp/grouter-install.sh"
mkdir -p /opt/tmp

if curl -fsSL --max-time 30 -o "$TMP_FILE" "${REPO_RAW}/install.sh${CACHE_BUST}"; then
    chmod +x "$TMP_FILE"
    sh "$TMP_FILE" --all "$@"
    rc=$?
    rm -f "$TMP_FILE"
    exit $rc
else
    printf "Ошибка скачивания install.sh\n"
    exit 1
fi
