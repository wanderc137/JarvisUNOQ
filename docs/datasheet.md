# JarvisUNOQ — Hoja de datos (datasheet)

**Asistente conversacional local para Arduino UNO Q**
Versión documentada: fase 1 (texto) · Fecha de mediciones: 2026-11-04

---

## 1. Resumen

JarvisUNOQ es un asistente de texto que corre **íntegramente dentro de una
Arduino UNO Q**, sin GPU, sin conexión a internet y sin telemetría. El usuario se
conecta por SSH, escribe una pregunta y recibe una respuesta breve en español
generada por un modelo Qwen2.5 cuantizado, servido por Ollama en loopback.

No es un producto comercial ni un asistente de voz. Es la fase 1 —validada y
medida— de un proyecto mayor orientado al automóvil.

| Aspecto | Valor |
|---|---|
| Tipo de dispositivo | Asistente conversacional embebido (solo texto) |
| Plataforma | Arduino UNO Q, Debian 13 aarch64 |
| Motor | Ollama v0.40.14 |
| Modelos | Qwen2.5 Instruct 0.5B y 1.5B, Q4_K_M |
| Interfaz | Terminal SSH (`jarvis-chat.py`) |
| Latencia típica | 1,4–2,4 s en caliente; 11 s en frío |
| Consumo de RAM | ~1,1 GiB usados, ~2,4 GiB disponibles |
| Conectividad requerida | Ninguna saliente; SSH entrante en LAN |
| Licencia | MIT |

---

## 2. Principio de funcionamiento

Un modelo de lenguaje es una red neuronal entrenada para predecir el siguiente
token. En esta placa no hay GPU ni NPU: la inferencia se ejecuta en los cuatro
núcleos CPU mediante `llama.cpp`, que Ollama integra. Para que quepa en 3,6 GiB
de RAM, el modelo se almacena en **Q4_K_M**, una cuantización de ~4,8 bits
efectivos por peso que reduce el tamaño aproximadamente cuatro veces respecto de
FP16 con una pérdida de calidad acotada.

El recorrido de una consulta es:

```text
SSH → jarvis-chat.py → HTTP POST /api/chat → Ollama → llama-server → Qwen2.5
                                                                        │
SSH ← texto en la terminal ← JSON de respuesta ←────────────────────────┘
```

El cliente no mantiene un demonio: existe mientras dura la conversación. Ollama
sí corre como servicio `systemd`, escuchando **solo** en `127.0.0.1:11434`.

### Qué hace el system prompt

El prompt de sistema es corto y restrictivo. Le indica al modelo que:

- responda en español rioplatense, breve (1–3 oraciones, menos de 60 palabras);
- **no** tiene acceso a archivos, disco, cámara, internet, sensores ni comandos;
- no invente datos, acciones, tiempos ni métricas;
- responda solo a la última pregunta y no repita respuestas previas.

Esto reduce —no elimina— las alucinaciones de capacidad.

---

## 3. Especificaciones técnicas

### 3.1 Hardware

| Parámetro | Valor medido |
|---|---|
| Placa | Arduino UNO Q |
| SoC Linux | Qualcomm, 4 núcleos Kryo-V2 |
| Frecuencia | 2.016 MHz (hasta 2,0 GHz) |
| RAM visible | **3,6 GiB** (no 8 GB) |
| Swap en uso con 0,5B | ~158 MiB |
| Almacenamiento `/` | 9,8 GB, casi lleno |
| Almacenamiento `/home/arduino` | 18 GB, ~14 GB libres |
| Temperatura en reposo | 31–39 °C |
| GPU / NPU | No utilizadas |

### 3.2 Software

| Componente | Versión / detalle |
|---|---|
| Sistema operativo | Debian 13 «trixie» |
| Arquitectura | aarch64 |
| Init | `systemd` |
| Ollama | v0.40.14, binario ARM64 sin CUDA |
| Python | 3.x, solo biblioteca estándar |
| Modelo rápido | `qwen2.5:0.5b-instruct-q4_K_M` (397 MB) |
| Modelo de calidad | `qwen2.5:1.5b-instruct-q4_K_M` (986 MB) |
| Contexto | 4096 tokens |
| Hilos | 4 |

### 3.3 Rendimiento

| Escenario | Latencia | Tokens |
|---|---:|---:|
| Primera consulta (modelo sin cargar) | **11,02 s** | 19 |
| Consulta en caliente, respuesta corta | **1,36 s** | 12 |
| Consulta en caliente, respuesta media | **2,44 s** | 21 |
| Respuesta de tres oraciones | **7,86 s** | 57 |
| 1.5B, primera consulta | ~20,3 s | 14 |

Throughput medido con el 0.5B: **~16 tok/s** de prompt eval y **~10,6 tok/s** de
generación. Con el 1.5B: **~5,2** y **~3,2 tok/s** respectivamente.

### 3.4 Límites operativos

| Límite | Valor |
|---|---|
| Clientes simultáneos | 1 (`OLLAMA_NUM_PARALLEL=1`) |
| Modelos cargados a la vez | 1 |
| Contexto máximo práctico | 4096 tokens |
| Tokens máximos por respuesta | 64 (`num_predict`) |
| Timeout del cliente | 180 s |
| Persistencia de historial | Ninguna (solo sesión) |

---

## 4. Instalación y dependencias

### 4.1 Dependencias

**El proyecto no tiene dependencias Python externas.** No existe
`requirements.txt` y no hace falta: `jarvis-chat.py` y `measure-jarvis.py` usan
únicamente módulos de la biblioteca estándar (`argparse`, `json`, `os`,
`subprocess`, `sys`, `time`, `urllib`). Por lo tanto **no se crea un entorno
virtual ni se ejecuta `pip install`**.

Las dependencias reales son del sistema operativo:

| Dependencia | Tipo | Uso | Verificación |
|---|---|---|---|
| `python3` | Paquete del SO | Ejecutar los scripts | `python3 --version` |
| `curl` | Paquete del SO | Descargar Ollama, sondear la API | `curl --version` |
| `zstd` | Paquete del SO | Extraer el tar de Ollama | `zstd --version` |
| `tar` | Base | Desempaquetar | `tar --version` |
| `systemd` | Base | Servicio `ollama.service` | `systemctl --version` |
| `ss` (iproute2) | Paquete del SO | Ver el socket 11434 | `ss -ltn` |
| `pgrep` (procps) | Paquete del SO | Medir procesos | `pgrep -V` |
| Ollama | Binario | Servidor de modelos | `~/.local/bin/ollama --version` |

En Debian 13 todos están presentes salvo Ollama, que se instala según
[`INSTALL.md`](INSTALL.md).

### 4.2 Si en el futuro se agregan dependencias

El procedimiento correcto —y el único que este repositorio aceptaría— es:

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

Con su correspondiente `requirements.txt` versionado. Hoy ese archivo **no
existe** y no debe crearse vacío: sería ruido.

### 4.3 Secuencia de instalación

1. Copiar el proyecto con `./scripts/deploy-unoq.sh`.
2. Instalar Ollama sin CUDA (ver `INSTALL.md`).
3. Habilitar `ollama.service` y descargar los dos modelos.
4. Instalar la regla de sudoers acotada.
5. Verificar con `~/status-jarvis.sh` y `~/jarvis-chat --stats "hola"`.

---

## 5. Modo de operar

### 5.1 Arranque

```bash
~/start-jarvis.sh
```

Inicia el servicio, espera hasta 60 s a que `/api/tags` responda y muestra el
estado. Si falla, el mensaje indica si el problema es el sudoers o el servicio.

### 5.2 Consulta única

```bash
~/jarvis-chat "¿Qué podés hacer como asistente en el auto?"
```

Ideal para scripts y pruebas. La salida es solo el texto de respuesta.

### 5.3 Conversación

```bash
~/jarvis-chat --interactive
```

Mantiene hasta 4 mensajes de historial (configurable con `--history`). Se sale
con `salir`, `exit`, `quit`, `Ctrl-C` o `Ctrl-D`.

### 5.4 Diagnóstico

```bash
~/jarvis-chat --stats "Responde exactamente: hola"
```

Agrega a `stderr` una línea con `total`, `load`, `prompt eval` y `eval`. Es la
forma recomendada de comparar modelos y configuraciones.

### 5.5 Estado del sistema

```bash
~/status-jarvis.sh
```

Devuelve servicio, socket, modelos cargados, modelos instalados, CPU y RSS por
proceso, y espacio libre.

### 5.6 Parada

```bash
~/stop-jarvis.sh
```

Descarga los modelos y detiene el servicio. Es la forma correcta de liberar RAM
antes de ejecutar otra carga de trabajo en la placa.

---

## 6. Interpretación de resultados

### 6.1 Calidad esperada

| Modelo | Coherencia | Repetición | Indicado para |
|---|---|---|---|
| 0.5B | Media | Frecuente en charlas largas | Consultas cortas, uso interactivo |
| 1.5B | Buena | Ocasional | Respuestas elaboradas, paciencia |

El modelo **no sabe** qué hora es, no conoce el estado del vehículo y no puede
ejecutar acciones. Si responde que sí puede, es una alucinación.

### 6.2 Señales de degradación

| Señal | Interpretación |
|---|---|
| Respuestas cada vez más lentas | Otro proceso compite por CPU/RAM |
| Swap creciendo | Dos modelos cargados o contexto excesivo |
| Frases repetidas | Limitación del 0.5B; subir `repeat_penalty` |
| Respuesta vacía | `num_predict` agotado o timeout |
| Error HTTP 400 | El prompt supera `num_ctx` |

---

## 7. Mantenimiento

| Tarea | Comando |
|---|---|
| Ver modelos | `ollama list` |
| Ver modelos cargados | `ollama ps` |
| Descargar/actualizar modelo | `ollama pull qwen2.5:0.5b-instruct-q4_K_M` |
| Liberar RAM sin parar el servicio | `ollama stop qwen2.5:0.5b-instruct-q4_K_M` |
| Ver logs | `journalctl -u ollama -n 80 --no-pager` |
| Ver espacio | `df -h /home/arduino` |
| Reiniciar el servicio | `sudo systemctl restart ollama` |

**No borrar** `/home/arduino/.ollama/models` sin volver a descargar los modelos.
**No mover** Ollama a `/usr` ni a `/tmp`: la partición root está casi llena.

---

## 8. Precisión y honestidad

- Las cifras de latencia y memoria provienen de mediciones reales del
  2026-11-04, no de estimaciones.
- No se comparó Qwen2.5 contra otras familias en esta placa; la elección se basó
  en tamaño, disponibilidad del quant y soporte de español.
- La temperatura y el consumo eléctrico no se midieron con instrumentos
  externos; la temperatura proviene de los sensores del sistema.
- El proyecto no incluye capturas de pantalla ni videos: la interfaz es una
  terminal.

---

## 9. Solución de problemas

| Síntoma | Causa | Acción |
|---|---|---|
| `No se pudo conectar con Ollama` | Servicio detenido | `~/start-jarvis.sh` |
| `sudo: a password is required` | Falta sudoers | Instalar `config/sudoers-jarvis` |
| `ollama: command not found` | PATH | Usar `~/.local/bin/ollama` |
| `Error HTTP 400` | Contexto excedido | Subir `--num-ctx` o acortar el prompt |
| `model not found` | Modelo ausente | `ollama pull …` |
| Respuestas repetidas | 0.5B | Subir `--repeat-penalty` o usar 1.5B |
| Placa lenta | 1.5B + contexto grande | Volver al 0.5B |
| Disco lleno | Instalación en `/` | Mover a `/home/arduino` |
| Arranque agota 60 s | Bucle de reinicio | `journalctl -u ollama` |
| `Permission denied (publickey)` | Clave/usuario | Revisar `UNOQ_KEY`, `UNOQ_USER` |

Diagnóstico mínimo:

```bash
systemctl is-active ollama
ss -ltn | grep ':11434'
curl -fsS http://127.0.0.1:11434/api/tags
~/jarvis-chat --stats "Decime hola"
```

---

## 10. Glosario

| Término | Definición |
|---|---|
| **LLM** | Modelo de lenguaje de gran escala; predice tokens |
| **Token** | Unidad de texto (~4 caracteres en español) |
| **Prompt eval** | Tiempo de procesar la entrada antes de generar |
| **Generación** | Tiempo de producir tokens de salida |
| **Q4_K_M** | Cuantización de 4 bits tipo k-quant, variante media |
| **GGUF** | Formato de archivo de modelos para `llama.cpp` |
| **Loopback** | Interfaz local `127.0.0.1`; no accesible desde la red |
| **RSS** | Memoria residente de un proceso |
| **STT / TTS** | Speech-to-text / text-to-speech |
| **Contexto** | Ventana máxima de tokens que el modelo puede atender |

---

## 11. Referencias

- Ollama: <https://ollama.com> · <https://github.com/ollama/ollama>
- Qwen2.5: <https://github.com/QwenLM/Qwen2.5>
- Model cards: [0.5B](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) ·
  [1.5B](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- llama.cpp: <https://github.com/ggml-org/llama.cpp>
- GGUF: <https://github.com/ggml-org/ggml/blob/master/docs/gguf.md>
- Arduino UNO Q: <https://docs.arduino.cc/hardware/uno-q>
- Debian 13: <https://www.debian.org/releases/trixie/>
- systemd: <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html>

Lista comentada completa en [`REFERENCES.md`](REFERENCES.md).
