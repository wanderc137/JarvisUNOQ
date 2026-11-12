# Rendimiento medido

Todas las pruebas se hicieron en la Arduino UNO Q, por SSH, sin GPU y sin
procesos de los proyectos de rostros. Fecha: **2026-11-04**.

## Resumen

| Camino | Modelo | Latencia típica | Viabilidad |
|---|---|---:|---|
| `jarvis-chat.py` (Ollama directo) | Qwen2.5 0.5B Q4 | **~11 s en frío, ~1,4–2,4 s en caliente** | Sí |
| `jarvis-chat.py` (Ollama directo) | Qwen2.5 1.5B Q4 | ~20 s en frío | Sí, con paciencia |

OpenClaw se evaluó y se eliminó: su gateway consumía ~1,2 GB de RAM y el agente
completo tardaba más de 4 minutos por turno. Las mediciones históricas de
OpenClaw no aplican al estado actual.

## Benchmarks crudos de Ollama

Prompt de prueba: `"Responde exactamente: hola"` (36 tokens de entrada).

| Modelo | Carga | Prompt eval | Generación | Total | RSS |
|---|---:|---:|---:|---:|---:|
| `qwen2.5:0.5b-instruct-q4_K_M` | 3,89 s | 2,25 s (36 tok, ~16 tok/s) | 16 tok en 1,50 s (~10,6 tok/s) | **7,77 s** | 940 MB con contexto 32768 |
| `qwen2.5:1.5b-instruct-q4_K_M` | 8,9 s | 6,96 s (36 tok, ~5,2 tok/s) | 14 tok en 4,42 s (~3,2 tok/s) | **20,3 s** | 1,2 GB |

El 0.5B es aproximadamente **3× más rápido** que el 1.5B. La diferencia se nota
mucho más con prompts largos.

## Medición con el chat real

Con el 0.5B cargado y el prompt del sistema de `jarvis-chat.py` (que incluye la
aclaración de que no tiene acceso a disco, archivos ni comandos):

| Prueba | Total | Prompt eval | Generación | Tokens |
|---|---:|---:|---:|---:|
| Saludo corto en frío (modelo sin cargar) | **11,02 s** | 93 tok / 5,90 s | 19 tok / 1,86 s | 19 |
| Saludo inmediato en caliente | **1,36 s** | 93 tok / 0,13 s | 12 tok / 1,15 s | 12 |
| Otra respuesta corta en caliente | **2,44 s** | 80 tok / 0,11 s | 21 tok / 2,25 s | 21 |
| Respuesta de 3 oraciones | **7,86 s** | 87 tok / 2,15 s | 57 tok / 5,69 s | 57 |
| Tras eliminar OpenClaw | **3,41 s** | 91 tok / 2,68 s | 8 tok / 0,71 s | 8 |

La diferencia entre 1,36 s y 2,44 s depende de la longitud de la respuesta y del
estado del modelo. Para conversación corta, el orden de magnitud es **1–4 s en
caliente**.

## Memoria y CPU

Con OpenClaw eliminado y el 0.5B cargado:

```text
MemTotal:       3,6 GiB
Mem usado:      1,1 GiB
Mem libre:      1,9 GiB
Mem disponible: 2,4 GiB
Modelo 0.5B:    486 MB
Proceso ollama: ~40 MB
Swap:           ~158 MiB
CPU:            4 núcleos a 2.016 MHz
Temperatura:    31–39 °C
```

Durante la generación, `llama-server` usa los 4 núcleos y el sistema llega a
~99 % de CPU. En reposo, con el modelo cargado, el CPU del sistema queda en
~0,3 %.

El 1.5B usa ~1,2 GB adicionales cuando se carga. No conviene tenerlo cargado
junto con el 0.5B; `OLLAMA_MAX_LOADED_MODELS=1` hace que Ollama descargue uno
antes de cargar el otro.

## Arranque

- `ollama.service` arranca en pocos segundos.
- `start-jarvis.sh` espera `/api/tags` hasta 60 s y luego muestra el estado.
- El modelo se carga la primera vez que se usa: ~3–7 s adicionales.
- El chat con Ollama directo no tiene el arranque de 2 minutos que tenía el
  gateway de OpenClaw.

## Configuración recomendada

- Modelo de chat: `qwen2.5:0.5b-instruct-q4_K_M`.
- Contexto: 4096 (`OLLAMA_CONTEXT_LENGTH=4096`, `num_ctx=4096`).
- `OLLAMA_MAX_LOADED_MODELS=1`.
- `OLLAMA_NUM_PARALLEL=1`.
- `OLLAMA_KEEP_ALIVE=15m` para el chat; 5m si se quiere liberar RAM antes.
- Un solo cliente de chat a la vez.
- No mantener STT y TTS cargados junto con el LLM; serializar en la fase 2.

## Reproducir

```bash
~/start-jarvis.sh
~/jarvis-chat --stats "Responde exactamente: hola"
~/status-jarvis.sh
```

Para el 1.5B:

```bash
~/jarvis-chat --stats \
  --model qwen2.5:1.5b-instruct-q4_K_M \
  "Responde exactamente: hola"
```

## Nota sobre las expectativas

La UNO Q es excelente como gateway, controlador y nodo de sensores. No es una
placa de inferencia LLM. El 0.5B permite una experiencia de texto aceptable; el
1.5B es el máximo razonable para calidad, no para velocidad. Para un Jarvis de
voz fluido en el auto, la alternativa realista es un modelo cloud o un híbrido
local/cloud cuando haya conectividad.
