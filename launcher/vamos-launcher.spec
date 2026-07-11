# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

SPEC_DIR = Path(SPECPATH)
ROOT = SPEC_DIR.parent

a = Analysis(
    [str(SPEC_DIR / "launcher.py")],
    pathex=[str(ROOT / "server")],
    binaries=[],
    datas=[
        (str(ROOT / "client" / "dist"), "client_dist"),
    ],
    hiddenimports=[
        "app.main",
        "app.models",
        "app.routers",
        "app.schemas",
        "app.services",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Vamos Subscription Tracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
