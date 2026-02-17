#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────
# DoctorFill build script
# Builds the Python sidecar + Tauri app
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 1. Determine target triple
TARGET_TRIPLE=$(rustc -vV | grep '^host:' | awk '{print $2}')
echo "==> Target: $TARGET_TRIPLE"

# 2. Build Python sidecar with PyInstaller
echo "==> Building Python sidecar..."
pyinstaller --noconfirm pyinstaller.spec

# 3. Copy binary to src-tauri/binaries/ with target triple suffix
mkdir -p src-tauri/binaries
SIDECAR_NAME="doctorfill-server-${TARGET_TRIPLE}"

if [[ "$TARGET_TRIPLE" == *"windows"* ]]; then
    cp "dist/doctorfill-server.exe" "src-tauri/binaries/${SIDECAR_NAME}.exe"
else
    cp "dist/doctorfill-server" "src-tauri/binaries/${SIDECAR_NAME}"
    chmod +x "src-tauri/binaries/${SIDECAR_NAME}"
fi

echo "==> Sidecar binary: src-tauri/binaries/${SIDECAR_NAME}"

# 4. Build Tauri app
echo "==> Building Tauri app..."
npm run tauri:build

echo "==> Build complete! Check src-tauri/target/release/bundle/"
