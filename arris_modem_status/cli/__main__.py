"""
CLI package main module for direct execution.

This allows the CLI to be run with: python -m arris_modem_status.cli

Author: Charles Marshall
License: MIT
"""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main() or 0)
