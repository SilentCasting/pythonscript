"""Build dist/ChangeImageHash.exe with PyInstaller.

Usage (from the repository root, after ``pip install -e .[build]``):

    python packaging/build_exe.py
"""

import os
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "changeimagehash" / "assets"

PyInstaller.__main__.run(
    [
        str(ROOT / "packaging" / "app.py"),
        "--name=ChangeImageHash",
        "--onefile",
        "--windowed",
        "--noconfirm",
        f"--icon={ASSETS / 'icon.ico'}",
        # os.pathsep is ';' on Windows and ':' elsewhere, as PyInstaller expects.
        f"--add-data={ASSETS}{os.pathsep}changeimagehash/assets",
        "--collect-data=customtkinter",
        "--collect-all=tkinterdnd2",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT / 'build'}",
    ]
)
