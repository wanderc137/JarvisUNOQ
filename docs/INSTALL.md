# Instalación en la Arduino UNO Q

Procedimiento reproducido en la placa el **2026-11-04**. La UNO Q tiene dos
particiones importantes:

- `/` (root): 9,8 GB, casi llena. No instalar aquí modelos ni runtimes grandes.
- `/home/arduino`: 18 GB, ~14 GB libres. Acá viven Ollama y los modelos.

Acceso:

```bash
ssh -p 22 -i ~/.ssh/unoq_key arduino@192.168.1.75
```

> **Nota:** OpenClaw se instaló y se probó, pero se eliminó por consumo de RAM y
> latencia. Esta guía instala solo Ollama y el chat de texto. El historial está en
> [`BITACORA.md`](BITACORA.md).

## 1. Ollama sin CUDA

El archivo ARM64 oficial pesa ~1,5 GB porque incluye CUDA 12 y 13. Esta placa no
tiene GPU NVIDIA, así que se extrae solo la parte necesaria.

En el host (o en `/home/arduino/tmp` de la placa):

```bash
curl -fL \
  https://github.com/ollama/ollama/releases/download/v0.40.14/ollama-linux-arm64.tar.zst \
  -o ollama-linux-arm64.tar.zst
```

Verificar SHA256:

```text
39bb333b7b4c0bafcdd7fad35eab1ae9aaf4518ea0f2c731de4376e3a29c94d0
```

Extraer sin CUDA:

```bash
mkdir -p /tmp/ollama-extract
tar --zstd -xf ollama-linux-arm64.tar.zst -C /tmp/ollama-extract \
  --exclude='lib/ollama/cuda_v12' --exclude='lib/ollama/cuda_v13'
```

Copiar a la placa:

```bash
scp -P 22 -i ~/.ssh/unoq_key -r /tmp/ollama-extract/bin /tmp/ollama-extract/lib \
  arduino@192.168.1.75:/home/arduino/ollama/
```

En la placa:

```bash
mkdir -p /home/arduino/.ollama/models /home/arduino/tmp
ln -sf /home/arduino/ollama/bin/ollama /home/arduino/.local/bin/ollama
/home/arduino/ollama/bin/ollama --version
```

## 2. Servicio systemd

```bash
sudo cp config/ollama.service /etc/systemd/system/ollama.service
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
```

`ollama.service` fija `OLLAMA_CONTEXT_LENGTH=4096` para no reservar 32k de
contexto por defecto, y `OLLAMA_NUM_THREADS=4`.

Verificar:

```bash
curl -fsS http://127.0.0.1:11434/api/tags
```

## 3. Modelos

```bash
/home/arduino/.local/bin/ollama pull qwen2.5:0.5b-instruct-q4_K_M
/home/arduino/.local/bin/ollama pull qwen2.5:1.5b-instruct-q4_K_M
/home/arduino/.local/bin/ollama list
```

Tamaños: 397 MB y 986 MB. El 0.5B es el modelo rápido; el 1.5B es el de mayor
calidad.

## 4. Sudoers acotado

Los scripts de arranque/parada necesitan iniciar y detener solo `ollama`, sin
contraseña:

```bash
sudo cp config/sudoers-jarvis /etc/sudoers.d/90-jarvis-control
sudo chmod 0440 /etc/sudoers.d/90-jarvis-control
sudo visudo -cf /etc/sudoers.d/90-jarvis-control
```

No se concede sudo general ni se habilita root por SSH.

## 5. Copiar el proyecto y probar

Desde el host:

```bash
./scripts/deploy-unoq.sh
```

En la placa:

```bash
cd ~/JarvisUNOQ
./scripts/start-jarvis.sh
./scripts/jarvis-chat.py "Hola Jarvis, preséntate en una frase"
./scripts/status-jarvis.sh
./scripts/stop-jarvis.sh
```

`start-jarvis.sh` solo inicia Ollama y espera a que `/api/tags` responda. No hay
gateway ni esperas de minutos.

## 6. Verificación mínima

```bash
systemctl is-active ollama
ss -ltn | grep ':11434'
curl -fsS http://127.0.0.1:11434/api/tags
~/jarvis-chat --stats "Decime hola"
```

## Problemas frecuentes

| Problema | Causa | Solución |
|---|---|---|
| `sudo: a password is required` | Falta la regla de sudoers | Instalar `config/sudoers-jarvis` |
| `ollama: command not found` | PATH no incluye `~/.local/bin` | Usar ruta completa o agregar al PATH |
| `No se pudo conectar con Ollama` | Servicio detenido | `~/start-jarvis.sh` |
| Respuestas repetidas | Limitación del 0.5B | Probar el 1.5B |
| Memoria llena | 1.5B + contexto grande | Usar 0.5B y contexto 4096 |
| Disco root lleno | Se instaló en `/usr` o `/tmp` | Mover todo a `/home/arduino` |

## Referencias

- Ollama releases: https://github.com/ollama/ollama/releases
- Qwen2.5: https://github.com/QwenLM/Qwen2.5
- Arduino UNO Q: https://docs.arduino.cc/hardware/uno-q
- Video de referencia (OpenClaw, descartado): https://www.youtube.com/watch?v=aA1oWSPh41Q
