"""
Command Line Interface Package for Arris Modem Status Client

This package provides a modular CLI implementation with separated concerns:
- args.py: Argument parsing and validation
- connectivity.py: Network connectivity checks
- formatters.py: Output formatting for different data types
- logging_setup.py: Logging configuration
- main.py: Main orchestration and entry point

Author: Charles Marshall
License: MIT
"""

# Import main function from main module
from .main import main

# Export main function
__all__ = ["main"]
