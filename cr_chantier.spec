# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller — CR Chantier
Génère un dossier dist/CR_Chantier/ avec CR_Chantier.exe
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collecte automatique des packages avec DLLs natives
all_datas, all_binaries, all_hidden = [], [], []
for pkg in ["ctranslate2", "faster_whisper", "sounddevice", "soundfile",
            "tokenizers", "huggingface_hub"]:
    d, b, h = collect_all(pkg)
    all_datas    += d
    all_binaries += b
    all_hidden   += h

# Templates Flask
all_datas += [("templates", "templates")]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden + [
        "flask", "flask.templating", "jinja2", "jinja2.ext",
        "werkzeug", "werkzeug.serving", "werkzeug.routing",
        "click", "requests", "numpy", "scipy",
        "faster_whisper", "ctranslate2", "tokenizers",
        "sounddevice", "soundfile",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "PyQt5", "PyQt6"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CR_Chantier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,        # Pas de fenêtre console noire
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="CR_Chantier",
)
