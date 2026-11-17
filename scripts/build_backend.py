"""用 uv 管理的 python-build-standalone 解释器构建 FastAPI sidecar。"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("OAT 的 Windows 自动化后端只能在 Windows 上打包")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("请通过 uv run --python 3.12 运行打包脚本")

    env = os.environ.copy()
    # only-managed 禁止回退到开发机或 CI 预装的系统 Python。
    env["UV_PYTHON_PREFERENCE"] = "only-managed"
    managed = subprocess.run(
        ["uv", "python", "find", "3.12", "--managed-python"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(f"[backend] python-build-standalone: {managed}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            "dist/backend",
            "--workpath",
            "build/backend",
            "packaging/oat_backend.spec",
        ],
        cwd=ROOT,
        check=True,
    )
    target_dir = ROOT / "frontend" / "src-tauri" / "binaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / "dist" / "backend" / "oat-backend.exe",
        target_dir / "oat-backend-x86_64-pc-windows-msvc.exe",
    )
    print("[backend] sidecar 已复制到 frontend/src-tauri/binaries")


if __name__ == "__main__":
    main()
