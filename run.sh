#!/usr/bin/env bash
# Lanzador de DINO RUSH.
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c "import pygame" >/dev/null 2>&1; then
    cat <<'EOF'
Falta pygame-ce. Instálalo con:

    python3 -m pip install -r requirements.txt

En Ubuntu/Debian, si pip no está disponible:

    sudo apt install python3-pip

EOF
    exit 1
fi

exec python3 main.py
