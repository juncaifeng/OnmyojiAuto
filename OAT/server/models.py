"""FastAPI 请求与响应模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClientSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hwnd: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=256)


class TaskStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(min_length=1, max_length=64)
    sub_mode: str = Field(default="", max_length=64)
    times: int = Field(ge=1, le=10000)
    client: ClientSelection
    hidden_window: bool = True
    sync_mode: bool = False
    explore_per_round: int | None = Field(default=5, ge=1, le=10000)
    explore_only: bool = False


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: Literal["light", "dark"] | None = None
    close_program_after_challenge: bool | None = None
    close_game_after_challenge: bool | None = None
    sync_mode: Literal["exactly_sync", "program_sync", "input_sync"] | None = None
    find_value: int | None = Field(default=None, ge=70, le=100)
    find_mode: Literal["opencv", "pyscreeze"] | None = None
    custom_res_width: int | None = Field(default=None, ge=320, le=7680)
    custom_res_height: int | None = Field(default=None, ge=240, le=4320)
    window_arrange_mode: Literal["diagonal", "tile"] | None = None
    windows_per_row: int | None = Field(default=None, ge=1, le=12)
    capture_window_mode: Literal["PrintWindow", "BitBlt"] | None = None
    emulator_type: Literal["pc", "mumu12"] | None = None
    mumu_folder: str | None = Field(default=None, max_length=1024)


class SyncStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_hwnd: int = Field(gt=0)
    sub_hwnds: list[int] = Field(min_length=1, max_length=32)


class MultiInstanceStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exe_path: str = Field(min_length=1, max_length=1024)
    count: int = Field(default=1, ge=1, le=20)
    interval: float = Field(default=5, ge=3, le=120)
