"""
Arris Modem Status Client Package
=================================

This package provides the main client implementation for querying
Arris cable modem status via HNAP protocol.

The client is split into modular components:
- auth.py: HNAP authentication logic
- http.py: HTTP request handling and retry logic
- parser.py: Response parsing and channel data processing
- error_handler.py: Error analysis and capture
- main.py: Main client orchestration

"""

from .main import ArrisModemStatusClient

__all__ = ["ArrisModemStatusClient"]
