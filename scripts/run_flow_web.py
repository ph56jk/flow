#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VENV_DIR = ROOT / ".venv"
INSTALL_STAMP = VENV_DIR / ".flow_install_stamp"
PID_FILE = ROOT / ".flow-web.pid"


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def venv_python() -> Path:
    if is_windows():
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run_checked(label: str, command: list[str]) -> None:
    print(f"[flow] {label}: {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_python_version() -> None:
    if sys.version_info >= (3, 11):
        return
    version = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(f"Can Python 3.11+. Python hien tai la {version}.")


def ensure_venv() -> Path:
    python = venv_python()
    if python.exists():
        return python

    ensure_python_version()
    run_checked("create venv", [sys.executable, "-m", "venv", str(VENV_DIR)])
    if not python.exists():
        raise SystemExit("Khong tao duoc .venv cho Flow v2.")
    return python


def needs_dependency_install() -> bool:
    if not INSTALL_STAMP.exists():
        return True
    try:
        return PYPROJECT.stat().st_mtime > INSTALL_STAMP.stat().st_mtime
    except OSError:
        return True


def ensure_dependencies(python: Path) -> None:
    if not needs_dependency_install():
        return
    run_checked("pip upgrade", [str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run_checked("pip install", [str(python), "-m", "pip", "install", "-e", "."])
    INSTALL_STAMP.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), encoding="utf-8")


def windows_drive_candidates() -> list[Path]:
    candidates: list[Path] = []
    for letter in ("D", "C"):
        drive = Path(f"{letter}:\\")
        if drive.exists():
            candidates.append(drive)
    root_drive = Path(ROOT.anchor)
    if root_drive.exists() and root_drive not in candidates:
        candidates.append(root_drive)
    return candidates


def preferred_windows_browser_root() -> Path:
    candidates = windows_drive_candidates()
    if not candidates:
        anchor = Path.home().anchor or ROOT.anchor
        return (Path(anchor) / "pw-flow") if anchor else (ROOT / "pw-flow")

    def free_bytes(path: Path) -> int:
        try:
            return shutil.disk_usage(path).free
        except OSError:
            return 0

    best = max(candidates, key=free_bytes)
    return best / "pw-flow"


def browser_root(cli_value: str) -> Path:
    configured = cli_value.strip() or os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if is_windows():
        return preferred_windows_browser_root()
    return (ROOT / ".pw-browsers").resolve()


def chromium_installed(path: Path) -> bool:
    if not path.exists():
        return False
    names = {"chrome", "Chromium", "chrome.exe", "Google Chrome for Testing", "chrome-headless-shell"}
    return any(candidate.is_file() and candidate.name in names for candidate in path.rglob("*"))


def ensure_chromium(python: Path, path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(path)
    if chromium_installed(path):
        return
    run_checked("playwright install chromium", [str(python), "-m", "playwright", "install", "chromium"])


def open_later(url: str) -> None:
    def _go() -> None:
        time.sleep(2)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_go, daemon=True).start()


def write_server_pid(pid: int) -> None:
    try:
        PID_FILE.write_text(f"{pid}\n", encoding="utf-8")
    except OSError:
        pass


def clear_server_pid(pid: int) -> None:
    try:
        if PID_FILE.read_text(encoding="utf-8").strip() == str(pid):
            PID_FILE.unlink()
    except OSError:
        pass


def run_server(command: list[str]) -> int:
    process = subprocess.Popen(command, cwd=ROOT)
    write_server_pid(process.pid)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 130
    finally:
        clear_server_pid(process.pid)


def windows_session_warning(prepare_only: bool) -> None:
    if prepare_only or not is_windows():
        return
    try:
        current_session = int(os.environ.get("SESSIONNAME", "") == "Services")
    except Exception:
        current_session = 0
    if current_session:
        print(
            "[flow] Canh bao: Flow v2 co the dang chay trong session nen cua Windows. "
            "Hay mo truc tiep tren desktop neu can dang nhap Google Flow."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform launcher for Flow v2.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1506)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--no-open-browser", action="store_true")
    parser.add_argument("--browser-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.chdir(ROOT)
    windows_session_warning(args.prepare_only)

    python = ensure_venv()
    ensure_dependencies(python)
    ensure_chromium(python, browser_root(args.browser_path))

    if args.prepare_only:
        print("[flow] Da setup xong. Chay app bang: python3 scripts/run_flow_web.py")
        return 0

    if not args.no_open_browser:
        open_later(f"http://{args.host}:{args.port}")

    command = [
        str(python),
        "-m",
        "uvicorn",
        "flow_web.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        command.append("--reload")
    return run_server(command)


if __name__ == "__main__":
    raise SystemExit(main())
