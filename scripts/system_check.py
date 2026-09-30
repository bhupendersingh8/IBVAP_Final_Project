"""
IBVAP — scripts/system_check.py
================================
Development Machine Audit Script

Detects and reports:
  - Operating system
  - CPU model and cores
  - RAM
  - Python version
  - pip version
  - Node.js version
  - npm version
  - Git version
  - Docker version
  - NVIDIA GPU (if present)
  - GPU VRAM
  - NVIDIA driver version
  - CUDA availability
  - Available disk space

Usage:
    python scripts/system_check.py

Rules:
  - Read-only: does NOT install or modify anything
  - Safe to run at any time
  - Outputs to console and saves to docs/environment-audit.md
"""

import subprocess
import sys
import platform
import os
import shutil
from pathlib import Path
from datetime import datetime

# ── Output Helpers ────────────────────────────────────────────────────────────

WIDTH = 70

def header(title: str) -> str:
    return f"\n{'=' * WIDTH}\n  {title}\n{'=' * WIDTH}"

def row(label: str, value: str, status: str = "") -> str:
    status_map = {"ok": "✅", "warn": "⚠️ ", "err": "❌", "info": "ℹ️ ", "": "  "}
    icon = status_map.get(status, "  ")
    return f"  {icon}  {label:<32} {value}"

def section(title: str) -> str:
    return f"\n  ── {title} ──"

# ── Command Runner ─────────────────────────────────────────────────────────────

def run(cmd: list[str], timeout: int = 10) -> str:
    """Run a command and return stdout, or empty string on error."""
    try:
        resolved = shutil.which(cmd[0]) if cmd else None
        exec_cmd = [resolved or cmd[0]] + cmd[1:]
        result = subprocess.run(
            exec_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=(platform.system() == "Windows" and resolved is not None and resolved.lower().endswith((".cmd", ".bat"))),
        )
        return (result.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return ""

# ── Individual Checks ─────────────────────────────────────────────────────────

def check_os() -> dict:
    system = platform.system()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    return {
        "system": system,
        "release": release,
        "version": version,
        "machine": machine,
        "full": f"{system} {release} ({machine})",
    }

def check_cpu() -> dict:
    cpu_name = platform.processor() or "Unknown"
    try:
        import psutil  # optional
        cores_phys = psutil.cpu_count(logical=False)
        cores_logic = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        freq_str = f"{freq.max:.0f} MHz" if freq else "Unknown"
    except ImportError:
        cores_phys = os.cpu_count() or "Unknown"
        cores_logic = cores_phys
        freq_str = "Unknown (install psutil for details)"
    return {
        "name": cpu_name,
        "physical_cores": cores_phys,
        "logical_cores": cores_logic,
        "freq": freq_str,
    }

def check_ram() -> dict:
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 1)
        available_gb = round(mem.available / (1024**3), 1)
        return {"total_gb": total_gb, "available_gb": available_gb}
    except ImportError:
        return {"total_gb": "Unknown (install psutil)", "available_gb": "Unknown"}

def check_disk() -> dict:
    try:
        total, used, free = shutil.disk_usage(Path.cwd().anchor)
        return {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
        }
    except Exception:
        return {"total_gb": "Unknown", "used_gb": "Unknown", "free_gb": "Unknown"}

def check_python() -> dict:
    ver = sys.version.split()[0]
    major, minor = sys.version_info.major, sys.version_info.minor
    ok = major == 3 and minor >= 11
    pip_out = run([sys.executable, "-m", "pip", "--version"])
    pip_ver = pip_out.split()[1] if pip_out else "Not found"
    return {"version": ver, "ok": ok, "pip": pip_ver, "path": sys.executable}

def check_tool(cmd: str, version_flag: str = "--version") -> str:
    out = run([cmd, version_flag])
    return out.split("\n")[0] if out else ""

def check_node() -> dict:
    ver = check_tool("node")
    npm_ver = check_tool("npm")
    return {"node": ver, "npm": npm_ver}

def check_git() -> dict:
    ver = check_tool("git")
    return {"version": ver}

def check_docker() -> dict:
    ver = check_tool("docker")
    compose_ver = run(["docker", "compose", "version"])
    return {"docker": ver, "compose": compose_ver}

def check_nvidia() -> dict:
    smi = run(["nvidia-smi"])
    if not smi:
        return {"available": False}
    lines = smi.split("\n")
    driver_ver = ""
    cuda_ver = ""
    gpu_name = ""
    vram_mb = ""
    for line in lines:
        if "Driver Version" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "Version" and i + 1 < len(parts):
                    driver_ver = parts[i + 1].strip("|").strip()
                if "CUDA" in parts[max(0, i-2):i] and p.replace(".", "").isdigit():
                    cuda_ver = p.strip("|").strip()
        if "MiB" in line and "Default" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                mem_part = parts[2].strip()
                nums = [x for x in mem_part.split() if "MiB" in x]
                if nums:
                    vram_mb = nums[-1].replace("MiB", "").strip()
        if "GeForce" in line or "RTX" in line or "GTX" in line or "Tesla" in line or "Quadro" in line:
            gpu_name_parts = [p.strip("|").strip() for p in line.split("|") if
                              any(k in p for k in ["GeForce", "RTX", "GTX", "Tesla", "Quadro"])]
            if gpu_name_parts:
                gpu_name = gpu_name_parts[0]
    return {
        "available": True,
        "driver": driver_ver,
        "cuda": cuda_ver,
        "gpu_name": gpu_name,
        "vram_mb": vram_mb,
        "raw": smi[:500],
    }

def check_cuda_python() -> dict:
    """Check if PyTorch can see CUDA."""
    try:
        import torch  # type: ignore
        cuda_available = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_available else 0
        device_name = torch.cuda.get_device_name(0) if cuda_available else ""
        cuda_version = torch.version.cuda or "N/A"
        torch_version = torch.__version__
        return {
            "torch_installed": True,
            "torch_version": torch_version,
            "cuda_available": cuda_available,
            "device_count": device_count,
            "device_name": device_name,
            "cuda_version": cuda_version,
        }
    except ImportError:
        return {"torch_installed": False}

# ── Main Report ───────────────────────────────────────────────────────────────

def build_report() -> tuple[str, dict]:
    lines = []
    data = {}

    lines.append(header("IBVAP — Development Machine Audit"))
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Script:    scripts/system_check.py")

    # ── Operating System ─────────────────────────────────────────────────────
    lines.append(section("Operating System"))
    os_info = check_os()
    data["os"] = os_info
    lines.append(row("OS", os_info["full"], "ok"))
    lines.append(row("Version", os_info["version"][:60], "info"))

    # ── Hardware ─────────────────────────────────────────────────────────────
    lines.append(section("Hardware"))
    cpu = check_cpu()
    data["cpu"] = cpu
    lines.append(row("CPU", cpu["name"][:50], "ok"))
    lines.append(row("Physical Cores", str(cpu["physical_cores"]), "ok"))
    lines.append(row("Logical Cores", str(cpu["logical_cores"]), "ok"))
    lines.append(row("CPU Frequency", cpu["freq"], "info"))

    ram = check_ram()
    data["ram"] = ram
    ram_status = "ok" if isinstance(ram["total_gb"], float) and ram["total_gb"] >= 8 else "warn"
    lines.append(row("RAM Total", f"{ram['total_gb']} GB", ram_status))
    lines.append(row("RAM Available", f"{ram['available_gb']} GB", "info"))

    disk = check_disk()
    data["disk"] = disk
    disk_status = "ok" if isinstance(disk["free_gb"], float) and disk["free_gb"] >= 10 else "warn"
    lines.append(row("Disk Free", f"{disk['free_gb']} GB", disk_status))
    lines.append(row("Disk Total", f"{disk['total_gb']} GB", "info"))

    # ── Python ───────────────────────────────────────────────────────────────
    lines.append(section("Python"))
    py = check_python()
    data["python"] = py
    py_status = "ok" if py["ok"] else "warn"
    lines.append(row("Python", py["version"], py_status))
    if not py["ok"]:
        lines.append(row("  ⚠️  Recommended: Python 3.11+", "", ""))
    lines.append(row("pip", py["pip"], "ok" if py["pip"] != "Not found" else "err"))
    lines.append(row("Path", py["path"][:50], "info"))

    # ── Node.js ──────────────────────────────────────────────────────────────
    lines.append(section("Node.js"))
    node = check_node()
    data["node"] = node
    node_status = "ok" if node["node"] else "err"
    lines.append(row("Node.js", node["node"] or "NOT FOUND", node_status))
    lines.append(row("npm", node["npm"] or "NOT FOUND", "ok" if node["npm"] else "err"))
    if not node["node"]:
        lines.append(row("  → Install from: https://nodejs.org", "", ""))

    # ── Git ───────────────────────────────────────────────────────────────────
    lines.append(section("Git"))
    git = check_git()
    data["git"] = git
    git_status = "ok" if git["version"] else "err"
    lines.append(row("Git", git["version"] or "NOT FOUND", git_status))

    # ── Docker ────────────────────────────────────────────────────────────────
    lines.append(section("Docker"))
    docker = check_docker()
    data["docker"] = docker
    docker_status = "ok" if docker["docker"] else "warn"
    lines.append(row("Docker", docker["docker"] or "NOT FOUND — Install Docker Desktop", docker_status))
    lines.append(row("Docker Compose", docker["compose"] or "NOT FOUND", "ok" if docker["compose"] else "warn"))
    if not docker["docker"]:
        lines.append(row("  → Install: https://www.docker.com/products/docker-desktop/", "", ""))

    # ── NVIDIA GPU ────────────────────────────────────────────────────────────
    lines.append(section("NVIDIA GPU (nvidia-smi)"))
    nvidia = check_nvidia()
    data["nvidia"] = nvidia
    if nvidia["available"]:
        lines.append(row("NVIDIA GPU", nvidia["gpu_name"], "ok"))
        lines.append(row("Driver Version", nvidia["driver"], "ok"))
        lines.append(row("CUDA Version (driver)", nvidia["cuda"], "ok"))
        if nvidia["vram_mb"]:
            lines.append(row("VRAM", f"{nvidia['vram_mb']} MiB", "ok"))
    else:
        lines.append(row("NVIDIA GPU", "NOT FOUND", "warn"))
        lines.append(row("  → CPU-only mode will be used", "", ""))
        lines.append(row("  → CUDA/TensorRT phases are optional", "", ""))

    # ── PyTorch / CUDA Python ─────────────────────────────────────────────────
    lines.append(section("PyTorch / CUDA (Python)"))
    cuda_py = check_cuda_python()
    data["cuda_python"] = cuda_py
    if cuda_py["torch_installed"]:
        lines.append(row("PyTorch", cuda_py["torch_version"], "ok"))
        cuda_status = "ok" if cuda_py["cuda_available"] else "warn"
        lines.append(row("CUDA Available", str(cuda_py["cuda_available"]), cuda_status))
        if cuda_py["cuda_available"]:
            lines.append(row("CUDA Version", cuda_py["cuda_version"], "ok"))
            lines.append(row("GPU Device", cuda_py["device_name"], "ok"))
        else:
            lines.append(row("  → Running in CPU mode", "", ""))
    else:
        lines.append(row("PyTorch", "Not installed yet", "info"))
        lines.append(row("  → Will be installed via requirements/ml.txt", "", ""))

    # ── Summary & Recommendations ─────────────────────────────────────────────
    lines.append(header("Summary & Recommendations"))

    missing = []
    warnings = []
    recommendations = []

    if not docker["docker"]:
        missing.append("Docker Desktop — https://www.docker.com/products/docker-desktop/")
    if not node["node"]:
        missing.append("Node.js LTS — https://nodejs.org")
    if not git["version"]:
        missing.append("Git — https://git-scm.com")
    if not py["ok"]:
        warnings.append(f"Python {py['version']} detected. Python 3.11+ recommended.")
    if not nvidia["available"]:
        warnings.append("No NVIDIA GPU detected. Using CPU-only mode (YOLOv8n nano).")
        recommendations.append("For faster inference: use a system with NVIDIA GPU + CUDA.")

    if missing:
        lines.append("\n  ❌ MISSING (must install):")
        for item in missing:
            lines.append(f"     • {item}")
    if warnings:
        lines.append("\n  ⚠️  WARNINGS:")
        for item in warnings:
            lines.append(f"     • {item}")
    if recommendations:
        lines.append("\n  💡 RECOMMENDATIONS:")
        for item in recommendations:
            lines.append(f"     • {item}")
    if not missing and not warnings:
        lines.append("\n  ✅ All core requirements satisfied. Ready to develop.")
    elif not missing:
        lines.append("\n  ✅ Core requirements satisfied. Review warnings above.")

    lines.append("\n" + "=" * WIDTH)
    return "\n".join(lines), data


def save_markdown(report_text: str) -> Path:
    """Save a markdown version to docs/environment-audit.md"""
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_path = docs_dir / "environment-audit.md"

    md_lines = [
        "# IBVAP — Development Environment Audit",
        f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        "**Script:** `scripts/system_check.py`\n",
        "```",
        report_text,
        "```",
        "\n---",
        "*This file is auto-generated. Re-run `python scripts/system_check.py` to update.*",
    ]
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report, _ = build_report()
    print(report)
    out = save_markdown(report)
    print(f"\n  📄 Report saved to: {out}")
