#!/usr/bin/env bash
set -euo pipefail

OLLAMA_BIN="${OLLAMA_BIN:-$HOME/.local/bin/ollama}"

if systemctl is-active --quiet ollama; then
  if [ -x "$OLLAMA_BIN" ]; then
    "$OLLAMA_BIN" stop qwen2.5:0.5b-instruct-q4_K_M >/dev/null 2>&1 || true
    "$OLLAMA_BIN" stop qwen2.5:1.5b-instruct-q4_K_M >/dev/null 2>&1 || true
  fi
  sudo -n systemctl stop ollama
  echo "ollama detenido. Jarvis no consume CPU/RAM."
else
  echo "ollama ya estaba detenido."
fi

for _ in $(seq 1 20); do
  if ! ss -ltn 2>/dev/null | grep -q ':11434'; then
    break
  fi
  sleep 0.5
done

echo "Estado final:"
printf '  %-9s %s\n' ollama "$(systemctl is-active ollama 2>/dev/null || true)"
