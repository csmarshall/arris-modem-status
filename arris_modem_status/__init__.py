"""
Arris Modem Status Library - Comprehensive HNAP Client Package
=============================================================

High-performance, production-ready Python library for querying Arris cable modem diagnostics
via HNAP (Home Network Administration Protocol). Provides comprehensive status information,
channel diagnostics, and system monitoring capabilities with enterprise-grade reliability,
automatic HTTP compatibility handling, and extensive monitoring integration.

This library bridges the gap between Arris modems' embedded web interfaces and modern
Python applications, providing both simple one-liner access for basic use cases and
comprehensive configuration options for production monitoring and automation systems.

Package Architecture:
    The library follows a modular, layered architecture designed for reliability and extensibility:

    **Core Client Layer**:
        * ArrisModemStatusClient - Main client class with comprehensive configuration
        * HNAP authentication and session management
        * Intelligent retry logic and error recovery

    **HTTP Compatibility Layer**:
        * Browser-compatible HTTP parsing for maximum modem compatibility
        * Automatic fallback handling for strict HTTP parser issues
        * Cross-platform networking optimizations

    **Data Processing Layer**:
        * Structured channel information with automatic signal quality analysis
        * Time parsing utilities for uptime and system time data
        * Performance instrumentation and metrics collection

    **Error Handling System**:
        * Comprehensive exception hierarchy for different failure modes
        * Error analysis and recovery pattern tracking
        * Integration-ready error context for monitoring systems

Key Features:
    * **Production-Ready Reliability**: Intelligent retry logic, error recovery, and comprehensive testing
    * **HTTP Compatibility**: Browser-compatible parsing handles Arris modem HTTP variations automatically
    * **Performance Optimization**: Configurable concurrency modes with 30-84% performance improvements
    * **Monitoring Integration**: Built-in instrumentation and metrics for operational visibility
    * **Developer-Friendly**: Rich examples, comprehensive documentation, and intuitive APIs
    * **Enterprise Support**: Comprehensive error handling, logging, and troubleshooting capabilities

Quick Start Guide:
    **Basic Usage** - Get started in under 30 seconds:

    >>> from arris_modem_status import ArrisModemStatusClient
    >>>
    >>> # Simple status retrieval with automatic resource management
    >>> with ArrisModemStatusClient(password="your_admin_password") as client:
    ...     status = client.get_status()
    ...     print(f"Internet: {status['internet_status']}")
    ...     print(f"Model: {status['model_name']}")
    ...     print(f"Uptime: {status['system_uptime']}")
    ...     print(f"Channels: {len(status['downstream_channels'])} down, {len(status['upstream_channels'])} up")

    **Enhanced Configuration** - Production-ready with monitoring:

    >>> from arris_modem_status import ArrisModemStatusClient
    >>>
    >>> # Production configuration with performance monitoring
    >>> client = ArrisModemStatusClient(
    ...     password="admin_password",
    ...     host="192.168.100.1",           # Custom modem IP
    ...     concurrent=False,               # Serial mode for maximum reliability
    ...     max_retries=3,                  # Conservative retry strategy
    ...     timeout=(5, 15),                # (connect, read) timeouts
    ...     enable_instrumentation=True     # Enable performance monitoring
    ... )
    >>>
    >>> with client:
    ...     # Get comprehensive status with performance metrics
    ...     status = client.get_status()
    ...     metrics = client.get_performance_metrics()
    ...
    ...     # Analyze results
    ...     success_rate = (metrics['session_metrics']['successful_operations'] /
    ...                    metrics['session_metrics']['total_operations'])
    ...     print(f"Operation success rate: {success_rate:.1%}")
    ...     print(f"Total time: {metrics['session_metrics']['total_session_time']:.2f}s")

Performance Modes:
    **Serial Mode (Default - Recommended)**:
        Sequential request processing for maximum compatibility and reliability.
        Many Arris modems have firmware issues with concurrent HNAP requests.

        >>> client = ArrisModemStatusClient(
        ...     password="password",
        ...     concurrent=False  # Default setting
        ... )

    **Concurrent Mode**:
        Parallel request processing for ~30% speed improvement. Use with caution
        as some modems may return HTTP 403 errors or inconsistent data.

        >>> client = ArrisModemStatusClient(
        ...     password="password",
        ...     concurrent=True,     # Enable parallel processing
        ...     max_workers=2        # Limit concurrent requests
        ... )

Error Handling Patterns:
    The library provides a comprehensive exception hierarchy for different failure modes,
    enabling sophisticated error handling and automated recovery strategies:

    **Basic Error Handling** - Handle common authentication issues:

    >>> from arris_modem_status import (
    ...     ArrisModemStatusClient, ArrisAuthenticationError,
    ...     ArrisConnectionError, ArrisTimeoutError
    ... )
    >>>
    >>> try:
    ...     with ArrisModemStatusClient(password="test_password") as client:
    ...         status = client.get_status()
    ... except ArrisAuthenticationError as e:
    ...     print(f"Authentication failed - check password: {e}")
    ... except ArrisConnectionError as e:
    ...     print(f"Cannot reach modem - check network: {e}")
    ... except ArrisTimeoutError as e:
    ...     print(f"Request timed out - modem may be slow: {e}")

    **Advanced Error Analysis** - Production error monitoring:

    >>> from arris_modem_status import ArrisModemError
    >>>
    >>> def robust_modem_query():
    ...     max_attempts = 3
    ...     for attempt in range(max_attempts):
    ...         try:
    ...             with ArrisModemStatusClient(password="password") as client:
    ...                 return client.get_status()
    ...         except ArrisTimeoutError:
    ...             if attempt < max_attempts - 1:
    ...                 time.sleep(2 ** attempt)  # Exponential backoff
    ...                 continue
    ...             raise
    ...         except ArrisAuthenticationError:
    ...             # Don't retry authentication failures
    ...             raise
    ...         except ArrisModemError as e:
    ...             logger.error(f"Modem error (attempt {attempt + 1}): {e}")
    ...             if attempt == max_attempts - 1:
    ...                 raise

Channel Information Analysis:
    Rich channel diagnostic information with automatic signal quality assessment:

    >>> from arris_modem_status import ChannelInfo
    >>>
    >>> with ArrisModemStatusClient(password="password") as client:
    ...     status = client.get_status()
    ...
    ...     # Analyze downstream channels
    ...     for channel in status['downstream_channels']:
    ...         print(f"Channel {channel.channel_id}:")
    ...         print(f"  Frequency: {channel.frequency}")
    ...         print(f"  Power: {channel.power}")
    ...         print(f"  SNR: {channel.snr}")
    ...         print(f"  Quality: {channel.get_signal_quality()}")
    ...
    ...         if channel.needs_attention():
    ...             print(f"  ⚠️  Channel requires attention!")
    ...             print(f"  Errors: {channel.get_total_errors()}")

Time Parsing and Enhancement:
    Automatic time parsing converts modem time strings to Python objects:

    >>> from arris_modem_status import enhance_status_with_time_fields
    >>>
    >>> with ArrisModemStatusClient(password="password") as client:
    ...     status = client.get_status()
    ...
    ...     # Original string values preserved
    ...     print(f"Uptime (string): {status['system_uptime']}")
    ...     print(f"System time (string): {status['current_system_time']}")
    ...
    ...     # Enhanced with Python objects (automatic)
    ...     if 'system_uptime-seconds' in status:
    ...         uptime_days = status['system_uptime-seconds'] / 86400
    ...         print(f"Uptime: {uptime_days:.1f} days")
    ...
    ...     if 'current_system_time-ISO8601' in status:
    ...         print(f"ISO time: {status['current_system_time-ISO8601']}")

Production Deployment Patterns:
    **Configuration Management** - Environment-based setup:

    >>> import os
    >>> from arris_modem_status import ArrisModemStatusClient
    >>>
    >>> def create_production_client():
    ...     return ArrisModemStatusClient(
    ...         password=os.environ['ARRIS_ADMIN_PASSWORD'],
    ...         host=os.environ.get('ARRIS_MODEM_HOST', '192.168.100.1'),
    ...         concurrent=os.environ.get('ARRIS_CONCURRENT_MODE', 'false').lower() == 'true',
    ...         max_retries=int(os.environ.get('ARRIS_MAX_RETRIES', '3')),
    ...         timeout=(
    ...             int(os.environ.get('ARRIS_CONNECT_TIMEOUT', '5')),
    ...             int(os.environ.get('ARRIS_READ_TIMEOUT', '15'))
    ...         ),
    ...         enable_instrumentation=True
    ...     )

    **Monitoring Integration** - Prometheus/Grafana integration:

    >>> import time
    >>> from prometheus_client import Counter, Histogram, Gauge
    >>> from arris_modem_status import ArrisModemStatusClient, ArrisModemError
    >>>
    >>> # Define metrics
    >>> modem_requests_total = Counter('modem_requests_total', 'Total modem requests', ['status'])
    >>> modem_request_duration = Histogram('modem_request_duration_seconds', 'Request duration')
    >>> modem_channels_gauge = Gauge('modem_channels_total', 'Total channels', ['type'])
    >>>
    >>> def monitored_modem_query():
    ...     with modem_request_duration.time():
    ...         try:
    ...             with ArrisModemStatusClient(password="password") as client:
    ...                 status = client.get_status()
    ...
    ...                 # Update metrics
    ...                 modem_requests_total.labels(status='success').inc()
    ...                 modem_channels_gauge.labels(type='downstream').set(
    ...                     len(status['downstream_channels'])
    ...                 )
    ...                 modem_channels_gauge.labels(type='upstream').set(
    ...                     len(status['upstream_channels'])
    ...                 )
    ...
    ...                 return status
    ...         except ArrisModemError:
    ...             modem_requests_total.labels(status='error').inc()
    ...             raise

    **Logging Integration** - Structured logging for operations:

    >>> import logging
    >>> import json
    >>> from arris_modem_status import ArrisModemStatusClient
    >>>
    >>> # Configure structured logging
    >>> logging.basicConfig(level=logging.INFO)
    >>> logger = logging.getLogger(__name__)
    >>>
    >>> def logged_modem_operation():
    ...     start_time = time.time()
    ...     try:
    ...         with ArrisModemStatusClient(
    ...             password="password",
    ...             enable_instrumentation=True
    ...         ) as client:
    ...             status = client.get_status()
    ...             metrics = client.get_performance_metrics()
    ...
    ...             # Log success with structured data
    ...             logger.info("Modem query successful", extra={
    ...                 'json': {
    ...                     'duration': time.time() - start_time,
    ...                     'channels': {
    ...                         'downstream': len(status['downstream_channels']),
    ...                         'upstream': len(status['upstream_channels'])
    ...                     },
    ...                     'performance': {
    ...                         'total_operations': metrics['session_metrics']['total_operations'],
    ...                         'success_rate': metrics['session_metrics']['successful_operations'] /
    ...                                       metrics['session_metrics']['total_operations']
    ...                     }
    ...                 }
    ...             })
    ...             return status
    ...
    ...     except Exception as e:
    ...         logger.error("Modem query failed", extra={
    ...             'json': {
    ...                 'duration': time.time() - start_time,
    ...                 'error_type': type(e).__name__,
    ...                 'error_message': str(e)
    ...             }
    ...         })
    ...         raise

Advanced Configuration Patterns:
    **Custom Timeout Strategy** - Adaptive timeouts based on network conditions:

    >>> class AdaptiveModemClient:
    ...     def __init__(self, password: str, base_timeout: float = 10.0):
    ...         self.password = password
    ...         self.base_timeout = base_timeout
    ...         self.timeout_multiplier = 1.0
    ...
    ...     def get_status_with_adaptive_timeout(self):
    ...         current_timeout = self.base_timeout * self.timeout_multiplier
    ...
    ...         try:
    ...             with ArrisModemStatusClient(
    ...                 password=self.password,
    ...                 timeout=(current_timeout, current_timeout * 2)
    ...             ) as client:
    ...                 status = client.get_status()
    ...
    ...                 # Success - reduce timeout for next attempt
    ...                 self.timeout_multiplier = max(0.8, self.timeout_multiplier * 0.9)
    ...                 return status
    ...
    ...         except ArrisTimeoutError:
    ...             # Increase timeout for next attempt
    ...             self.timeout_multiplier = min(3.0, self.timeout_multiplier * 1.5)
    ...             raise

    **Connection Pooling** - Efficient resource usage for high-frequency monitoring:

    >>> from contextlib import contextmanager
    >>> from arris_modem_status import ArrisModemStatusClient
    >>> import threading
    >>> import time
    >>>
    >>> class ModemConnectionManager:
    ...     def __init__(self, password: str, **client_kwargs):
    ...         self.password = password
    ...         self.client_kwargs = client_kwargs
    ...         self._client = None
    ...         self._last_used = 0
    ...         self._lock = threading.Lock()
    ...
    ...     @contextmanager
    ...     def get_client(self):
    ...         with self._lock:
    ...             now = time.time()
    ...
    ...             # Reuse client if recent (within 5 minutes)
    ...             if self._client and (now - self._last_used) < 300:
    ...                 self._last_used = now
    ...                 yield self._client
    ...             else:
    ...                 # Create new client
    ...                 if self._client:
    ...                     self._client.close()
    ...
    ...                 self._client = ArrisModemStatusClient(
    ...                     password=self.password,
    ...                     **self.client_kwargs
    ...                 )
    ...                 self._last_used = now
    ...
    ...                 try:
    ...                     with self._client:
    ...                         yield self._client
    ...                 finally:
    ...                     # Keep client alive for reuse
    ...                     pass

Troubleshooting and Debugging:
    **Common Issues and Solutions**:

    >>> # Issue: HTTP 403 errors with concurrent mode
    >>> try:
    ...     with ArrisModemStatusClient(password="password", concurrent=True) as client:
    ...         status = client.get_status()
    ... except ArrisHTTPError as e:
    ...     if e.status_code == 403:
    ...         print("Modem rejected concurrent requests - switch to serial mode")
    ...         # Retry with serial mode
    ...         with ArrisModemStatusClient(password="password", concurrent=False) as client:
    ...             status = client.get_status()

    **Debug Mode** - Enable detailed logging for troubleshooting:

    >>> import logging
    >>> from arris_modem_status import ArrisModemStatusClient
    >>>
    >>> # Enable debug logging
    >>> logging.getLogger('arris-modem-status').setLevel(logging.DEBUG)
    >>>
    >>> with ArrisModemStatusClient(
    ...     password="password",
    ...     enable_instrumentation=True,
    ...     capture_errors=True
    ... ) as client:
    ...     status = client.get_status()
    ...
    ...     # Analyze errors and performance
    ...     error_analysis = client.get_error_analysis()
    ...     if error_analysis['total_errors'] > 0:
    ...         print(f"Captured {error_analysis['total_errors']} errors:")
    ...         for error_type, count in error_analysis['error_types'].items():
    ...             print(f"  {error_type}: {count}")
    ...
    ...     performance = client.get_performance_metrics()
    ...     print(f"Performance summary: {performance['session_metrics']}")

    **Validation and Health Checks** - Verify parsing and data quality:

    >>> with ArrisModemStatusClient(password="password") as client:
    ...     # Validate parsing quality
    ...     validation = client.validate_parsing()
    ...
    ...     print("Parsing Validation Results:")
    ...     parsing = validation['parsing_validation']
    ...     print(f"  Model parsed: {parsing['basic_info_parsed']}")
    ...     print(f"  Channels found: {parsing['downstream_channels_found']} down, {parsing['upstream_channels_found']} up")
    ...     print(f"  Data completeness: {validation['performance_metrics']['data_completeness_score']:.1f}%")

API Reference:
    **Main Classes**:
        * ArrisModemStatusClient - Primary client interface
        * ChannelInfo - Channel diagnostic data structure

    **Exception Hierarchy**:
        * ArrisModemError - Base exception class
        * ArrisAuthenticationError - Authentication failures
        * ArrisConnectionError - Network connectivity issues
        * ArrisTimeoutError - Request timeouts
        * ArrisHTTPError - HTTP protocol errors
        * ArrisParsingError - Response parsing failures
        * ArrisOperationError - High-level operation failures
        * ArrisConfigurationError - Configuration validation errors

    **Utility Functions**:
        * enhance_status_with_time_fields - Time parsing enhancement

Version Compatibility:
    **Current Version**: 1.0.0
    **Python Compatibility**: Python 3.8+
    **Backward Compatibility**: Full API stability guaranteed within major versions

    **Upgrade Paths**:
        * Minor versions (1.x.y): Backward compatible, new features only
        * Major versions (x.0.0): May include breaking changes with migration guide
        * Patch versions (1.0.x): Bug fixes only, always safe to upgrade

Package Dependencies:
    **Core Dependencies**:
        * requests - HTTP client library
        * urllib3 - HTTP connection pooling and retry logic

    **Optional Dependencies**:
        * prometheus_client - Metrics collection (install separately)

Security Considerations:
    **Credential Management**:
        * Never log or store passwords in plaintext
        * Use environment variables for password storage
        * Consider using credential management systems in production

    **Network Security**:
        * Library accepts self-signed certificates by default (modems typically use these)
        * All communication over HTTPS by default
        * No sensitive data is logged in error messages

Development and Contributing:
    **Development Setup**:
        ```bash
        git clone https://github.com/your-repo/arris-modem-status
        cd arris-modem-status
        pip install -e ".[dev]"
        python -m pytest tests/
        ```

    **Testing Patterns**:
        >>> # Mock testing for unit tests
        >>> from unittest.mock import Mock, patch
        >>> from arris_modem_status import ArrisModemStatusClient
        >>>
        >>> with patch('arris_modem_status.client.main.create_arris_compatible_session'):
        ...     client = ArrisModemStatusClient(password="test")
        ...     # Test client behavior without real modem

    **Performance Testing**:
        >>> import time
        >>> from arris_modem_status import ArrisModemStatusClient
        >>>
        >>> def performance_test():
        ...     times = []
        ...     for i in range(10):
        ...         start = time.time()
        ...         with ArrisModemStatusClient(password="password") as client:
        ...             status = client.get_status()
        ...         times.append(time.time() - start)
        ...
        ...     avg_time = sum(times) / len(times)
        ...     print(f"Average request time: {avg_time:.2f}s")

License and Legal:
    **License**: MIT License - free for commercial and personal use
    **Disclaimer**: This is an unofficial library not affiliated with ARRIS® or CommScope
    **Support**: Community-supported open source project

    **Attribution**:
        When using this library in commercial products, attribution is appreciated
        but not required under the MIT license terms.

Support and Community:
    **Documentation**: Full API documentation and examples available
    **Issues**: Report bugs and feature requests via GitHub issues
    **Discussions**: Community support and usage questions welcome
    **Contributing**: Pull requests welcome - see CONTRIBUTING.md

This comprehensive package provides everything needed for production modem monitoring,
from simple scripts to enterprise monitoring systems, with the reliability and
performance required for critical network infrastructure monitoring.

Author: Charles Marshall
License: MIT
"""

from .client.main import ArrisModemStatusClient
from .exceptions import (
    ArrisAuthenticationError,
    ArrisConfigurationError,
    ArrisConnectionError,
    ArrisHTTPError,
    ArrisModemError,
    ArrisOperationError,
    ArrisParsingError,
    ArrisTimeoutError,
)
from .models import ChannelInfo
from .time_utils import enhance_status_with_time_fields

# Version information
__version__ = "1.0.2"
__author__ = "Charles Marshall"
__license__ = "MIT"

# Public API
__all__ = [
    "ArrisAuthenticationError",
    "ArrisConfigurationError",
    "ArrisConnectionError",
    "ArrisHTTPError",
    "ArrisModemError",
    "ArrisModemStatusClient",
    "ArrisOperationError",
    "ArrisParsingError",
    "ArrisTimeoutError",
    "ChannelInfo",
    "__author__",
    "__license__",
    "__version__",
]
