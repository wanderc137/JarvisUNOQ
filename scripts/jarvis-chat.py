#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = os.environ.get("JARVIS_MODEL", "qwen2.5:0.5b-instruct-q4_K_M")
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
DEFAULT_SYSTEM = (
    "Sos Jarvis, un asistente conversacional local para el auto. Respondés en "
    "español rioplatense, breve, claro y útil. En este modo de chat solo podés "
    "conversar: NO tenés acceso a archivos, disco, cámara, internet, sensores "
    "ni comandos. Si te preguntan por esas capacidades, decí que no las tenés. "
    "No inventes datos ni acciones. Tampoco sabés cuánto tardás en responder: "
    "no inventes tiempos ni métricas. Respondé únicamente a la última pregunta "
    "y no repitas respuestas anteriores. Usá 1 a 3 oraciones y menos de 60 "
    "palabras, salvo que pidan más detalle."
)


def build_url(host):
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return "http://" + host.rstrip("/")


def request_chat(
    host, model, messages, max_tokens, temperature, repeat_penalty, num_ctx, timeout
):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "15m",
        "options": {
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
            "temperature": temperature,
            "repeat_penalty": repeat_penalty,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        build_url(host) + "/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def format_stats(data):
    def seconds(value):
        return value / 1_000_000_000 if value else 0.0

    return (
        f"total={seconds(data.get('total_duration')):.2f}s "
        f"load={seconds(data.get('load_duration')):.2f}s "
        f"prompt={data.get('prompt_eval_count', '?')} tok/"
        f"{seconds(data.get('prompt_eval_duration')):.2f}s "
        f"eval={data.get('eval_count', '?')} tok/"
        f"{seconds(data.get('eval_duration')):.2f}s"
    )


def ask(args, messages):
    started = time.time()
    try:
        data = request_chat(
            args.host,
            args.model,
            messages,
            args.max_tokens,
            args.temperature,
            args.repeat_penalty,
            args.num_ctx,
            args.timeout,
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Error HTTP {exc.code}: {body}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(
            "No se pudo conectar con Ollama. "
            "Ejecutá scripts/start-jarvis.sh o revisá el servicio ollama.",
            file=sys.stderr,
        )
        print(f"Detalle: {exc}", file=sys.stderr)
        return None
    except TimeoutError:
        print("Ollama no respondió a tiempo.", file=sys.stderr)
        return None
    text = data.get("message", {}).get("content", "").strip()
    if args.stats:
        elapsed = time.time() - started
        print(f"[{elapsed:.2f}s] {format_stats(data)}", file=sys.stderr)
    return text


def trim_history(history, max_messages):
    if len(history) <= max_messages + 1:
        return history
    return [history[0]] + history[-(max_messages):]


def run_interactive(args):
    history = [{"role": "system", "content": args.system}]
    print(f"Jarvis local · modelo {args.model}")
    print("Escribí 'salir' para terminar.")
    while True:
        try:
            prompt = input("Vos > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            continue
        if prompt.lower() in {"salir", "exit", "quit"}:
            break
        history.append({"role": "user", "content": prompt})
        answer = ask(args, trim_history(history, args.history))
        if answer is None:
            history.pop()
            continue
        print(f"Jarvis > {answer}")
        history.append({"role": "assistant", "content": answer})


def main():
    parser = argparse.ArgumentParser(description="Chat de texto local para JarvisUNOQ.")
    parser.add_argument("prompt", nargs="*", help="Consulta de una sola vez.")
    parser.add_argument("-i", "--interactive", action="store_true", help="Modo conversación.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama.")
    parser.add_argument("--system", default=DEFAULT_SYSTEM, help="System prompt.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host de Ollama.")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--repeat-penalty", type=float, default=1.2)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--history", type=int, default=4, help="Mensajes de historial.")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--stats", action="store_true", help="Muestra tiempos de Ollama.")
    args = parser.parse_args()

    if args.interactive:
        run_interactive(args)
        return

    if not args.prompt:
        parser.error("Indicá una consulta o usá --interactive.")
    messages = [
        {"role": "system", "content": args.system},
        {"role": "user", "content": " ".join(args.prompt)},
    ]
    answer = ask(args, messages)
    if answer is None:
        sys.exit(1)
    print(answer)


if __name__ == "__main__":
    main()
