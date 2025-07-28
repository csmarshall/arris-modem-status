"""
CLI package main module for direct execution.

This allows the CLI to be run with: python -m arris_modem_status.cli

Author: Charles Marshall
License: MIT
"""

import sys

from .main import main

if __name__ == "__main__":
    # Set the program name for help display
    prog_name = "arris-modem-status"
    if len(sys.argv) > 0:
        # Check if running as module
        if sys.argv[0].endswith("__main__.py") or "-m" in sys.argv[0]:
            sys.argv[0] = prog_name

    sys.exit(main() or 0)
