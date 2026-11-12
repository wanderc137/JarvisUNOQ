#!/usr/bin/env bash
set -uo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
OLLAMA_BIN="${OLLAMA_BIN:-$HOME/.local/bin/ollama}"

echo "JarvisUNOQ · $(date -Is)"
echo
echo "Servicio:"
printf '  %-9s %s\n' ollama "$(systemctl is-active ollama 2>/dev/null || true)"

echo
echo "Puerto:"
if ss -ltn 2>/dev/null | grep -Eq ':11434\b'; then
  ss -ltn 2>/dev/null | grep -E ':11434\b'
else
  echo "  11434 no está escuchando"
fi

if [ -x "$OLLAMA_BIN" ]; then
  echo
  echo "Modelos cargados:"
  "$OLLAMA_BIN" ps 2>/dev/null || echo "  Ollama no responde"
  echo
  echo "Modelos instalados:"
  "$OLLAMA_BIN" list 2>/dev/null || true
fi

echo
"$SCRIPT_DIR/measure-jarvis.py"

echo
echo "Disco:"
df -h /home/arduino 2>/dev/null | tail -1 || true
