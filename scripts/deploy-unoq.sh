#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HOST="${UNOQ_HOST:-192.168.1.75}"
USER_NAME="${UNOQ_USER:-arduino}"
PORT="${UNOQ_PORT:-22}"
KEY="${UNOQ_KEY:-$HOME/.ssh/unoq_key}"
TARGET="/home/$USER_NAME/JarvisUNOQ"

ssh -p "$PORT" -i "$KEY" -o BatchMode=yes "$USER_NAME@$HOST" "mkdir -p '$TARGET'"

tar \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='.env' \
  -czf - -C "$PROJECT_DIR" . |
  ssh -p "$PORT" -i "$KEY" -o BatchMode=yes "$USER_NAME@$HOST" \
    "tar -xzf - -C '$TARGET'"

ssh -p "$PORT" -i "$KEY" -o BatchMode=yes "$USER_NAME@$HOST" "
  chmod +x '$TARGET'/scripts/*.sh '$TARGET'/scripts/*.py
  ln -sfn '$TARGET'/scripts/start-jarvis.sh \"\$HOME/start-jarvis.sh\"
  ln -sfn '$TARGET'/scripts/stop-jarvis.sh \"\$HOME/stop-jarvis.sh\"
  ln -sfn '$TARGET'/scripts/status-jarvis.sh \"\$HOME/status-jarvis.sh\"
  ln -sfn '$TARGET'/scripts/jarvis-chat.py \"\$HOME/jarvis-chat\"
"

echo "Proyecto copiado a $USER_NAME@$HOST:$TARGET"
echo "Probar: ssh -p $PORT -i $KEY $USER_NAME@$HOST '$TARGET/scripts/status-jarvis.sh'"
