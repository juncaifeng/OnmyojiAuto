"""源码与打包环境通用的资源路径。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def oat_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    return oat_dir().parent


def data_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "OnmyojiAuto"
    else:
        base = project_root()
    base.mkdir(parents=True, exist_ok=True)
    return base
