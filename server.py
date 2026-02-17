"""
DoctorFill server entrypoint for PyInstaller.

This file uses absolute imports (no relative imports) so that
PyInstaller can bundle it as a standalone executable.
"""

import sys
import os

# Ensure the project root is in sys.path for absolute imports
# when running as a PyInstaller bundle.
if getattr(sys, '_MEIPASS', None):
    sys.path.insert(0, sys._MEIPASS)

from src.web.app import app, main

if __name__ == "__main__":
    main()
