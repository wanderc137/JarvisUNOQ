# Referencias

Enlaces usados para construir, medir y documentar JarvisUNOQ. Todos son fuentes
primarias o documentación oficial; no hay agregadores ni contenido generado.

---

## Motor de inferencia

| Enlace | Utilidad |
|---|---|
| <https://ollama.com> | Sitio oficial y biblioteca de modelos; permite buscar tags y ver tamaños antes de descargar. |
| <https://github.com/ollama/ollama> | Código fuente y releases; de acá sale el tar ARM64 que se instala en la placa. |
| <https://github.com/ollama/ollama/releases/tag/v0.40.14> | Release exacta usada: binario `ollama-linux-arm64.tar.zst`. |
| <https://github.com/ollama/ollama/blob/main/docs/api.md> | Referencia de `/api/chat`, `/api/tags`, `/api/ps` y de los campos de métricas. |

## Modelos

| Enlace | Utilidad |
|---|---|
| <https://github.com/QwenLM/Qwen2.5> | Familia Qwen2.5, tamaños, contexto y reporte técnico. |
| <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct> | Model card del modelo rápido: licencia, idiomas y límites. |
| <https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct> | Model card del modelo de calidad usado en la placa. |
| <https://ollama.com/library/qwen2.5> | Tags disponibles; de acá salen los nombres `…-instruct-q4_K_M`. |
| <https://arxiv.org/abs/2412.15115> | Reporte técnico de Qwen2.5: datos de entrenamiento y evaluación. |

## Inferencia en CPU y formato

| Enlace | Utilidad |
|---|---|
| <https://github.com/ggml-org/llama.cpp> | Motor que Ollama usa por debajo; explica por qué la CPU es viable. |
| <https://github.com/ggml-org/ggml/blob/master/docs/gguf.md> | Especificación del formato GGUF que empaqueta los pesos cuantizados. |
| <https://huggingface.co/docs/hub/gguf> | Guía práctica de cuantizaciones GGUF y su relación tamaño/calidad. |

## Hardware y sistema operativo

| Enlace | Utilidad |
|---|---|
| <https://docs.arduino.cc/hardware/uno-q> | Documentación oficial de la placa: especificaciones y guías de inicio. |
| <https://www.debian.org/releases/trixie/> | Página de Debian 13 «trixie», el SO que corre en la placa. |
| <https://www.debian.org/releases/trixie/releasenotes> | Notas de release; útil para diferencias de paquetes y versiones. |
| <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html> | Sintaxis de `[Service]`, `Restart`, `TimeoutStopSec` usados en `ollama.service`. |
| <https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html> | Variables de entorno y directivas de ejecución para unidades. |

## Seguridad y sistema

| Enlace | Utilidad |
|---|---|
| <https://man7.org/linux/man-pages/man5/sudoers.5.html> | Sintaxis de `sudoers`, incluida la regla NOPASSWD acotada del proyecto. |
| <https://man7.org/linux/man-pages/man8/ss.8.html> | Uso de `ss -ltn` para verificar que 11434 escucha solo en loopback. |
| <https://www.kernel.org/doc/html/latest/filesystems/proc.html> | Documentación de `/proc/stat`, `/proc/meminfo` y `/proc/<pid>/statm`, que usa `measure-jarvis.py`. |

## Fase 2 (voz), candidatos no implementados

| Enlace | Utilidad |
|---|---|
| <https://github.com/ggml-org/whisper.cpp> | STT en CPU; modelos `tiny`/`base` compatibles con el presupuesto de RAM. |
| <https://github.com/rhasspy/piper> | TTS liviano en CPU, con voces en español. |
| <https://alphacephei.com/vosk/> | Alternativa de STT con modelos pequeños y bajo consumo. |

---

## Cómo leer estas referencias

- Para **replicar la instalación**, alcanza con la release de Ollama y la
  documentación de la placa.
- Para **entender el rendimiento**, la clave está en la documentación de
  `llama.cpp` y en el formato GGUF: explican por qué un modelo de 0,5B corre a
  ~10 tok/s en cuatro núcleos.
- Para **extender el proyecto**, la referencia de la API de Ollama y la
  documentación de `systemd` cubren el 90 % de los cambios previsibles.

Las mediciones propias están en [`PERFORMANCE.md`](PERFORMANCE.md) y las
decisiones en [`BITACORA.md`](BITACORA.md).
