#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
OLLAMA_BIN="${OLLAMA_BIN:-$HOME/.local/bin/ollama}"

if ! sudo -n systemctl start ollama; then
  echo "No se pudo iniciar ollama. Revisá la regla de sudoers." >&2
  exit 1
fi

ready=0
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "Ollama no respondió en 60 s." >&2
  exit 1
fi

echo "Ollama listo. Jarvis responde por texto con el modelo local."
"$SCRIPT_DIR/status-jarvis.sh"
