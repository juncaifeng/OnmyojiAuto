"""本机客户端发现与窗口预览。"""
from __future__ import annotations

from typing import Any

from OAT.tools import settings
from OAT.tools.ClientDiscovery import build_client_items, discover_clients


def list_clients() -> list[dict[str, Any]]:
    clients = discover_clients(settings.resolve_mumu_folder())
    items = build_client_items(clients)
    result = []
    for label, client in items:
        result.append({
            "id": str(client.hwnd) if client and client.hwnd else f"title:{label}",
            "label": label,
            "title": client.title if client and client.title else label,
            "hwnd": int(client.hwnd) if client and client.hwnd else None,
            "kind": client.kind if client else "pc",
            "pid": client.pid if client else None,
        })
    return result


def window_preview(hwnd: int) -> bytes:
    import cv2

    from OAT.tools.GetDC import WindowCapture

    image = None
    try:
        from OAT.tools.emulator.backend import create_backend
        from OAT.tools.emulator.mumu_handle import build_handle

        build_handle(hwnd, wait_tries=1)
        backend = create_backend(
            "mumu12", handle_spec=hwnd, mumu_folder=settings.resolve_mumu_folder()
        )
        try:
            image = backend.screenshot()
        finally:
            backend.close()
    except Exception:
        image = None
    if image is None:
        image = WindowCapture(hwnd=hwnd).capture_window()
    if image is None:
        raise RuntimeError("无法捕获窗口画面，请检查窗口是否最小化")
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("窗口截图编码失败")
    return encoded.tobytes()
