#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time

CLK_TCK = os.sysconf("SC_CLK_TCK")
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
GROUPS = {
    "ollama": ["/home/arduino/ollama/bin/ollama serve", "ollama serve"],
    "llama-server": ["llama-server"],
}


def pids_for(pattern):
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        capture_output=True,
        text=True,
        check=False,
    )
    return {int(line) for line in result.stdout.splitlines() if line.strip().isdigit()}


def group_pids():
    groups = {}
    for label, patterns in GROUPS.items():
        found = set()
        for pattern in patterns:
            found |= pids_for(pattern)
        groups[label] = sorted(found)
    return groups


def read_proc(pid):
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as handle:
            stat = handle.read()
        with open(f"/proc/{pid}/statm", "r", encoding="utf-8") as handle:
            statm = handle.read().split()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    fields = stat.rsplit(") ", 1)[-1].split()
    ticks = int(fields[11]) + int(fields[12])
    rss = int(statm[1]) * PAGE_SIZE
    name = stat.split("(", 1)[-1].split(")", 1)[0]
    return {"name": name, "ticks": ticks, "rss": rss}


def read_meminfo():
    values = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            key, rest = line.split(":", 1)
            values[key] = int(rest.strip().split()[0]) * 1024
    return values


def read_cpu_total():
    with open("/proc/stat", "r", encoding="utf-8") as handle:
        fields = handle.readline().split()[1:]
    values = [int(value) for value in fields]
    idle = values[3] + values[4]
    return sum(values), idle


def human_mib(value):
    return f"{value / (1024 * 1024):.1f}"


def main():
    parser = argparse.ArgumentParser(description="Mide CPU y RAM de JarvisUNOQ.")
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    groups = group_pids()
    before = {}
    for pids in groups.values():
        for pid in pids:
            data = read_proc(pid)
            if data:
                before[pid] = data
    cpu_before, idle_before = read_cpu_total()
    time.sleep(args.interval)
    cpu_after, idle_after = read_cpu_total()

    total_delta = cpu_after - cpu_before
    idle_delta = idle_after - idle_before
    system_cpu = 0.0
    if total_delta > 0:
        system_cpu = 100.0 * (total_delta - idle_delta) / total_delta

    rows = []
    for label, pids in groups.items():
        cpu = 0.0
        rss = 0
        names = []
        for pid in pids:
            current = read_proc(pid)
            if not current:
                continue
            previous = before.get(pid)
            if previous:
                delta = max(0, current["ticks"] - previous["ticks"])
                cpu += 100.0 * delta / CLK_TCK / args.interval
            rss += current["rss"]
            names.append(current["name"])
        rows.append(
            {
                "service": label,
                "pids": pids,
                "processes": names,
                "cpu_percent": round(cpu, 1),
                "rss_mib": round(rss / (1024 * 1024), 1),
            }
        )

    mem = read_meminfo()
    result = {
        "interval_seconds": args.interval,
        "system_cpu_percent": round(system_cpu, 1),
        "mem_total_mib": round(mem.get("MemTotal", 0) / (1024 * 1024), 1),
        "mem_available_mib": round(mem.get("MemAvailable", 0) / (1024 * 1024), 1),
        "swap_used_mib": round(
            (mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)) / (1024 * 1024), 1
        ),
        "services": rows,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"Muestra: {args.interval:.1f}s · CPU sistema: {system_cpu:.1f}%")
    print(f"{'Servicio':<14} {'PID(s)':<18} {'CPU%':>7} {'RSS MiB':>9}  Proceso")
    for row in rows:
        pid_text = ",".join(str(pid) for pid in row["pids"]) or "-"
        process_text = ",".join(row["processes"]) or "-"
        print(
            f"{row['service']:<14} {pid_text:<18} {row['cpu_percent']:>7.1f} "
            f"{row['rss_mib']:>9.1f}  {process_text}"
        )
    total_rss = sum(row["rss_mib"] for row in rows)
    print(f"{'TOTAL':<14} {'':<18} {'':>7} {total_rss:>9.1f}")
    print(
        f"RAM: {result['mem_available_mib']:.1f} MiB disponibles de "
        f"{result['mem_total_mib']:.1f} MiB · swap usado {result['swap_used_mib']:.1f} MiB"
    )


if __name__ == "__main__":
    main()
