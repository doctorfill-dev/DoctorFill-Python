"""
DoctorFill server entrypoint for PyInstaller.

This file uses absolute imports (no relative imports) so that
PyInstaller can bundle it as a standalone executable.
"""

import sys
import os
import multiprocessing

# Fix for macOS/Windows PyInstaller + multiprocessing
multiprocessing.freeze_support()

# When running as a PyInstaller bundle:
if getattr(sys, '_MEIPASS', None):
    # Ensure absolute imports work
    sys.path.insert(0, sys._MEIPASS)
    # Force debug off in bundled mode (prevents Flask reloader double-start)
    os.environ.setdefault('DEBUG', 'false')

if __name__ == "__main__":
    from src.web.app import main
    main()
