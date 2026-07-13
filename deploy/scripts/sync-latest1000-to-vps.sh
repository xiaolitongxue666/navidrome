#!/usr/bin/env bash
# Wrapper: sync latest1000 MP3s to VPS via Python (Windows-safe paths).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SCRIPT_DIR}/sync-latest1000-to-vps.py" "$@"
