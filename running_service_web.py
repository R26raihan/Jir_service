#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class ManagedProcess:
    def __init__(self, name: str, cmd: list[str], cwd: Path):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        env = os.environ.copy()
        # Ensure local packages are discoverable
        env["PYTHONUNBUFFERED"] = "1"
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def stream_output(self) -> None:
        assert self.proc is not None
        prefix = f"[{self.name}] "
        for line in self.proc.stdout:  # type: ignore[arg-type]
            sys.stdout.write(prefix + line)
        sys.stdout.flush()

    def terminate(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            except Exception:
                pass


def main() -> int:
    crowd_dir = BASE_DIR / "crowd_monitoring_service"
    banjir_dir = BASE_DIR / "banjir_service"
    report_dir = BASE_DIR / "report_service"
    mobility_dir = BASE_DIR / "user_mobility_service"
    llm_dir = BASE_DIR / "crow_LLM_service"

    services: list[ManagedProcess] = [
        ManagedProcess(
            name="crowd",
            cmd=["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"],
            cwd=crowd_dir,
        ),
        ManagedProcess(
            name="banjir",
            cmd=["python3", "-m", "uvicorn", "Databanjir:app", "--host", "0.0.0.0", "--port", "8002"],
            cwd=banjir_dir,
        ),
        ManagedProcess(
            name="report",
            cmd=["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"],
            cwd=report_dir,
        ),
        ManagedProcess(
            name="mobility",
            cmd=["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"],
            cwd=mobility_dir,
        ),
        ManagedProcess(
            name="llm",
            cmd=["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005"],
            cwd=llm_dir,
        ),
    ]

    print("Starting services:")
    print("- crowd_monitoring_service -> http://localhost:8001")
    print("- banjir_service            -> http://localhost:8002")
    print("- report_service            -> http://localhost:8003")
    print("- user_mobility_service     -> http://localhost:8004")
    print("- crowd_llm_service         -> http://localhost:8005")
    print("Press Ctrl+C to stop all services.\n")

    for svc in services:
        svc.start()

    threads: list[threading.Thread] = []
    for svc in services:
        t = threading.Thread(target=svc.stream_output, daemon=True)
        t.start()
        threads.append(t)

    def handle_sigint(signum, frame):  # noqa: ARG001
        print("\nShutting down services...")
        for svc in services:
            svc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    try:
        # Keep main thread alive while children run
        while True:
            time.sleep(5)  # Check every 5 seconds instead of 1
            # Check if any service exited and restart it
            for svc in services:
                if svc.proc and svc.proc.poll() is not None:
                    print(f"Service '{svc.name}' exited with code {svc.proc.returncode}. Waiting 10 seconds before restart...")
                    time.sleep(10)  # Wait 10 seconds before restart
                    print(f"Restarting service '{svc.name}'...")
                    svc.start()
                    # Start output streaming thread for restarted service
                    t = threading.Thread(target=svc.stream_output, daemon=True)
                    t.start()
    finally:
        for svc in services:
            svc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())


