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

# Import the main module itself, not just the function
from . import main

# Also export the main function for backward compatibility
from .main import main as main_function

# Export both for different use cases
__all__ = ["main", "main_function"]
