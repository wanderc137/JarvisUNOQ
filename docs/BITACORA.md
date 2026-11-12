# Bitácora

## 2026-11-04 — Estado final: sin OpenClaw

- El usuario pidió eliminar OpenClaw porque consumía recursos sin aportar al
  chat rápido.
- Se detuvo y deshabilitó `openclaw.service`, se borró la unidad y se eliminaron
  `/home/arduino/.openclaw` (852 MB) y `/home/arduino/.npm` (332 MB).
- El sudoers quedó limitado a `systemctl start/stop/restart ollama`.
- Memoria con el 0.5B cargado: **1,1 GiB usados, 1,9 GiB libres, 2,4 GiB
  disponibles**.
- Chat verificado: 3,41 s (prompt 91 tok/2,68 s; generación 8 tok/0,71 s).
- `start-jarvis.sh`, `stop-jarvis.sh`, `status-jarvis.sh` y `measure-jarvis.py`
  quedaron solo con Ollama.

## 2026-11-03 — Descubrimiento

- La UNO Q reporta **3,6 GiB de RAM**, no 8 GiB. La partición `/home/arduino` es
  la única con espacio suficiente (18 GB).
- No había Node, npm, pip ni Ollama. Sí había `curl`, `git`, `python3`, `zstd`.
- OpenClaw exige Node 24.16+ o 26.1+. El video de Sascha Segan usa Node 22 y ya
  está desactualizado para la versión actual.
- Se descargó el instalador local `install-cli.sh` (73 KB) y se instaló OpenClaw
  con Node 24.22.1 en `/home/arduino/.openclaw`.

## 2026-11-04 — Ollama y modelos

- El tar ARM64 de Ollama v0.40.14 pesa 1,5 GB e incluye CUDA 12/13. Se extrajo
  sin esas carpetas: 63 MB. Se copió a `/home/arduino/ollama` y se creó
  `/home/arduino/.local/bin/ollama`.
- Se creó `ollama.service` con `OLLAMA_MODELS` en la partición home y
  `OLLAMA_HOST=127.0.0.1:11434`.
- Se descargaron:
  - `qwen2.5:0.5b-instruct-q4_K_M` (397 MB).
  - `qwen2.5:1.5b-instruct-q4_K_M` (986 MB).
- El 1.5B respondió bien, pero a 3,2 tok/s de generación y 5,2 tok/s de prompt
  eval. El 0.5B es ~3× más rápido.

## 2026-11-04 — OpenClaw configurado

- Onboarding no interactivo con provider Ollama y agente `jarvis`.
- Gateway en `127.0.0.1:18789`, servicio `openclaw.service`.
- El gateway tarda ~112 s en llegar a `/ready` y puede consumir 1,2–1,4 GB de
  RSS; después hace mantenimiento durante ~39 s más.
- Se agregó el 0.5B al provider y se validó la configuración.

## 2026-11-04 — Arranque y chat medidos

- `stop-jarvis.sh` + `start-jarvis.sh` desde cero: **2m39s**. El gateway queda
  `ready` y el script espera 45 s de mantenimiento.
- Primer chat tras el arranque (modelo sin cargar): **11,02 s**.
- Chat inmediato en caliente: **1,36 s** (12 tokens); otra prueba: 2,44 s
  (21 tokens); respuesta de tres oraciones: 7,86 s (57 tokens).
- En reposo: CPU del sistema 0,3 %, gateway ~1,2 GB RSS, `llama-server` 510 MB,
  RAM disponible ~1,38 GiB.
- `start-jarvis.sh` y `status-jarvis.sh` usan `/ready` del gateway, no el CLI
  `openclaw health`, que puede colgarse.

## Intentos fallidos

### Contexto demasiado chico

El primer agente usó `num_ctx=4096`, pero el prompt real era de 12.463 tokens.
Ollama devolvió HTTP 400 por exceso de contexto. Se subió a 12.288 y luego se
probó con 0.5B.

### Prompt del agente

Aun con contexto suficiente, el prompt del agente ronda los 4.360 tokens. La CPU
procesa ~5 tok/s, así que el turno no termina antes del timeout de 240 s. Se
intentó `--local-model-lean`, `--cwd` vacío y `agent exec`; el 0.5B también
superó los 200 s.

### `--isolated`

`openclaw agent exec --isolated` no usa la configuración ambiental y falla con
`Ollama requires authentication`. No sirve para esta instalación.

## Decisión

- **Chat rápido:** `scripts/jarvis-chat.py` contra `/api/chat` de Ollama, modelo
  0.5B, contexto 4096, system prompt corto.
- **OpenClaw:** **eliminado** el 2026-11-04. Consumía ~1,2 GB de RAM y su agente
  tardaba más de 4 minutos por turno; no aportaba al chat de texto.
- **1.5B:** disponible para respuestas de mayor calidad, no para velocidad.

## Lecciones

- La UNO Q no es una placa de inferencia LLM; es un gateway/nodo excelente.
- El cuello de botella es el **prompt eval**, no solo la generación.
- El contexto por defecto de Ollama (32768) consume memoria de más; fijarlo en
  4096 cambia el presupuesto.
- OpenClaw era potente, pero su prompt de agente resultó incompatible con una
  CPU de 4 núcleos y 3,6 GiB si se busca latencia de conversación; por eso se
  eliminó.
- Para el auto, la fase de voz debe serializar STT, LLM y TTS para no entrar en
  swap.
