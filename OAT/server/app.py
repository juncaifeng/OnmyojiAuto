"""本地 API 路由、认证和应用生命周期。"""
from __future__ import annotations

import asyncio
import hmac
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from OAT.server.clients import list_clients, window_preview
from OAT.server.events import bus
from OAT.server.models import MultiInstanceStartRequest, SettingsPatch, SyncStartRequest, TaskStartRequest
from OAT.server.paths import oat_dir
from OAT.server.services import MultiInstanceService, SyncManager, TaskManager
from OAT.server.settings_service import get_settings, update_settings
from OAT.tools.settings import APP_VERSION


def create_app(api_token: str) -> FastAPI:
    if not api_token:
        raise ValueError("api_token 不能为空")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bus.set_loop(asyncio.get_running_loop())
        sync_manager = SyncManager()
        app.state.sync = sync_manager
        app.state.tasks = TaskManager(sync_manager.synchronizer)
        app.state.multi = MultiInstanceService()
        yield
        app.state.tasks.shutdown()
        sync_manager.synchronizer.stop_all_sync()

    app = FastAPI(
        title="OnmyojiAuto Local API",
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:1420",
            "http://127.0.0.1:1420",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-OAT-Token"],
    )

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path == "/api/v1/health" or request.method == "OPTIONS":
            return await call_next(request)
        supplied = request.headers.get("X-OAT-Token", "")
        if not hmac.compare_digest(supplied, api_token):
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        return await call_next(request)

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": APP_VERSION}

    @app.get("/api/v1/modes")
    async def modes():
        with (oat_dir() / "source" / "mode.json").open("r", encoding="utf-8") as file:
            raw = json.load(file)
        result = []
        for name, value in raw.items():
            if not value:
                continue
            result.append({
                "name": name,
                "sub_modes": [key for key in value if key != "default"] if isinstance(value, dict) else [],
            })
        return result

    @app.get("/api/v1/clients")
    async def clients():
        return await run_in_threadpool(list_clients)

    @app.get("/api/v1/clients/{hwnd}/preview")
    async def preview(hwnd: int):
        try:
            content = await run_in_threadpool(window_preview, hwnd)
            return Response(content=content, media_type="image/png")
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/tasks/current")
    async def current_task(request: Request):
        return request.app.state.tasks.snapshot()

    @app.post("/api/v1/tasks/start", status_code=202)
    async def start_task(payload: TaskStartRequest, request: Request):
        try:
            return await run_in_threadpool(request.app.state.tasks.start, payload)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/tasks/pause")
    async def pause_task(request: Request):
        return request.app.state.tasks.pause()

    @app.post("/api/v1/tasks/resume")
    async def resume_task(request: Request):
        return request.app.state.tasks.resume()

    @app.post("/api/v1/tasks/stop", status_code=202)
    async def stop_task(request: Request):
        return request.app.state.tasks.stop()

    @app.get("/api/v1/settings")
    async def settings():
        return get_settings()

    @app.patch("/api/v1/settings")
    async def patch_settings(payload: SettingsPatch):
        try:
            return await run_in_threadpool(update_settings, payload)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/v1/sync")
    async def sync_state(request: Request):
        return request.app.state.sync.snapshot()

    @app.post("/api/v1/sync/start")
    async def sync_start(payload: SyncStartRequest, request: Request):
        try:
            discovered = await run_in_threadpool(list_clients)
            request.app.state.sync.update_clients(discovered)
            return await run_in_threadpool(
                request.app.state.sync.start, payload.main_hwnd, payload.sub_hwnds
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/sync/stop")
    async def sync_stop(request: Request):
        return await run_in_threadpool(request.app.state.sync.stop)

    @app.post("/api/v1/sync/arrange")
    async def sync_arrange(request: Request):
        try:
            return await run_in_threadpool(request.app.state.sync.arrange)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/multi")
    async def multi_state(request: Request):
        return request.app.state.multi.snapshot()

    @app.post("/api/v1/multi/start", status_code=202)
    async def multi_start(payload: MultiInstanceStartRequest, request: Request):
        try:
            return request.app.state.multi.start(payload.exe_path, payload.count, payload.interval)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.delete("/api/v1/multi/{instance_id}")
    async def multi_close(instance_id: int, request: Request):
        if not await run_in_threadpool(request.app.state.multi.close, instance_id):
            raise HTTPException(status_code=404, detail="实例不存在或无法关闭")
        return {"closed": True}

    @app.websocket("/api/v1/events")
    async def events(websocket: WebSocket, token: str = Query(default="")):
        if not hmac.compare_digest(token, api_token):
            await websocket.close(code=4401)
            return
        await websocket.accept()
        try:
            async for event in bus.subscribe():
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass

    return app
