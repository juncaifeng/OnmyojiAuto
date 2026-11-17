"""类型化设置读写。"""
from __future__ import annotations

from threading import Lock
from typing import Any

from OAT.server.models import SettingsPatch
from OAT.tools import settings

_lock = Lock()


def get_settings() -> dict[str, Any]:
    return dict(settings.settings_data)


def update_settings(patch: SettingsPatch) -> dict[str, Any]:
    values = patch.model_dump(exclude_none=True)
    with _lock:
        for key, value in values.items():
            if not settings.update_settings(key, value):
                raise RuntimeError(f"保存设置失败：{key}")
    return get_settings()
