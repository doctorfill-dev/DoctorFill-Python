# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for DoctorFill Python backend sidecar.

Builds a single-file executable that Tauri will launch as a sidecar.
The output binary must be placed in src-tauri/binaries/ with the correct
target triple suffix for Tauri to find it.

Usage:
    pyinstaller --noconfirm pyinstaller.spec

After build, copy:
    dist/doctorfill-server -> src-tauri/binaries/doctorfill-server-<target-triple>
"""

import platform
import subprocess

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# ChromaDB uses dynamic imports heavily — collect everything
chromadb_datas, chromadb_binaries, chromadb_hiddenimports = collect_all("chromadb")

# Also collect all onnxruntime submodules (used by chromadb embeddings)
onnxruntime_hiddenimports = collect_submodules("onnxruntime")

# Determine the Rust target triple (Tauri sidecar naming convention)
def get_target_triple():
    try:
        out = subprocess.check_output(["rustc", "-vV"], text=True)
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split(":")[1].strip()
    except Exception:
        pass
    # Fallback
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "darwin":
        arch = "aarch64" if machine == "arm64" else "x86_64"
        return f"{arch}-apple-darwin"
    elif system == "windows":
        return "x86_64-pc-windows-msvc"
    else:
        return f"{machine}-unknown-linux-gnu"

TARGET_TRIPLE = get_target_triple()

a = Analysis(
    ["server.py"],
    pathex=["."],
    binaries=chromadb_binaries,
    datas=[
        ("src/web/static", "src/web/static"),
        ("templates", "templates"),
        ("forms", "forms"),
        (".env.example", "."),
    ] + chromadb_datas,
    hiddenimports=[
        # DoctorFill modules
        "src",
        "src.config",
        "src.config.settings",
        "src.config.user_config",
        "src.config.form_registry",
        "src.core",
        "src.core.template_manager",
        "src.core.type_converter",
        "src.llm",
        "src.llm.provider",
        "src.llm.infomaniak",
        "src.llm.local",
        "src.llm.response_parser",
        "src.pdf",
        "src.pdf.xfa",
        "src.pdf.xfa.extract",
        "src.pdf.xfa.fill",
        "src.pdf.xfa.inject",
        "src.rag",
        "src.rag.chunker",
        "src.rag.processor",
        "src.rag.context_builder",
        "src.pipeline",
        "src.pipeline.orchestrator",
        "src.pipeline.report_merger",
        "src.templates",
        "src.templates.loader",
        "src.web",
        "src.web.app",
        # Third-party
        "flask",
        "flask_cors",
        "dotenv",
        "tiktoken",
        "tiktoken_ext",
        "tiktoken_ext.openai_public",
        "numpy",
        "lxml",
        "lxml.etree",
        "pikepdf",
        "pymupdf",
        "fitz",
        "json_repair",
        "tqdm",
        "requests",
    ] + chromadb_hiddenimports + onnxruntime_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="doctorfill-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
