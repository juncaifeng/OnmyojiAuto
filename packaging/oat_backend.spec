"""FastAPI sidecar；由 uv 的 python-build-standalone 3.12 解释器构建。"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / "OAT" / "source"), "OAT/source"),
    (str(ROOT / "OAT" / "tools" / "settings.json"), "OAT/tools"),
    (str(ROOT / "OAT" / "tools" / "client.json"), "OAT/tools"),
    (str(ROOT / "yyx" / "yyx-launcher.exe"), "yyx"),
]
binaries = []
hiddenimports = []
for package in ("rapidocr", "onnxruntime"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

analysis = Analysis(
    [str(ROOT / "backend_entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt6", "qfluentwidgets", "OAT.app", "nuitka"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="oat-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "OAT" / "tools" / "uiResources" / "icon.ico"),
)
