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

# Ensure the project root is in sys.path for absolute imports
# when running as a PyInstaller bundle.
if getattr(sys, '_MEIPASS', None):
    sys.path.insert(0, sys._MEIPASS)

if __name__ == "__main__":
    from src.web.app import main
    main()
