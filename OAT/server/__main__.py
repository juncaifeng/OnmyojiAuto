"""直接由解释器或 PyInstaller sidecar 启动，不经 shell。"""
from __future__ import annotations

import argparse
import os

import uvicorn

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="OAT local FastAPI backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=os.environ.get("OAT_API_TOKEN", ""))
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("本地后端只允许监听回环地址")
    if not args.token:
        parser.error("必须通过 --token 或 OAT_API_TOKEN 提供本地 API 令牌")

    uvicorn.run(
        create_app(api_token=args.token),
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
