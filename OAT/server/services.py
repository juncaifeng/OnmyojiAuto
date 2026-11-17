"""FastAPI 与原自动化核心之间的应用服务。"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from OAT.server.events import bus
from OAT.server.models import TaskStartRequest
from OAT.server.paths import oat_dir, project_root
from OAT.tools import settings
from OAT.utils import pause_state
from OAT.utils.logging import logger


class TaskManager:
    """单任务生命周期管理；不创建 shell，也不接受命令行字符串。"""

    def __init__(self, synchronizer: Any) -> None:
        self.synchronizer = synchronizer
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._request: TaskStartRequest | None = None
        self._status = "idle"
        self._error: str | None = None
        self._done = 0
        self._total = 0
        logger.record_updated.connect(self._on_log)
        logger.progress_updated.connect(self._on_progress)

    def _on_log(self, record: dict[str, Any]) -> None:
        bus.publish("log", record)

    def _on_progress(self, done: int, total: int) -> None:
        with self._lock:
            self._done, self._total = done, total
        bus.publish("progress", {"done": done, "total": total})

    def _set_status(self, status: str, error: str | None = None) -> None:
        with self._lock:
            self._status = status
            self._error = error
        bus.publish("task", self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            request = self._request.model_dump() if self._request else None
            return {
                "status": self._status,
                "error": self._error,
                "done": self._done,
                "total": self._total,
                "paused": pause_state.is_paused(),
                "request": request,
            }

    def start(self, request: TaskStartRequest) -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("已有挑战任务正在运行")
            if request.sync_mode and not self.synchronizer.sync_enabled:
                raise RuntimeError("请先启动窗口同步，再启用同步挑战")
            self._request = request
            self._done = 0
            self._total = request.times
            self._error = None
            self._thread = threading.Thread(
                target=self._run,
                args=(request,),
                name="oat-challenge",
                daemon=True,
            )
            self._thread.start()
        self._set_status("running")
        return self.snapshot()

    def _run(self, request: TaskStartRequest) -> None:
        pause_state.begin_run()
        self._set_status("running")
        try:
            from OAT.source import MODE_MAPPING, mode_choice

            folder_info = MODE_MAPPING.get(request.mode)
            if not folder_info:
                raise ValueError(f"不支持的模式：{request.mode}")
            if isinstance(folder_info, dict):
                folder_name = folder_info.get(request.sub_mode, folder_info["default"])
            else:
                folder_name = folder_info
            if not folder_name:
                raise ValueError("请选择有效的子模式")
            script_dir = oat_dir() / "source" / folder_name
            with (script_dir / "config.json").open("r", encoding="utf-8") as file:
                config = json.load(file)
            logger.info(f"开始挑战：{request.mode}，共 {request.times} 次")
            mode_choice(
                request.mode,
                request.sub_mode,
                request.times,
                config=config,
                window_title=request.client.title,
                window_hwnd=request.client.hwnd,
                hidden_window=request.hidden_window,
                sync_mode=request.sync_mode,
                synchronizer=self.synchronizer,
                sync_mode_value=settings.settings_data.get("sync_mode", "exactly_sync"),
                explore_per_round=request.explore_per_round,
                explore_only=request.explore_only,
            )
            if pause_state.is_stopped():
                self._set_status("stopped")
            else:
                self._set_status("completed")
        except Exception as exc:
            logger.error(f"挑战任务失败：{exc}")
            self._set_status("failed", str(exc))

    def pause(self) -> dict[str, Any]:
        pause_state.pause()
        self._set_status("paused")
        return self.snapshot()

    def resume(self) -> dict[str, Any]:
        pause_state.resume()
        if self._thread and self._thread.is_alive():
            self._set_status("running")
        return self.snapshot()

    def stop(self) -> dict[str, Any]:
        pause_state.request_stop()
        if self._thread and self._thread.is_alive():
            self._set_status("stopping")
        else:
            self._set_status("stopped")
        return self.snapshot()

    def shutdown(self) -> None:
        pause_state.request_stop()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3)


class SyncManager:
    def __init__(self) -> None:
        from OAT.tools.WindowSynchronizer import WindowSynchronizer

        self.synchronizer = WindowSynchronizer(
            sync_mode=settings.settings_data.get("sync_mode", "exactly_sync")
        )
        self._clients: dict[int, str] = {}

    def update_clients(self, clients: list[dict[str, Any]]) -> None:
        self._clients = {int(c["hwnd"]): c["title"] for c in clients if c.get("hwnd")}

    def start(self, main_hwnd: int, sub_hwnds: list[int]) -> dict[str, Any]:
        import win32gui

        if main_hwnd in sub_hwnds or len(sub_hwnds) != len(set(sub_hwnds)):
            raise ValueError("主副窗口不能重复")
        for hwnd in [main_hwnd, *sub_hwnds]:
            if not win32gui.IsWindow(hwnd):
                raise ValueError(f"窗口不存在：{hwnd}")
        self.synchronizer.set_sync_mode(settings.settings_data.get("sync_mode", "exactly_sync"))
        self.synchronizer.set_main_and_sub_windows(
            self._clients.get(main_hwnd, str(main_hwnd)),
            [self._clients.get(hwnd, str(hwnd)) for hwnd in sub_hwnds],
            main_hwnd=main_hwnd,
            sub_hwnds=sub_hwnds,
        )
        self.synchronizer.set_true_enable()
        self.synchronizer.sync_controller()
        return self.snapshot()

    def stop(self) -> dict[str, Any]:
        self.synchronizer.stop_all_sync()
        return self.snapshot()

    def arrange(self) -> dict[str, Any]:
        if not self.synchronizer.main_window or not self.synchronizer.sub_windows:
            raise RuntimeError("请先启动同步并设置主副窗口")
        self.synchronizer.arrange_windows(
            self.synchronizer.main_window[0],
            [hwnd for hwnd, _ in self.synchronizer.sub_windows],
        )
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        main = self.synchronizer.main_window
        return {
            "enabled": bool(self.synchronizer.sync_enabled),
            "main_hwnd": main[0] if main else None,
            "sub_hwnds": [hwnd for hwnd, _ in self.synchronizer.get_sub_windows()],
        }


class MultiInstanceService:
    def __init__(self) -> None:
        from OAT.tools.MultiInstanceManager import MultiInstanceManager

        self.manager = MultiInstanceManager(project_root() / "yyx")

    def start(self, exe_path: str, count: int, interval: float) -> list[dict[str, Any]]:
        path = Path(exe_path)
        if not path.is_file() or path.suffix.lower() != ".exe":
            raise ValueError("请选择有效的游戏 exe 文件")

        def launched(instance: Any) -> None:
            bus.publish("multi", self.snapshot())

        # 使用后台线程，避免启动间隔阻塞 ASGI 事件循环。
        threading.Thread(
            target=self.manager.launch_instances,
            args=(str(path), count, interval),
            kwargs={"on_launched": launched},
            name="oat-multi-launch",
            daemon=True,
        ).start()
        return self.snapshot()

    def snapshot(self) -> list[dict[str, Any]]:
        self.manager.refresh_all_status()
        return [
            {
                "id": instance_id,
                "pid": item.pid,
                "status": item.status,
                "launched_at": item.launched_at,
            }
            for instance_id, item in self.manager.get_all_instances().items()
        ]

    def close(self, instance_id: int) -> bool:
        result = self.manager.close_instance(instance_id)
        bus.publish("multi", self.snapshot())
        return result
