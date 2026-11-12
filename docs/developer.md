# JarvisUNOQ — Documentación de desarrollador

Guía para entender, mantener y extender el código de la fase 1 (chat de texto).
Todo el software corre en la Arduino UNO Q; el repositorio no tiene build system ni
dependencias externas.

---

## 1. Mapa del proyecto

```text
JarvisUNOQ/
├── config/
│   ├── ollama.service      Unidad systemd del servidor de modelos
│   └── sudoers-jarvis      Regla NOPASSWD acotada a systemctl ollama
├── scripts/
│   ├── jarvis-chat.py      Cliente HTTP de chat (stdlib)
│   ├── measure-jarvis.py   Muestreador de CPU/RSS vía /proc
│   ├── start-jarvis.sh     Arranque + espera de readiness
│   ├── stop-jarvis.sh      Descarga de modelos + parada
│   ├── status-jarvis.sh    Reporte de estado
│   └── deploy-unoq.sh      Empaquetado y copia por SSH
├── docs/                   Documentación
└── README.md
```

No hay paquetes, módulos compartidos ni archivos de configuración del cliente:
los defaults viven en el código y se pueden pisar por CLI o variables de entorno.

---

## 2. Arquitectura de ejecución

```text
┌─────────────┐   stdin    ┌──────────────────┐   HTTP/JSON   ┌──────────────┐
│ Terminal    │ ─────────▶ │ jarvis-chat.py   │ ────────────▶ │ ollama serve │
│ (SSH)       │            │ urllib.request   │ ◀──────────── │ llama-server │
└─────────────┘   stdout   └──────────────────┘   respuesta   └──────────────┘
```

- El cliente es **efímero**: se ejecuta, conversa y termina.
- Ollama es **persistente**: `ollama.service`, usuario `arduino`, bind loopback.
- El modelo se carga bajo demanda y se descarga según `keep_alive`.

### Capas y responsabilidades

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Presentación | `jarvis-chat.py` | Parsear CLI, imprimir, mantener historial |
| Transporte | `jarvis-chat.py` | Serializar JSON, POST, timeouts, errores |
| Inferencia | Ollama | Carga del modelo, sampling, métricas |
| Supervisión | `start/stop/status` | Ciclo de vida del servicio |
| Observabilidad | `measure-jarvis.py` | CPU y RSS por proceso, memoria global |

---

## 3. `scripts/jarvis-chat.py`

### 3.1 Constantes

| Constante | Valor | Origen |
|---|---|---|
| `DEFAULT_MODEL` | `qwen2.5:0.5b-instruct-q4_K_M` | `JARVIS_MODEL` o literal |
| `DEFAULT_HOST` | `127.0.0.1:11434` | `OLLAMA_HOST` o literal |
| `DEFAULT_SYSTEM` | Prompt en español rioplatense | Literal en el código |

El system prompt es la pieza más delicada del cliente. Está redactado para
**negar capacidades** que el modelo no tiene y para limitar la longitud de la
respuesta. Si se acorta demasiado, el 0.5B empieza a inventar que puede leer
archivos o ejecutar comandos.

### 3.2 API de funciones

#### `build_url(host: str) -> str`

Normaliza el host. Si ya empieza con `http://` o `https://`, lo respeta; si no,
antepone `http://` y elimina la barra final.

```python
build_url("127.0.0.1:11434")      # "http://127.0.0.1:11434"
build_url("http://host:1234/")   # "http://host:1234"
```

#### `request_chat(host, model, messages, max_tokens, temperature, repeat_penalty, num_ctx, timeout) -> dict`

Construye el payload y ejecuta el POST a `/api/chat`. Devuelve el JSON ya
decodificado.

Payload efectivo:

```json
{
  "model": "qwen2.5:0.5b-instruct-q4_K_M",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "stream": false,
  "keep_alive": "15m",
  "options": {
    "num_ctx": 4096,
    "num_predict": 64,
    "temperature": 0.3,
    "repeat_penalty": 1.2
  }
}
```

> **Detalle:** el cliente envía `keep_alive: "15m"` en cada request, lo que
> **pisa** el `OLLAMA_KEEP_ALIVE=5m` del servicio para esa conversación. Es
> intencional: mantener el modelo cargado mientras el usuario interactúa. Si se
> busca liberar RAM rápido, bajar ambos valores.

#### `format_stats(data: dict) -> str`

Convierte las duraciones en nanosegundos que devuelve Ollama a segundos y arma
una línea legible:

```text
total=3.41s load=0.00s prompt=91 tok/2.68s eval=8 tok/0.71s
```

#### `ask(args, messages) -> str | None`

Ejecuta la request y devuelve el texto limpio (`message.content.strip()`).
Maneja tres errores:

| Excepción | Salida |
|---|---|
| `HTTPError` | `Error HTTP <code>: <body>` en `stderr`, retorna `None` |
| `URLError` | Mensaje de conexión + sugerencia de `start-jarvis.sh` |
| `TimeoutError` | `Ollama no respondió a tiempo.` |

Si `args.stats` está activo, imprime la línea de métricas en `stderr` para no
contaminar `stdout` (importante para usar el cliente en pipes).

#### `trim_history(history: list, max_messages: int) -> list`

Conserva el mensaje de sistema y los últimos `max_messages` mensajes. Evita que
el contexto crezca sin límite y que el prompt eval se dispare.

```python
trim_history([sys, u1, a1, u2, a2, u3], 4)  # [sys, a1, u2, a2, u3]
```

#### `run_interactive(args) -> None`

Bucle de lectura. Inicializa el historial con el system prompt, lee de `stdin`,
agrega el turno del usuario, llama a `ask` y agrega la respuesta al historial.
Si `ask` devuelve `None`, revierte el último mensaje de usuario para no dejar el
historial inconsistente.

#### `main() -> None`

Define el contrato CLI con `argparse`. Si no hay `--interactive` ni prompt
posicional, falla con `parser.error(...)`. Si `ask` devuelve `None` en modo
one-shot, sale con código 1.

### 3.3 Contrato CLI

```text
jarvis-chat.py [prompt ...] [-i] [--model M] [--system S] [--host H]
               [--max-tokens N] [--temperature T] [--repeat-penalty P]
               [--num-ctx N] [--history N] [--timeout S] [--stats]
```

| Flag | Tipo | Default | Efecto |
|---|---|---|---|
| `prompt` | positional | — | Se une con espacios |
| `-i`, `--interactive` | flag | off | Bucle conversacional |
| `--model` | str | 0.5B | Modelo de Ollama |
| `--system` | str | prompt local | Reemplaza el system prompt |
| `--host` | str | `127.0.0.1:11434` | Endpoint |
| `--max-tokens` | int | 64 | `num_predict` |
| `--temperature` | float | 0.3 | Sampling |
| `--repeat-penalty` | float | 1.2 | Penalización |
| `--num-ctx` | int | 4096 | Ventana |
| `--history` | int | 4 | Mensajes conservados |
| `--timeout` | float | 180 | Timeout HTTP |
| `--stats` | flag | off | Métricas en `stderr` |

### 3.4 Variables de entorno

| Variable | Efecto |
|---|---|
| `JARVIS_MODEL` | Cambia el modelo por defecto sin tocar el código |
| `OLLAMA_HOST` | Cambia el host por defecto |

Se evalúan **al importar** el módulo, no en cada request.

---

## 4. `scripts/measure-jarvis.py`

Lee `/proc` directamente; no depende de `psutil`.

### 4.1 Estructuras

```python
GROUPS = {
    "ollama": ["/home/arduino/ollama/bin/ollama serve", "ollama serve"],
    "llama-server": ["llama-server"],
}
CLK_TCK = os.sysconf("SC_CLK_TCK")     # ticks por segundo
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") # bytes por página
```

### 4.2 Funciones

| Función | Devuelve | Detalle |
|---|---|---|
| `pids_for(pattern)` | `set[int]` | Ejecuta `pgrep -f` y parsea la salida |
| `group_pids()` | `dict[str, list[int]]` | Agrupa por servicio, sin duplicados |
| `read_proc(pid)` | `dict \| None` | Nombre, ticks de CPU y RSS desde `/proc/<pid>/stat` y `statm` |
| `read_meminfo()` | `dict[str, int]` | Convierte `/proc/meminfo` a bytes |
| `read_cpu_total()` | `tuple[int, int]` | Total y idle de `/proc/stat` |
| `human_mib(value)` | `str` | Convierte bytes a MiB con un decimal |
| `main()` | — | Muestrea dos veces y calcula deltas |

El cálculo de CPU usa la diferencia de ticks entre dos muestras:

```text
CPU% = 100 × Δticks / CLK_TCK / intervalo
```

El CPU del sistema se calcula con la diferencia de `idle` sobre el total de
`/proc/stat`. Salida disponible en texto o `--json`.

---

## 5. Scripts de shell

### 5.1 `start-jarvis.sh`

1. `sudo -n systemctl start ollama` (falla explícito si no hay sudoers).
2. Sondea `http://127.0.0.1:11434/api/tags` cada segundo, hasta 60 intentos.
3. Si no responde, error y `exit 1`.
4. Si responde, delega en `status-jarvis.sh`.

`set -euo pipefail` hace que cualquier fallo no controlado aborte el script.

### 5.2 `stop-jarvis.sh`

1. Si el servicio está activo, ejecuta `ollama stop` para ambos modelos.
2. `sudo -n systemctl stop ollama`.
3. Espera hasta 10 s a que el puerto 11434 deje de escuchar.
4. Imprime el estado final.

### 5.3 `status-jarvis.sh`

Reporte de solo lectura: `systemctl is-active`, `ss -ltn`, `ollama ps`,
`ollama list`, `measure-jarvis.py` y `df -h /home/arduino`. Usa `set -uo pipefail`
sin `-e` para que un comando ausente no corte el reporte.

### 5.4 `deploy-unoq.sh`

Empaqueta con `tar` (excluyendo `.git`, `__pycache__`, `*.pyc`, `*.log`, `.env`),
transfiere por `ssh` y crea enlaces simbólicos en el home remoto. Es idempotente:
se puede correr las veces que haga falta.

Parámetros por variable de entorno: `UNOQ_HOST`, `UNOQ_USER`, `UNOQ_PORT`,
`UNOQ_KEY`. Todos con default, ninguno hardcodeado en la lógica.

---

## 6. `config/ollama.service`

```ini
[Service]
Type=simple
User=arduino
Environment=OLLAMA_MODELS=/home/arduino/.ollama/models
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_KEEP_ALIVE=5m
Environment=OLLAMA_CONTEXT_LENGTH=4096
Environment=OLLAMA_NUM_THREADS=4
ExecStart=/home/arduino/ollama/bin/ollama serve
Restart=always
RestartSec=5
TimeoutStopSec=15
```

Cada variable responde a una restricción medida:

| Variable | Restricción |
|---|---|
| `OLLAMA_MODELS` | La partición root está casi llena |
| `OLLAMA_HOST` | No exponer la API a la LAN |
| `MAX_LOADED_MODELS` | 0.5B + 1.5B no caben juntos |
| `NUM_PARALLEL` | Evitar contención de RAM/CPU |
| `KEEP_ALIVE` | Liberar memoria tras inactividad |
| `CONTEXT_LENGTH` | 32k por defecto consume demasiada RAM |
| `NUM_THREADS` | Coincide con los 4 núcleos |

---

## 7. Cómo extender

### 7.1 Agregar un flag al cliente

1. Añadir el argumento en `main()` con `parser.add_argument`.
2. Pasarlo a `request_chat` (o usarlo en `ask`).
3. Documentarlo en `README.md` y `datasheet.md`.

Ejemplo: forzar `top_p`.

```python
parser.add_argument("--top-p", type=float, default=0.9)
...
"options": {..., "top_p": top_p}
```

### 7.2 Agregar un modelo

```bash
ollama pull <modelo>:<tag>
~/jarvis-chat --model <modelo>:<tag> --stats "hola"
```

Antes de adoptarlo, medir con `--stats`: carga, prompt eval y generación. Un
modelo que no entra en RAM produce swap y arruina la latencia.

### 7.3 Streaming de respuestas

Ollama soporta `stream=true` con NDJSON. El cambio afecta a `request_chat`:
habría que leer línea por línea e imprimir `message.content` incrementalmente.
Ventaja: percepción de velocidad. Costo: más complejidad y un `readline` por
token.

### 7.4 Capa de herramientas (function calling)

El modelo actual no ejecuta nada. Para agregar acciones hace falta:

1. Un registro de herramientas con nombre, descripción y esquema JSON.
2. Un bucle que detecte `tool_calls`, ejecute la función y devuelva el resultado
   al modelo.
3. Permisos explícitos y lista blanca de comandos.

Con 0.5B la confiabilidad de `tool_calls` es baja; el 1.5B es el mínimo
razonable, y aun así requiere validación estricta de argumentos.

### 7.5 Persistencia de historial

Opción simple: guardar la lista `messages` en JSON por sesión. Opción robusta:
SQLite con tablas `sessions` y `messages`. Considerar que cada mensaje extra
aumenta el prompt eval, que es el cuello de botella.

### 7.6 Fase 2 (voz)

El diseño previsto serializa STT, LLM y TTS para no entrar en swap:

```text
mic → VAD → STT → jarvis-chat (o API directa) → TTS → parlante
```

Puntos de integración:

- Reemplazar `input()` por una transcripción.
- Reemplazar `print()` por una llamada a TTS.
- Medir cada etapa por separado; el presupuesto total es <10 s por turno.

---

## 8. Convenciones y trampas

- **No agregar dependencias** sin `requirements.txt` y justificación de RAM.
- **No tocar `/`**: cualquier artefacto grande va a `/home/arduino`.
- **No exponer 11434**: `OLLAMA_HOST=0.0.0.0` rompe el modelo de seguridad.
- **No subir `num_ctx` a ciegas**: 4096 es el equilibrio medido; 32k consume
  memoria de más y hace lento el prompt eval.
- **El timeout debe superar la carga del modelo**: 180 s cubre el 1.5B en frío.
- **`stdout` es para la respuesta**, `stderr` para métricas y errores.
- **Los scripts deben ser idempotentes** y fallar con mensajes accionables.

---

## 9. Pruebas manuales

No hay suite automatizada (el proyecto es un prototipo de exploración). La
verificación mínima tras un cambio:

```bash
python3 -m py_compile scripts/*.py
bash -n scripts/*.sh

~/start-jarvis.sh
~/status-jarvis.sh
~/jarvis-chat --stats "Responde exactamente: hola"
~/jarvis-chat --interactive        # dos turnos y salir
~/stop-jarvis.sh
```

Criterios de aceptación:

| Prueba | Criterio |
|---|---|
| Arranque | `/api/tags` responde en <60 s |
| Chat en frío | < 15 s con 0.5B |
| Chat en caliente | 1–4 s para respuestas cortas |
| Memoria | > 2 GiB disponibles con 0.5B |
| Parada | Puerto 11434 cerrado en <10 s |
| Error de servicio | Mensaje claro, sin traza de Python |

---

## 10. Depuración

| Necesidad | Herramienta |
|---|---|
| Ver el payload exacto | Añadir `print(json.dumps(payload))` temporal en `request_chat` |
| Ver la respuesta cruda | `curl` a `/api/chat` (ver README, sección API local) |
| Ver errores del servicio | `journalctl -u ollama -n 80 --no-pager` |
| Ver quién ocupa RAM | `~/status-jarvis.sh` o `measure-jarvis.py --json` |
| Ver el socket | `ss -ltnp | grep 11434` |
| Ver la versión | `~/.local/bin/ollama --version` |

Para reproducir una medición, usar siempre el mismo prompt
(`"Responde exactamente: hola"`) y el mismo estado de carga del modelo.
