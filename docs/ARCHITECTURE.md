# Arquitectura

## Fase 1: texto local

```text
┌──────────────┐     texto      ┌─────────────────────┐
│ Usuario      │ ─────────────▶ │ jarvis-chat.py      │
│ (SSH o CLI)  │                │ urllib + JSON       │
└──────────────┘                └──────────┬──────────┘
                                           │ POST /api/chat
                                           ▼
                                ┌─────────────────────┐
                                │ Ollama              │
                                │ 127.0.0.1:11434     │
                                │ qwen2.5 0.5B Q4     │
                                └──────────┬──────────┘
                                           │
                                           ▼
                                Respuesta en español
```

`jarvis-chat.py` usa la API nativa de Ollama (`/api/chat`), no el endpoint
OpenAI-compatible `/v1`. El system prompt es corto, aclara que el bot no tiene
acceso a disco, archivos, cámara ni comandos, y el contexto se limita a 4096
tokens para que la respuesta llegue en segundos.

El modelo no ejecuta acciones: solo conversa. Cualquier acceso a archivos,
sensores o comandos requeriría una capa de herramientas aparte, que en esta
placa todavía no existe.

## Servicios y puertos

| Servicio | Puerto | Bind | Función |
|---|---:|---|---|
| `ollama.service` | 11434 | `127.0.0.1` | Servidor de modelos |
| SSH | 22 / 2222 | LAN | Administración |

Ollama escucha solo en loopback. No se expone a la WiFi ni a internet.

## Presupuesto de memoria

| Componente | RSS aproximado |
|---|---:|
| Sistema base Debian | 300–500 MB |
| `ollama serve` | 40–150 MB |
| `llama-server` 0.5B | 500–940 MB |
| `llama-server` 1.5B | ~1,2 GB |

Con el 0.5B cargado quedan ~2,4 GiB disponibles. El 1.5B entra en swap si se
carga junto con otras tareas; por eso el chat usa 0.5B y `OLLAMA_MAX_LOADED_MODELS=1`.

## Por qué no está OpenClaw

OpenClaw se instaló, se probó y se eliminó. Su gateway consumía ~1,2 GB de RAM y
el agente completo armaba un prompt de ~4.300 tokens; a la velocidad de prompt
eval de esta CPU (~5 tok/s), el turno tardaba más de 4 minutos. Para el chat de
texto rápido no aportaba nada frente a Ollama directo. La decisión y las
mediciones quedaron en `docs/BITACORA.md` y `docs/PERFORMANCE.md`.

## Fase 2: voz en el auto

```text
┌────────────┐   audio   ┌──────────────┐   texto   ┌─────────────┐
│ Micrófono  │ ────────▶ │ STT local    │ ────────▶ │ Ollama      │
│ USB        │           │ whisper.cpp  │           │ qwen2.5 0.5B│
└────────────┘           │ o Vosk       │           └──────┬──────┘
                                                           │ texto
                                                           ▼
┌────────────┐   audio   ┌──────────────┐   texto   ┌─────────────┐
│ Parlante   │ ◀──────── │ TTS local    │ ◀──────── │ Respuesta   │
│ del auto   │           │ Piper        │           │             │
└────────────┘           └──────────────┘           └─────────────┘
```

Recomendaciones para la fase 2:

- **STT:** `whisper.cpp` con modelo `tiny` o `base` en español, o Vosk con un
  modelo chico. Ejecutar solo mientras se escucha.
- **TTS:** Piper con una voz en español; es liviano y rápido en CPU.
- **Serializar:** no mantener STT, LLM y TTS cargados a la vez. Con 3,6 GiB, la
  suma de modelos puede entrar en swap.
- **Audio:** micrófono USB y salida de audio del auto. La UNO Q tiene un solo
  puerto USB-C; si se usa para alimentación, hace falta un hub USB-C con PD o
  alimentar por VIN y usar host mode.
- **Palabra de activación:** opcional. Se puede empezar con un botón físico o
  con una tecla, y agregar wake word después.
- **Latencia objetivo:** STT ~1–3 s, LLM ~2–5 s, TTS ~1–2 s. La conversación
  completa debería quedar en menos de 10 s por turno.

## Flujo de una conversación de voz

1. El usuario presiona un botón o dice la palabra de activación.
2. Se graba audio hasta detectar silencio.
3. STT transcribe a texto.
4. `jarvis-chat.py` (o un cliente equivalente) envía el texto a Ollama.
5. La respuesta se pasa a TTS.
6. Se reproduce el audio y se vuelve al estado de escucha.

## Seguridad

- Ollama y SSH escuchan en loopback o LAN, no en internet.
- No hay claves ni tokens en el repositorio.
- El chat no tiene acceso a archivos ni comandos; no puede modificar el sistema.
- La contraseña de `sudo` no se guarda en el proyecto.

## Limitaciones conocidas

- La UNO Q reporta 3,6 GiB de RAM, no 8 GiB.
- El 0.5B es rápido pero limitado; el 1.5B es más coherente pero lento.
- El modelo puede alucinar capacidades si se le pregunta por acciones que no
  puede hacer; el system prompt lo aclara, pero no lo garantiza al 100 %.
- La fase de voz todavía no está implementada.
