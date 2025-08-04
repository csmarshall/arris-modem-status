"""
Custom Exceptions for Arris Modem Status Client
===============================================

This module defines a comprehensive exception hierarchy for the arris-modem-status
library, providing structured error handling with rich context and debugging support.
The exception system is designed for both development debugging and production
monitoring, offering detailed error context while maintaining clean error propagation.

The exception hierarchy follows Python best practices with a base exception class
and specialized subclasses for different failure modes. Each exception includes
contextual details to aid in debugging, monitoring integration, and automated
error recovery.

Exception Hierarchy:
    ArrisModemError (base)
    ├── ArrisAuthenticationError (credential/session failures)
    ├── ArrisConnectionError (network connectivity issues)
    │   └── ArrisTimeoutError (timeout-specific connection failures)
    ├── ArrisHTTPError (HTTP-level errors with status codes)
    ├── ArrisParsingError (response parsing and data validation failures)
    ├── ArrisConfigurationError (invalid configuration parameters)
    └── ArrisOperationError (high-level operation failures)

Design Philosophy:
    * **Rich Context**: Every exception includes detailed context for debugging
    * **Monitoring Ready**: Structured details suitable for alerting systems
    * **Recovery Support**: Error types designed to guide automated recovery
    * **Developer Friendly**: Clear error messages with actionable guidance
    * **Production Safe**: No sensitive data exposure in error messages

Core Features:
    * **Structured Error Details**: Each exception carries contextual information
      in a standardized `details` dictionary for programmatic access
    * **Error Classification**: Automatic categorization enables smart retry logic
      and monitoring dashboard organization
    * **Chain Preservation**: Proper exception chaining maintains full error context
    * **Monitoring Integration**: Error details structured for external monitoring
      systems like Prometheus, Grafana, or custom dashboards

Usage Patterns:
    The exception system supports several common patterns for robust error handling:

    Basic Exception Handling:
        >>> try:
        ...     client = ArrisModemStatusClient(password="wrong")
        ...     client.authenticate()
        ... except ArrisAuthenticationError as e:
        ...     print(f"Authentication failed: {e}")
        ...     print(f"Error details: {e.details}")

    Hierarchical Error Handling:
        >>> try:
        ...     status = client.get_status()
        ... except ArrisAuthenticationError:
        ...     handle_auth_failure()
        ... except ArrisConnectionError:
        ...     handle_connectivity_issue()
        ... except ArrisModemError as e:
        ...     handle_general_modem_error(e)

    Monitoring Integration:
        >>> try:
        ...     operation_result = perform_modem_operation()
        ... except ArrisModemError as e:
        ...     metrics.increment(f'modem_errors.{type(e).__name__.lower()}')
        ...     if e.details:
        ...         log_error_context(e.details)
        ...     raise  # Re-raise for upstream handling

Error Context and Details:
    Each exception includes a `details` dictionary with structured information:

    >>> error = ArrisConnectionError(
    ...     "Failed to connect to modem",
    ...     details={
    ...         "host": "192.168.1.1",
    ...         "port": 443,
    ...         "timeout": 10.0,
    ...         "attempt": 3,
    ...         "error_type": "connection_refused"
    ...     }
    ... )
    >>> print(error.details["host"])  # "192.168.1.1"

Production Monitoring:
    The exception system integrates with monitoring and alerting systems:

    Error Rate Monitoring:
        >>> # Track error rates by exception type
        >>> error_metrics = {
        ...     'ArrisAuthenticationError': 0,
        ...     'ArrisConnectionError': 0,
        ...     'ArrisTimeoutError': 0,
        ...     'ArrisHTTPError': 0
        ... }
        >>>
        >>> try:
        ...     result = modem_operation()
        ... except ArrisModemError as e:
        ...     error_type = type(e).__name__
        ...     error_metrics[error_type] += 1
        ...
        ...     # Alert on high error rates
        ...     if error_metrics[error_type] > threshold:
        ...         send_alert(f"High {error_type} rate detected")

    Context-Aware Alerting:
        >>> def handle_modem_error(error: ArrisModemError) -> None:
        ...     if isinstance(error, ArrisTimeoutError):
        ...         if error.details.get("timeout_type") == "connection":
        ...             alert("Network connectivity issues detected")
        ...         elif error.details.get("timeout_type") == "read":
        ...             alert("Modem response slowness detected")
        ...
        ...     elif isinstance(error, ArrisHTTPError):
        ...         status_code = error.status_code
        ...         if status_code == 403:
        ...             alert("Authentication issues - check credentials")
        ...         elif status_code == 500:
        ...             alert("Modem internal error - may need restart")

Debugging and Development:
    The exception system provides rich debugging information:

    >>> try:
    ...     client.get_status()
    ... except ArrisParsingError as e:
    ...     print(f"Parsing failed: {e.message}")
    ...     if "response_type" in e.details:
    ...         print(f"Failed parsing: {e.details['response_type']}")
    ...     if "raw_data" in e.details:
    ...         print(f"Raw data: {e.details['raw_data'][:200]}...")

Exception Recovery Patterns:
    Different exception types suggest different recovery strategies:

    >>> def robust_modem_operation():
    ...     max_retries = 3
    ...
    ...     for attempt in range(max_retries):
    ...         try:
    ...             return client.get_status()
    ...
    ...         except ArrisTimeoutError:
    ...             # Retry with longer timeout
    ...             increase_timeout()
    ...             continue
    ...
    ...         except ArrisAuthenticationError:
    ...             # Re-authenticate and retry
    ...             client.authenticate()
    ...             continue
    ...
    ...         except ArrisHTTPError as e:
    ...             if e.status_code == 500:
    ...                 # Transient server error, retry
    ...                 time.sleep(2 ** attempt)
    ...                 continue
    ...             else:
    ...                 # Non-retryable HTTP error
    ...                 raise
    ...
    ...         except ArrisConfigurationError:
    ...             # Configuration errors don't retry
    ...             raise
    ...
    ...     raise ArrisOperationError("All retry attempts exhausted")

Integration with External Systems:
    The structured exception details integrate with external monitoring:

    Prometheus Metrics:
        >>> from prometheus_client import Counter, Histogram
        >>>
        >>> error_counter = Counter('arris_errors_total', 'Total errors', ['error_type'])
        >>> operation_duration = Histogram('arris_operation_duration_seconds', 'Operation duration')
        >>>
        >>> try:
        ...     with operation_duration.time():
        ...         result = client.get_status()
        ... except ArrisModemError as e:
        ...     error_counter.labels(error_type=type(e).__name__).inc()
        ...     raise

    Structured Logging:
        >>> import logging
        >>> import json
        >>>
        >>> logger = logging.getLogger(__name__)
        >>>
        >>> try:
        ...     result = modem_operation()
        ... except ArrisModemError as e:
        ...     error_context = {
        ...         'error_type': type(e).__name__,
        ...         'error_message': str(e),
        ...         'error_details': e.details,
        ...         'timestamp': time.time()
        ...     }
        ...     logger.error("Modem operation failed", extra={'json': error_context})

Error Context Standardization:
    Common detail keys across exception types:

    Network-Related Details:
        * host: Target hostname/IP
        * port: Target port number
        * timeout: Timeout value used
        * attempt: Retry attempt number
        * error_type: Specific error classification

    HTTP-Related Details:
        * status_code: HTTP response code
        * response_text: Response body snippet
        * headers: Relevant HTTP headers
        * operation: HNAP operation name

    Authentication Details:
        * phase: "challenge" or "login"
        * username: Login username (never password)
        * status_code: HTTP status if applicable

    Parsing Details:
        * response_type: Type of response being parsed
        * raw_data: Data that failed to parse (truncated)
        * parse_error: Underlying parsing error
        * field: Specific field that caused failure

Thread Safety and Concurrency:
    Exception handling in concurrent environments:

    >>> import threading
    >>> from concurrent.futures import ThreadPoolExecutor, as_completed
    >>>
    >>> def safe_modem_operation(host):
    ...     try:
    ...         return get_modem_status(host)
    ...     except ArrisModemError as e:
    ...         # Add thread context to error details
    ...         e.details['thread_id'] = threading.get_ident()
    ...         e.details['host'] = host
    ...         raise
    >>>
    >>> # Concurrent operations with error aggregation
    >>> errors = []
    >>> with ThreadPoolExecutor(max_workers=5) as executor:
    ...     futures = {executor.submit(safe_modem_operation, host): host
    ...               for host in modem_hosts}
    ...
    ...     for future in as_completed(futures):
    ...         try:
    ...             result = future.result()
    ...         except ArrisModemError as e:
    ...             errors.append(e)

Testing Exception Handling:
    Unit testing patterns for exception handling:

    >>> import pytest
    >>>
    >>> def test_authentication_error_handling():
    ...     with pytest.raises(ArrisAuthenticationError) as exc_info:
    ...         client = ArrisModemStatusClient(password="invalid")
    ...         client.authenticate()
    ...
    ...     error = exc_info.value
    ...     assert "phase" in error.details
    ...     assert error.details["phase"] in ["challenge", "login"]
    >>>
    >>> def test_connection_error_context():
    ...     with pytest.raises(ArrisConnectionError) as exc_info:
    ...         client = ArrisModemStatusClient(host="unreachable.host")
    ...         client.get_status()
    ...
    ...     error = exc_info.value
    ...     assert "host" in error.details
    ...     assert "port" in error.details

Best Practices for Exception Handling:
    * Always preserve the original exception through chaining
    * Include relevant context in the details dictionary
    * Use specific exception types for different failure modes
    * Log exceptions at the appropriate level with full context
    * Design recovery strategies based on exception types
    * Monitor exception rates and patterns for operational insights

Security Considerations:
    * Never include passwords or sensitive data in error messages
    * Limit response body content in error details (truncate long responses)
    * Be careful with file paths and system information in error context
    * Consider data privacy regulations when logging error details

This exception system provides a robust foundation for error handling that scales
from development debugging to production monitoring and automated recovery systems.

Author: Charles Marshall
License: MIT
"""

from typing import Any, Optional


class ArrisModemError(Exception):
    """
    Base exception for all Arris Modem Status Client errors.

    This is the root of the exception hierarchy for the arris-modem-status library.
    It provides the foundation for structured error handling with rich contextual
    information and monitoring integration capabilities.

    All library-specific exceptions inherit from this class, making it easy to catch
    all library errors with a single except clause while still allowing granular
    error handling for specific failure modes.

    The base class establishes the pattern of including structured details alongside
    human-readable error messages, supporting both development debugging and
    production monitoring workflows.

    Attributes:
        message: Human-readable error message describing what went wrong
        details: Dictionary containing structured error context for debugging
                and monitoring. Common keys include:
                - error_type: Classification of the error
                - timestamp: When the error occurred
                - operation: What operation was being performed
                - context: Additional relevant information

    Examples:
        Catching all library errors:

        >>> try:
        ...     client = ArrisModemStatusClient(password="test")
        ...     status = client.get_status()
        ... except ArrisModemError as e:
        ...     print(f"Modem operation failed: {e}")
        ...     if e.details:
        ...         print(f"Error context: {e.details}")

        Using error details for monitoring:

        >>> try:
        ...     result = modem_operation()
        ... except ArrisModemError as e:
        ...     error_type = type(e).__name__
        ...     metrics.increment(f'errors.{error_type.lower()}')
        ...
        ...     if e.details:
        ...         log_structured_error({
        ...             'error_class': error_type,
        ...             'error_message': str(e),
        ...             'error_details': e.details
        ...         })

        Exception chaining preservation:

        >>> try:
        ...     low_level_operation()
        ... except ConnectionError as e:
        ...     # Preserve original exception context
        ...     raise ArrisModemError(
        ...         "High-level operation failed",
        ...         details={"original_error": str(e)}
        ...     ) from e

    Design Considerations:
        * **Rich Context**: The details dictionary provides structured information
          beyond what fits in a human-readable message
        * **Monitoring Ready**: Exception attributes are designed for easy
          integration with monitoring and alerting systems
        * **Hierarchy Support**: Serves as base for specialized exception types
          while maintaining consistent interface
        * **Security Aware**: Framework supports including debug context while
          avoiding sensitive data exposure

    Integration Patterns:
        Error aggregation and analysis:

        >>> class ErrorTracker:
        ...     def __init__(self):
        ...         self.errors = []
        ...
        ...     def handle_error(self, error: ArrisModemError):
        ...         self.errors.append({
        ...             'type': type(error).__name__,
        ...             'message': error.message,
        ...             'details': error.details,
        ...             'timestamp': time.time()
        ...         })
        ...
        ...     def get_error_summary(self):
        ...         return {
        ...             'total_errors': len(self.errors),
        ...             'error_types': Counter(e['type'] for e in self.errors),
        ...             'recent_errors': self.errors[-10:]  # Last 10 errors
        ...         }

        Automated recovery decision making:

        >>> def should_retry_operation(error: ArrisModemError) -> bool:
        ...     # Base class errors are generally retryable unless specified
        ...     if isinstance(error, ArrisConfigurationError):
        ...         return False  # Config errors don't resolve with retries
        ...
        ...     if error.details and error.details.get('retry_exhausted'):
        ...         return False  # Already tried maximum retries
        ...
        ...     return True  # Most errors benefit from retry with backoff

    Thread Safety:
        Exception instances are immutable after creation and safe for concurrent
        access. The details dictionary should be treated as read-only after
        exception initialization.

    Note:
        This base exception provides the foundation for all library error handling.
        In most cases, you'll want to catch specific exception subclasses for
        targeted error handling, using ArrisModemError as a catch-all for
        unexpected library errors.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """
        Initialize base Arris modem error with message and contextual details.

        Args:
            message: Human-readable error message describing the failure.
                    Should be concise but descriptive enough for debugging.
                    Avoid including sensitive information like passwords.

            details: Optional dictionary containing structured error context.
                    Common keys include:
                    - error_type: String classification of error
                    - operation: Name of operation that failed
                    - timestamp: When error occurred
                    - retry_count: Number of attempts made
                    - context: Additional relevant information

        Examples:
            Basic error with message only:

            >>> error = ArrisModemError("Operation failed")
            >>> print(error.message)  # "Operation failed"

            Error with rich context:

            >>> error = ArrisModemError(
            ...     "Network operation timed out",
            ...     details={
            ...         "operation": "get_status",
            ...         "timeout": 30.0,
            ...         "attempt": 3,
            ...         "error_type": "timeout"
            ...     }
            ... )
            >>> print(error.details["operation"])  # "get_status"
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """
        Return string representation of the error with optional details.

        Provides a human-readable representation that includes both the main
        error message and a summary of available details when present.

        Returns:
            String representation suitable for logging and display

        Examples:
            >>> error = ArrisModemError("Connection failed")
            >>> str(error)
            'Connection failed'

            >>> error = ArrisModemError(
            ...     "Timeout occurred",
            ...     details={"timeout": 30, "host": "192.168.1.1"}
            ... )
            >>> str(error)
            'Timeout occurred (details: {'timeout': 30, 'host': '192.168.1.1'})'
        """
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ArrisAuthenticationError(ArrisModemError):
    """
    Raised when authentication with the Arris modem fails.

    This exception indicates problems with the credential verification process,
    including invalid passwords, expired sessions, challenge-response failures,
    or authentication protocol errors. It's a specialized exception that helps
    identify when problems are specifically related to user credentials or
    authentication state rather than network or protocol issues.

    Authentication failures are typically non-transient - they indicate either
    incorrect credentials or authentication system problems that require manual
    intervention rather than retry attempts.

    Common Scenarios:
        * Invalid admin password provided to client
        * Authentication challenge request fails
        * HMAC token generation or validation errors
        * Session cookies expired or invalid
        * Modem authentication system temporarily unavailable

    Attributes:
        message: Human-readable description of the authentication failure
        details: Dictionary with authentication-specific context:
                - phase: "challenge" or "login" indicating where failure occurred
                - username: Username attempted (never password for security)
                - status_code: HTTP status code if relevant
                - response: Truncated response from modem (if available)
                - attempt_count: Number of authentication attempts made

    Examples:
        Basic authentication error handling:

        >>> try:
        ...     client = ArrisModemStatusClient(password="wrong_password")
        ...     client.authenticate()
        ... except ArrisAuthenticationError as e:
        ...     print(f"Authentication failed: {e}")
        ...
        ...     # Check specific failure phase
        ...     if e.details.get("phase") == "challenge":
        ...         print("Failed to get authentication challenge")
        ...     elif e.details.get("phase") == "login":
        ...         print("Challenge succeeded but login failed - check password")

        Monitoring authentication failures:

        >>> def handle_auth_error(error: ArrisAuthenticationError):
        ...     metrics.increment('auth_failures_total')
        ...
        ...     failure_phase = error.details.get("phase", "unknown")
        ...     metrics.increment(f'auth_failures.{failure_phase}')
        ...
        ...     # Alert on repeated authentication failures
        ...     if error.details.get("attempt_count", 0) > 3:
        ...         alert("Multiple authentication failures detected")

        Smart retry logic:

        >>> def authenticate_with_retry(client, max_attempts=2):
        ...     for attempt in range(max_attempts):
        ...         try:
        ...             return client.authenticate()
        ...         except ArrisAuthenticationError as e:
        ...             if e.details.get("phase") == "challenge":
        ...                 # Challenge failures might be transient
        ...                 if attempt < max_attempts - 1:
        ...                     time.sleep(1)
        ...                     continue
        ...
        ...             # Login failures indicate bad credentials
        ...             elif e.details.get("phase") == "login":
        ...                 raise  # Don't retry login failures
        ...
        ...             raise  # Re-raise after exhausting retries

    Integration with Authentication Flow:
        The exception integrates with the HNAP authentication process:

        >>> class HNAPAuthenticator:
        ...     def authenticate(self):
        ...         try:
        ...             # Step 1: Request challenge
        ...             challenge = self.request_challenge()
        ...         except Exception as e:
        ...             raise ArrisAuthenticationError(
        ...                 "Failed to get authentication challenge",
        ...                 details={"phase": "challenge", "error": str(e)}
        ...             ) from e
        ...
        ...         try:
        ...             # Step 2: Submit credentials
        ...             return self.submit_credentials(challenge)
        ...         except Exception as e:
        ...             raise ArrisAuthenticationError(
        ...                 "Login failed with provided credentials",
        ...                 details={"phase": "login", "error": str(e)}
        ...             ) from e

    Security Considerations:
        * Never includes actual passwords in error messages or details
        * Limits response data to prevent information disclosure
        * Username included only for debugging, not sensitive
        * Error timing doesn't reveal whether username or password was wrong

    Recovery Patterns:
        Authentication errors typically require user intervention:

        >>> def handle_auth_recovery(error: ArrisAuthenticationError):
        ...     if error.details.get("phase") == "challenge":
        ...         # Network or modem issue - retry may help
        ...         return "retry_with_backoff"
        ...     elif error.details.get("phase") == "login":
        ...         # Credential issue - user action needed
        ...         return "prompt_for_new_password"
        ...     else:
        ...         # Unknown issue - investigate
        ...         return "manual_investigation"

    This exception type enables sophisticated authentication error handling that
    can distinguish between transient network issues and persistent credential
    problems, supporting both automated recovery and user-guided resolution.
    """


class ArrisConnectionError(ArrisModemError):
    """
    Raised when connection to the Arris modem cannot be established.

    This exception covers all network-level connectivity problems that prevent
    communication with the modem, including DNS resolution failures, network
    unreachability, connection refused errors, and socket-level issues.

    Connection errors are often transient and may resolve with retry attempts,
    but can also indicate persistent network configuration issues, modem power
    problems, or network infrastructure failures that require investigation.

    The exception provides detailed context about the connection attempt to aid
    in diagnosing whether the issue is local network configuration, modem
    availability, or broader network connectivity problems.

    Common Scenarios:
        * Modem is powered off or unreachable
        * Incorrect IP address or hostname configuration
        * Network routing issues preventing access to modem
        * Firewall blocking connections to modem ports
        * DNS resolution failure for modem hostname
        * SSL/TLS handshake failures with HTTPS connections

    Attributes:
        message: Human-readable description of the connection failure
        details: Dictionary with connection-specific context:
                - host: Target hostname or IP address
                - port: Target port number
                - timeout: Connection timeout value used
                - error_type: Specific connection error classification
                - original_error: Original exception details
                - attempt: Retry attempt number if applicable

    Examples:
        Basic connection error handling:

        >>> try:
        ...     client = ArrisModemStatusClient(host="unreachable.host")
        ...     status = client.get_status()
        ... except ArrisConnectionError as e:
        ...     print(f"Cannot reach modem: {e}")
        ...
        ...     # Check specific failure details
        ...     if e.details.get("error_type") == "connection_refused":
        ...         print("Modem rejected connection - check if web interface is enabled")
        ...     elif e.details.get("error_type") == "timeout":
        ...         print("Connection timed out - check network connectivity")

        Network diagnostics integration:

        >>> def diagnose_connection_error(error: ArrisConnectionError):
        ...     host = error.details.get("host")
        ...     port = error.details.get("port")
        ...
        ...     diagnostics = {
        ...         "ping_result": ping_host(host),
        ...         "port_scan": scan_port(host, port),
        ...         "dns_resolution": resolve_hostname(host),
        ...         "route_trace": trace_route_to_host(host)
        ...     }
        ...
        ...     return diagnostics

        Smart retry with exponential backoff:

        >>> def connect_with_retry(client, max_attempts=3):
        ...     for attempt in range(max_attempts):
        ...         try:
        ...             return client.get_status()
        ...         except ArrisConnectionError as e:
        ...             if attempt < max_attempts - 1:
        ...                 # Exponential backoff for connection retries
        ...                 backoff_time = 2 ** attempt
        ...                 print(f"Connection failed, retrying in {backoff_time}s...")
        ...                 time.sleep(backoff_time)
        ...                 continue
        ...
        ...             # Add retry context to final error
        ...             e.details["retry_attempts"] = max_attempts
        ...             e.details["final_attempt"] = True
        ...             raise

    Integration with Network Layer:
        Connection errors are wrapped from lower-level network exceptions:

        >>> import socket
        >>> import requests
        >>>
        >>> def make_modem_request(host, port):
        ...     try:
        ...         response = requests.get(f"https://{host}:{port}/", timeout=10)
        ...         return response
        ...     except requests.exceptions.ConnectionError as e:
        ...         raise ArrisConnectionError(
        ...             f"Failed to connect to {host}:{port}",
        ...             details={
        ...                 "host": host,
        ...                 "port": port,
        ...                 "error_type": "connection_refused",
        ...                 "original_error": str(e)
        ...             }
        ...         ) from e
        ...     except requests.exceptions.Timeout as e:
        ...         raise ArrisTimeoutError(  # Specialized subclass
        ...             f"Connection to {host}:{port} timed out",
        ...             details={
        ...                 "host": host,
        ...                 "port": port,
        ...                 "timeout_type": "connection",
        ...                 "original_error": str(e)
        ...             }
        ...         ) from e

    Monitoring and Alerting:
        Connection errors provide rich context for monitoring systems:

        >>> def monitor_connection_health(error: ArrisConnectionError):
        ...     host = error.details.get("host", "unknown")
        ...     error_type = error.details.get("error_type", "unknown")
        ...
        ...     # Track connection failures by host and type
        ...     metrics.increment(f'connection_errors.{error_type}', tags=[f'host:{host}'])
        ...
        ...     # Alert on persistent connection issues
        ...     if error.details.get("retry_attempts", 0) >= 3:
        ...         alert(f"Persistent connection failures to {host}")

    Troubleshooting Support:
        Error details support automated troubleshooting guidance:

        >>> def suggest_connection_fixes(error: ArrisConnectionError):
        ...     suggestions = []
        ...     error_type = error.details.get("error_type")
        ...     host = error.details.get("host")
        ...
        ...     if error_type == "connection_refused":
        ...         suggestions.extend([
        ...             f"Check if {host} is powered on and responsive",
        ...             "Verify web interface is enabled on modem",
        ...             "Check firewall settings blocking the connection"
        ...         ])
        ...     elif error_type == "timeout":
        ...         suggestions.extend([
        ...             f"Test network connectivity: ping {host}",
        ...             "Check for network congestion or packet loss",
        ...             "Verify correct IP address and network segment"
        ...         ])
        ...
        ...     return suggestions

    This exception enables sophisticated connection error handling that can
    distinguish between different types of network failures and provide
    appropriate recovery strategies and troubleshooting guidance.
    """


class ArrisTimeoutError(ArrisConnectionError):
    """
    Raised when a timeout occurs during communication with the Arris modem.

    This is a specialized connection error that specifically handles timeout
    scenarios during modem communication. Timeouts can occur at different
    stages of the communication process and often indicate different underlying
    issues that require different recovery strategies.

    Timeout errors are generally more likely to be transient than other
    connection failures, as they may indicate temporary network congestion,
    modem busy states, or resource contention rather than persistent
    configuration problems.

    The exception provides detailed context about what type of timeout occurred
    and at what stage of the communication process, enabling intelligent retry
    logic and appropriate timeout adjustments.

    Timeout Categories:
        * **Connection Timeout**: Failed to establish initial connection
        * **Read Timeout**: Connection established but no response received
        * **Operation Timeout**: Overall operation exceeded time limit
        * **SSL Handshake Timeout**: HTTPS negotiation took too long

    Attributes:
        message: Human-readable description of the timeout
        details: Dictionary with timeout-specific context:
                - timeout_type: "connection", "read", "operation", or "ssl"
                - timeout_value: The timeout value that was exceeded
                - operation: What operation was being performed
                - elapsed_time: How long the operation ran before timing out
                - host: Target host that timed out
                - port: Target port number

    Examples:
        Timeout-specific error handling:

        >>> try:
        ...     status = client.get_status()
        ... except ArrisTimeoutError as e:
        ...     timeout_type = e.details.get("timeout_type")
        ...
        ...     if timeout_type == "connection":
        ...         print("Failed to connect - network may be slow")
        ...     elif timeout_type == "read":
        ...         print("Connected but modem didn't respond - may be busy")
        ...     elif timeout_type == "operation":
        ...         print("Operation took too long - try increasing timeout")

        Adaptive timeout adjustment:

        >>> class AdaptiveTimeoutClient:
        ...     def __init__(self):
        ...         self.base_timeout = 10.0
        ...         self.timeout_multiplier = 1.0
        ...
        ...     def get_status_with_adaptive_timeout(self):
        ...         current_timeout = self.base_timeout * self.timeout_multiplier
        ...
        ...         try:
        ...             client = ArrisModemStatusClient(timeout=current_timeout)
        ...             return client.get_status()
        ...         except ArrisTimeoutError as e:
        ...             # Increase timeout for next attempt
        ...             self.timeout_multiplier = min(self.timeout_multiplier * 1.5, 4.0)
        ...
        ...             # Add adaptive context to error
        ...             e.details["adaptive_timeout_used"] = current_timeout
        ...             e.details["next_timeout_will_be"] = self.base_timeout * self.timeout_multiplier
        ...             raise

        Performance monitoring integration:

        >>> def track_timeout_patterns(error: ArrisTimeoutError):
        ...     timeout_type = error.details.get("timeout_type", "unknown")
        ...     elapsed = error.details.get("elapsed_time", 0)
        ...     operation = error.details.get("operation", "unknown")
        ...
        ...     # Track timeout duration patterns
        ...     metrics.histogram(f'timeout_duration.{timeout_type}', elapsed)
        ...     metrics.increment(f'timeouts.{timeout_type}.{operation}')
        ...
        ...     # Alert on timeout trend changes
        ...     if should_alert_on_timeout_pattern(timeout_type, elapsed):
        ...         alert(f"Unusual {timeout_type} timeout pattern detected")

    Integration with Retry Logic:
        Timeout errors often benefit from retry with adjusted parameters:

        >>> def retry_with_timeout_escalation(operation_func, max_attempts=3):
        ...     base_timeout = 10.0
        ...
        ...     for attempt in range(max_attempts):
        ...         # Escalate timeout with each attempt
        ...         timeout = base_timeout * (1.5 ** attempt)
        ...
        ...         try:
        ...             return operation_func(timeout=timeout)
        ...         except ArrisTimeoutError as e:
        ...             e.details["retry_attempt"] = attempt + 1
        ...             e.details["timeout_used"] = timeout
        ...
        ...             if attempt < max_attempts - 1:
        ...                 print(f"Timeout after {timeout}s, retrying with longer timeout...")
        ...                 continue
        ...
        ...             # Final timeout - add escalation context
        ...             e.details["timeout_escalation_attempted"] = True
        ...             e.details["max_timeout_reached"] = timeout
        ...             raise

    Network Quality Assessment:
        Timeout patterns can indicate network quality issues:

        >>> class NetworkQualityMonitor:
        ...     def __init__(self):
        ...         self.timeout_history = []
        ...
        ...     def record_timeout(self, error: ArrisTimeoutError):
        ...         self.timeout_history.append({
        ...             'timestamp': time.time(),
        ...             'type': error.details.get('timeout_type'),
        ...             'duration': error.details.get('elapsed_time'),
        ...             'operation': error.details.get('operation')
        ...         })
        ...
        ...         # Keep only recent history
        ...         cutoff = time.time() - 3600  # Last hour
        ...         self.timeout_history = [
        ...             t for t in self.timeout_history if t['timestamp'] > cutoff
        ...         ]
        ...
        ...     def assess_network_quality(self):
        ...         if len(self.timeout_history) > 10:  # High timeout rate
        ...             return "poor"
        ...         elif len(self.timeout_history) > 5:
        ...             return "degraded"
        ...         else:
        ...             return "good"

    Diagnostic Information:
        Timeout errors provide context for network diagnostics:

        >>> def diagnose_timeout_cause(error: ArrisTimeoutError):
        ...     diagnostics = {}
        ...     timeout_type = error.details.get("timeout_type")
        ...     host = error.details.get("host")
        ...
        ...     if timeout_type == "connection":
        ...         diagnostics["likely_causes"] = [
        ...             "Network congestion",
        ...             "Modem overloaded",
        ...             "Routing issues"
        ...         ]
        ...         diagnostics["recommended_tests"] = [
        ...             f"ping {host}",
        ...             f"traceroute {host}",
        ...             "Check network interface statistics"
        ...         ]
        ...     elif timeout_type == "read":
        ...         diagnostics["likely_causes"] = [
        ...             "Modem processing delays",
        ...             "High modem CPU usage",
        ...             "HNAP service busy"
        ...         ]
        ...         diagnostics["recommended_actions"] = [
        ...             "Increase read timeout",
        ...             "Reduce request frequency",
        ...             "Check modem system load"
        ...         ]
        ...
        ...     return diagnostics

    This specialized timeout exception enables fine-grained timeout handling
    that can adapt to network conditions and provide intelligent recovery
    strategies based on the specific type and context of the timeout.
    """


class ArrisHTTPError(ArrisModemError):
    r"""
    Raised when HTTP-level errors occur during modem communication.

    This exception handles all HTTP protocol-level errors including client errors
    (4xx status codes), server errors (5xx status codes), and HTTP parsing issues.
    It provides detailed information about the HTTP response to aid in debugging
    and determining appropriate recovery strategies.

    HTTP errors often indicate specific types of problems:
    - 4xx errors suggest client-side issues (authentication, malformed requests)
    - 5xx errors suggest modem-side issues (internal errors, overload)
    - Parsing errors suggest protocol compatibility issues

    The exception preserves both the HTTP status code for programmatic handling
    and response content for debugging, while being careful not to expose
    sensitive information in error messages.

    Attributes:
        message: Human-readable description of the HTTP error
        status_code: HTTP status code if available (e.g., 403, 500)
        details: Dictionary with HTTP-specific context:
                - status_code: HTTP response status code
                - response_text: Truncated response body for debugging
                - headers: Relevant HTTP response headers
                - operation: HNAP operation that failed
                - url: Request URL that generated error
                - method: HTTP method used (GET, POST, etc.)

    Examples:
        HTTP error handling with status code logic:

        >>> try:
        ...     status = client.get_status()
        ... except ArrisHTTPError as e:
        ...     if e.status_code == 403:
        ...         print("Authentication failed - check password")
        ...         # Attempt re-authentication
        ...         client.authenticate()
        ...     elif e.status_code == 500:
        ...         print("Modem internal error - may be temporary")
        ...         # Retry with backoff
        ...         time.sleep(5)
        ...     elif e.status_code == 404:
        ...         print("HNAP endpoint not found - check modem model compatibility")
        ...     else:
        ...         print(f"HTTP error {e.status_code}: {e}")

        Response content analysis for debugging:

        >>> def analyze_http_error(error: ArrisHTTPError):
        ...     response_text = error.details.get("response_text", "")
        ...
        ...     if "authentication" in response_text.lower():
        ...         return "auth_required"
        ...     elif "internal server error" in response_text.lower():
        ...         return "server_error"
        ...     elif "not found" in response_text.lower():
        ...         return "endpoint_missing"
        ...     else:
        ...         return "unknown_http_error"

        Monitoring HTTP error patterns:

        >>> def monitor_http_errors(error: ArrisHTTPError):
        ...     status_code = error.status_code or 0
        ...     operation = error.details.get("operation", "unknown")
        ...
        ...     # Track error rates by status code and operation
        ...     metrics.increment(f'http_errors.{status_code}')
        ...     metrics.increment(f'http_errors.{operation}.{status_code}')
        ...
        ...     # Alert on specific error patterns
        ...     if status_code == 403:
        ...         alert("Authentication failures detected")
        ...     elif status_code in [500, 502, 503]:
        ...         alert("Modem server errors detected")

    Integration with HNAP Protocol:
        HTTP errors in the context of HNAP operations:

        >>> class HNAPClient:
        ...     def make_hnap_request(self, action, body):
        ...         try:
        ...             response = self.session.post(
        ...                 f"{self.base_url}/HNAP1/",
        ...                 json=body,
        ...                 headers=self.get_hnap_headers(action)
        ...             )
        ...             response.raise_for_status()
        ...             return response.text
        ...         except requests.exceptions.HTTPError as e:
        ...             status_code = e.response.status_code if e.response else None
        ...             response_text = e.response.text if e.response else ""
        ...
        ...             raise ArrisHTTPError(
        ...                 f"HNAP request failed with HTTP {status_code}",
        ...                 status_code=status_code,
        ...                 details={
        ...                     "operation": action,
        ...                     "response_text": response_text[:500],  # Truncate long responses
        ...                     "url": f"{self.base_url}/HNAP1/",
        ...                     "method": "POST"
        ...                 }
        ...             ) from e

    Status Code Classification and Recovery:
        Different HTTP status codes suggest different recovery strategies:

        >>> def determine_recovery_strategy(error: ArrisHTTPError) -> str:
        ...     status_code = error.status_code
        ...
        ...     if status_code in [400, 401, 403]:
        ...         # Client errors - likely need authentication or request fixes
        ...         return "reauthenticate"
        ...     elif status_code in [429, 503]:
        ...         # Rate limiting or service unavailable - back off
        ...         return "backoff_and_retry"
        ...     elif status_code in [500, 502, 504]:
        ...         # Server errors - may be transient
        ...         return "retry_with_delay"
        ...     elif status_code == 404:
        ...         # Not found - likely configuration issue
        ...         return "check_configuration"
        ...     else:
        ...         return "manual_investigation"

        Smart retry implementation:

        >>> def retry_http_operation(operation_func, max_attempts=3):
        ...     for attempt in range(max_attempts):
        ...         try:
        ...             return operation_func()
        ...         except ArrisHTTPError as e:
        ...             recovery = determine_recovery_strategy(e)
        ...
        ...             if recovery == "reauthenticate" and attempt == 0:
        ...                 # Try re-authentication once
        ...                 client.authenticate()
        ...                 continue
        ...             elif recovery == "retry_with_delay":
        ...                 if attempt < max_attempts - 1:
        ...                     delay = 2 ** attempt
        ...                     time.sleep(delay)
        ...                     continue
        ...             elif recovery == "check_configuration":
        ...                 # Don't retry configuration errors
        ...                 break
        ...
        ...             raise  # Re-raise if no recovery strategy or retries exhausted

    Response Analysis and Debugging:
        HTTP errors provide valuable debugging information:

        >>> def extract_debug_info(error: ArrisHTTPError):
        ...     debug_info = {
        ...         "status_code": error.status_code,
        ...         "error_message": str(error),
        ...         "operation": error.details.get("operation"),
        ...         "response_snippet": error.details.get("response_text", "")[:200]
        ...     }
        ...
        ...     # Parse common error patterns
        ...     response_text = error.details.get("response_text", "").lower()
        ...     if "invalid session" in response_text:
        ...         debug_info["likely_cause"] = "expired_session"
        ...     elif "malformed request" in response_text:
        ...         debug_info["likely_cause"] = "request_format_error"
        ...     elif "service unavailable" in response_text:
        ...         debug_info["likely_cause"] = "modem_overloaded"
        ...
        ...     return debug_info

    Security Considerations:
        HTTP errors may contain sensitive information that should be handled carefully:

        >>> def sanitize_http_error_for_logging(error: ArrisHTTPError):
        ...     # Create safe version for logging without sensitive data
        ...     safe_details = error.details.copy()
        ...
        ...     # Remove or truncate potentially sensitive response content
        ...     if "response_text" in safe_details:
        ...         response = safe_details["response_text"]
        ...         # Remove authentication tokens or session data
        ...         response = re.sub(r'"token":\s*"[^"]*"', '"token": "[REDACTED]"', response)
        ...         response = re.sub(r'"session":\s*"[^"]*"', '"session": "[REDACTED]"', response)
        ...         safe_details["response_text"] = response[:200]  # Truncate
        ...
        ...     return safe_details

    This HTTP error exception provides comprehensive support for diagnosing and
    recovering from HTTP protocol issues while maintaining security and providing
    rich context for monitoring and debugging systems.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize HTTP error with status code and contextual details.

        Args:
            message: Human-readable error message describing the HTTP failure
            status_code: HTTP status code from the response (e.g., 403, 500)
            details: Optional dictionary with HTTP-specific context including
                    response content, headers, operation details, and request info

        Examples:
            Basic HTTP error:

            >>> error = ArrisHTTPError("Request failed", status_code=403)
            >>> print(error.status_code)  # 403

            HTTP error with detailed context:

            >>> error = ArrisHTTPError(
            ...     "HNAP request failed",
            ...     status_code=500,
            ...     details={
            ...         "operation": "GetCustomerStatusSoftware",
            ...         "response_text": "Internal Server Error",
            ...         "url": "https://192.168.1.1/HNAP1/",
            ...         "method": "POST"
            ...     }
            ... )
        """
        super().__init__(message, details)
        self.status_code = status_code
        if status_code and self.details is not None:
            self.details["status_code"] = status_code


class ArrisParsingError(ArrisModemError):
    """
    Raised when parsing modem responses fails.

    This exception handles all failures related to processing and interpreting
    data received from the Arris modem, including JSON parsing failures,
    unexpected response formats, missing required fields, and data validation
    errors.

    Parsing errors often indicate either protocol changes in modem firmware,
    compatibility issues between different modem models, or data corruption
    during transmission. These errors provide detailed context about what
    data failed to parse and why.

    The exception is designed to help developers understand exactly what went
    wrong during parsing so they can either adapt the parsing logic or
    identify modem compatibility issues.

    Common Scenarios:
        * JSON parsing failures due to malformed response data
        * Missing expected fields in HNAP responses
        * Unexpected data formats from different firmware versions
        * Channel data parsing failures due to format changes
        * Response structure changes in modem firmware updates

    Attributes:
        message: Human-readable description of the parsing failure
        details: Dictionary with parsing-specific context:
                - response_type: Type of response that failed to parse
                - raw_data: Raw data that couldn't be parsed (truncated)
                - parse_error: Details of the underlying parsing error
                - field: Specific field that caused parsing failure
                - expected_format: What format was expected
                - actual_format: What format was encountered

    Examples:
        Parsing error handling with fallback logic:

        >>> try:
        ...     status = client.get_status()
        ... except ArrisParsingError as e:
        ...     response_type = e.details.get("response_type")
        ...
        ...     if response_type == "channel_data":
        ...         print("Channel data parsing failed - using defaults")
        ...         status = get_default_status_with_no_channels()
        ...     elif response_type == "json":
        ...         print("JSON parsing failed - check response format")
        ...         print(f"Raw data: {e.details.get('raw_data', '')[:100]}...")
        ...
        ...     # Log parsing failure for investigation
        ...     log_parsing_failure(e)

        Parsing error analysis for debugging:

        >>> def analyze_parsing_error(error: ArrisParsingError):
        ...     analysis = {
        ...         "error_type": error.details.get("parse_error", "unknown"),
        ...         "response_type": error.details.get("response_type"),
        ...         "data_length": len(error.details.get("raw_data", "")),
        ...         "has_json_structure": False,
        ...         "missing_fields": []
        ...     }
        ...
        ...     raw_data = error.details.get("raw_data", "")
        ...
        ...     # Check if data looks like JSON
        ...     if raw_data.strip().startswith(("{", "[")):
        ...         analysis["has_json_structure"] = True
        ...
        ...         # Try to identify missing expected fields
        ...         if "GetMultipleHNAPsResponse" not in raw_data:
        ...             analysis["missing_fields"].append("GetMultipleHNAPsResponse")
        ...
        ...     return analysis

        Compatibility testing across modem models:

        >>> class ParsingCompatibilityTracker:
        ...     def __init__(self):
        ...         self.parsing_failures = {}
        ...
        ...     def record_parsing_failure(self, error: ArrisParsingError, modem_model: str):
        ...         key = f"{modem_model}_{error.details.get('response_type', 'unknown')}"
        ...
        ...         if key not in self.parsing_failures:
        ...             self.parsing_failures[key] = []
        ...
        ...         self.parsing_failures[key].append({
        ...             "timestamp": time.time(),
        ...             "error": str(error),
        ...             "details": error.details
        ...         })
        ...
        ...     def get_compatibility_report(self):
        ...         return {
        ...             "models_with_issues": list(self.parsing_failures.keys()),
        ...             "total_failures": sum(len(failures) for failures in self.parsing_failures.values()),
        ...             "failure_breakdown": {k: len(v) for k, v in self.parsing_failures.items()}
        ...         }

    Integration with Response Processing:
        Parsing errors integrate with the response processing pipeline:

        >>> class ResponseParser:
        ...     def parse_hnap_response(self, response_text: str, response_type: str):
        ...         try:
        ...             # Attempt JSON parsing
        ...             data = json.loads(response_text)
        ...             return self.process_hnap_data(data, response_type)
        ...         except json.JSONDecodeError as e:
        ...             raise ArrisParsingError(
        ...                 f"Failed to parse {response_type} as JSON",
        ...                 details={
        ...                     "response_type": response_type,
        ...                     "raw_data": response_text[:500],  # Truncate long responses
        ...                     "parse_error": str(e),
        ...                     "error_position": getattr(e, 'pos', None)
        ...                 }
        ...             ) from e
        ...         except KeyError as e:
        ...             raise ArrisParsingError(
        ...                 f"Missing required field in {response_type}",
        ...                 details={
        ...                     "response_type": response_type,
        ...                     "missing_field": str(e),
        ...                     "raw_data": response_text[:500]
        ...                 }
        ...             ) from e

        Graceful degradation with partial parsing:

        >>> def parse_with_fallback(response_data, response_type):
        ...     try:
        ...         return parse_complete_response(response_data, response_type)
        ...     except ArrisParsingError as e:
        ...         # Log the parsing error
        ...         logger.warning(f"Parsing failed for {response_type}: {e}")
        ...
        ...         # Attempt partial parsing
        ...         try:
        ...             return parse_partial_response(response_data, response_type)
        ...         except ArrisParsingError:
        ...             # Fall back to defaults
        ...             logger.error(f"Complete parsing failure for {response_type}")
        ...             return get_default_response_structure(response_type)

    Data Validation and Schema Checking:
        Parsing errors can include schema validation:

        >>> def validate_response_schema(data, expected_schema, response_type):
        ...     missing_fields = []
        ...     invalid_fields = []
        ...
        ...     for field, field_type in expected_schema.items():
        ...         if field not in data:
        ...             missing_fields.append(field)
        ...         elif not isinstance(data[field], field_type):
        ...             invalid_fields.append({
        ...                 "field": field,
        ...                 "expected": field_type.__name__,
        ...                 "actual": type(data[field]).__name__
        ...             })
        ...
        ...     if missing_fields or invalid_fields:
        ...         raise ArrisParsingError(
        ...             f"Schema validation failed for {response_type}",
        ...             details={
        ...                 "response_type": response_type,
        ...                 "missing_fields": missing_fields,
        ...                 "invalid_fields": invalid_fields,
        ...                 "expected_schema": {k: v.__name__ for k, v in expected_schema.items()}
        ...             }
        ...         )

    Recovery and Adaptation Strategies:
        Parsing errors can guide adaptive parsing logic:

        >>> class AdaptiveParser:
        ...     def __init__(self):
        ...         self.parsing_strategies = ["strict", "lenient", "fallback"]
        ...         self.current_strategy = 0
        ...
        ...     def parse_with_adaptation(self, data, response_type):
        ...         for strategy in self.parsing_strategies[self.current_strategy:]:
        ...             try:
        ...                 return self.parse_with_strategy(data, response_type, strategy)
        ...             except ArrisParsingError as e:
        ...                 if strategy == self.parsing_strategies[-1]:
        ...                     # Exhausted all strategies
        ...                     e.details["adaptation_attempted"] = True
        ...                     e.details["strategies_tried"] = self.parsing_strategies
        ...                     raise
        ...
        ...                 # Try next strategy
        ...                 continue

    This parsing error exception enables robust error handling that can adapt
    to different modem firmware versions and response formats while providing
    detailed debugging information for compatibility issues.
    """


class ArrisConfigurationError(ArrisModemError):
    """
    Raised when configuration validation fails.

    This exception handles all issues related to invalid configuration parameters,
    missing required settings, parameter values outside valid ranges, and
    configuration conflicts. It's designed to catch configuration problems
    early in the process before they cause runtime failures.

    Configuration errors are typically permanent - they don't resolve with
    retry attempts and require user intervention to correct the configuration
    parameters. The exception provides detailed information about what
    configuration is invalid and what the valid options are.

    This exception is particularly important for providing clear feedback
    to users about how to correctly configure the client, making the library
    more user-friendly and reducing support burden.

    Common Scenarios:
        * Invalid timeout values (negative numbers, zero timeouts)
        * Port numbers outside valid range (1-65535)
        * Invalid IP addresses or hostnames
        * Conflicting configuration options
        * Missing required configuration parameters
        * Invalid retry counts or worker counts

    Attributes:
        message: Human-readable description of the configuration error
        details: Dictionary with configuration-specific context:
                - parameter: Name of the invalid parameter
                - value: The invalid value that was provided
                - valid_range: Description of valid values or range
                - suggestion: Recommended value or action
                - related_parameters: Other parameters that affect this one

    Examples:
        Configuration validation with helpful error messages:

        >>> try:
        ...     client = ArrisModemStatusClient(
        ...         password="test",
        ...         timeout=-5,  # Invalid negative timeout
        ...         max_retries=100  # Excessive retry count
        ...     )
        ... except ArrisConfigurationError as e:
        ...     print(f"Configuration error: {e}")
        ...
        ...     # Get specific parameter information
        ...     if e.details.get("parameter") == "timeout":
        ...         print(f"Valid timeout range: {e.details.get('valid_range')}")
        ...         print(f"Suggested value: {e.details.get('suggestion')}")

        Configuration validation function:

        >>> def validate_client_config(host, port, timeout, max_retries, max_workers):
        ...     errors = []
        ...
        ...     # Validate timeout
        ...     if timeout <= 0:
        ...         errors.append(ArrisConfigurationError(
        ...             "Timeout must be positive",
        ...             details={
        ...                 "parameter": "timeout",
        ...                 "value": timeout,
        ...                 "valid_range": "positive number (recommended: 5-30 seconds)",
        ...                 "suggestion": 10
        ...             }
        ...         ))
        ...
        ...     # Validate port range
        ...     if not (1 <= port <= 65535):
        ...         errors.append(ArrisConfigurationError(
        ...             "Port number out of valid range",
        ...             details={
        ...                 "parameter": "port",
        ...                 "value": port,
        ...                 "valid_range": "1-65535",
        ...                 "suggestion": 443
        ...             }
        ...         ))
        ...
        ...     # Validate retry count
        ...     if max_retries < 0 or max_retries > 10:
        ...         errors.append(ArrisConfigurationError(
        ...             "Max retries should be reasonable",
        ...             details={
        ...                 "parameter": "max_retries",
        ...                 "value": max_retries,
        ...                 "valid_range": "0-10",
        ...                 "suggestion": 3
        ...             }
        ...         ))
        ...
        ...     if errors:
        ...         # Combine multiple configuration errors
        ...         combined_message = f"Multiple configuration errors: {len(errors)} issues found"
        ...         combined_details = {
        ...             "error_count": len(errors),
        ...             "errors": [{"parameter": e.details.get("parameter"), "value": e.details.get("value")} for e in errors]
        ...         }
        ...         raise ArrisConfigurationError(combined_message, details=combined_details)

        Configuration builder with validation:

        >>> class ArrisClientConfigBuilder:
        ...     def __init__(self):
        ...         self.config = {}
        ...         self.validation_errors = []
        ...
        ...     def set_host(self, host: str):
        ...         if not host or not isinstance(host, str):
        ...             self.validation_errors.append(
        ...                 ArrisConfigurationError(
        ...                     "Host must be a non-empty string",
        ...                     details={"parameter": "host", "value": host}
        ...                 )
        ...             )
        ...         self.config["host"] = host
        ...         return self
        ...
        ...     def set_timeout(self, timeout: float):
        ...         if timeout <= 0:
        ...             self.validation_errors.append(
        ...                 ArrisConfigurationError(
        ...                     "Timeout must be positive",
        ...                     details={
        ...                         "parameter": "timeout",
        ...                         "value": timeout,
        ...                         "valid_range": "> 0 seconds"
        ...                     }
        ...                 )
        ...             )
        ...         self.config["timeout"] = timeout
        ...         return self
        ...
        ...     def build(self):
        ...         if self.validation_errors:
        ...             raise self.validation_errors[0]  # Raise first error
        ...         return ArrisModemStatusClient(**self.config)

    Integration with Argument Parsing:
        Configuration errors work with command-line argument validation:

        >>> def validate_cli_args(args):
        ...     try:
        ...         # Validate timeout argument
        ...         if args.timeout <= 0:
        ...             raise ArrisConfigurationError(
        ...                 "Timeout must be greater than 0",
        ...                 details={
        ...                     "parameter": "timeout",
        ...                     "value": args.timeout,
        ...                     "valid_range": "> 0",
        ...                     "suggestion": "Use a positive number like 10 or 30"
        ...                 }
        ...             )
        ...
        ...         # Validate port range
        ...         if not (1 <= args.port <= 65535):
        ...             raise ArrisConfigurationError(
        ...                 "Port must be between 1 and 65535",
        ...                 details={
        ...                     "parameter": "port",
        ...                     "value": args.port,
        ...                     "valid_range": "1-65535",
        ...                     "suggestion": "Use 443 for HTTPS or 80 for HTTP"
        ...                 }
        ...             )
        ...
        ...     except ArrisConfigurationError as e:
        ...         print(f"Configuration error: {e}", file=sys.stderr)
        ...         if e.details.get("suggestion"):
        ...             print(f"Suggestion: {e.details['suggestion']}", file=sys.stderr)
        ...         sys.exit(1)

    Environment-Based Configuration:
        Handle environment variable configuration errors:

        >>> def load_config_from_environment():
        ...     config = {}
        ...
        ...     # Load timeout from environment
        ...     timeout_str = os.environ.get("ARRIS_TIMEOUT")
        ...     if timeout_str:
        ...         try:
        ...             config["timeout"] = float(timeout_str)
        ...             if config["timeout"] <= 0:
        ...                 raise ValueError("Must be positive")
        ...         except ValueError as e:
        ...             raise ArrisConfigurationError(
        ...                 "Invalid ARRIS_TIMEOUT environment variable",
        ...                 details={
        ...                     "parameter": "ARRIS_TIMEOUT",
        ...                     "value": timeout_str,
        ...                     "valid_range": "positive number",
        ...                     "error": str(e)
        ...                 }
        ...             ) from e
        ...
        ...     return config

    Configuration Documentation and Help:
        Generate helpful configuration guidance:

        >>> def generate_configuration_help(error: ArrisConfigurationError):
        ...     help_text = [f"Configuration Error: {error.message}"]
        ...
        ...     if "parameter" in error.details:
        ...         param = error.details["parameter"]
        ...         help_text.append(f"Parameter: {param}")
        ...
        ...         if "value" in error.details:
        ...             help_text.append(f"Invalid value: {error.details['value']}")
        ...
        ...         if "valid_range" in error.details:
        ...             help_text.append(f"Valid range: {error.details['valid_range']}")
        ...
        ...         if "suggestion" in error.details:
        ...             help_text.append(f"Suggested value: {error.details['suggestion']}")
        ...
        ...     return "\n".join(help_text)

    This configuration error exception provides comprehensive support for
    validating user input and providing clear, actionable feedback about
    how to correct configuration problems.
    """


class ArrisOperationError(ArrisModemError):
    """
    Raised when a high-level modem operation fails.

    This exception represents failures at the operation level - when individual
    requests might succeed but the overall operation (like retrieving complete
    modem status) fails. It typically indicates that multiple underlying
    failures have occurred or that the operation couldn't be completed
    successfully despite retry attempts.

    Operation errors often represent the "final" failure after all retry
    mechanisms have been exhausted, making them important for understanding
    the overall reliability and success rate of modem operations.

    This exception provides context about what operation was attempted,
    how many underlying requests succeeded or failed, and what recovery
    strategies were attempted.

    Common Scenarios:
        * Complete status retrieval fails after some requests succeed
        * Authentication succeeds but subsequent operations fail
        * Partial data retrieved but not enough for meaningful status
        * All retry attempts exhausted for critical operations
        * Operation timeout exceeded despite individual request success

    Attributes:
        message: Human-readable description of the operation failure
        details: Dictionary with operation-specific context:
                - operation: Name of the high-level operation that failed
                - requests_attempted: Number of individual requests made
                - requests_successful: Number that succeeded
                - requests_failed: Number that failed
                - retry_attempts: Number of retry cycles attempted
                - partial_data: Whether some data was successfully retrieved
                - last_error: Details of the final error that caused failure

    Examples:
        Operation error handling with partial data recovery:

        >>> try:
        ...     status = client.get_status()
        ... except ArrisOperationError as e:
        ...     # Check if we got partial data
        ...     if e.details.get("partial_data"):
        ...         print("Got partial status data, continuing with limitations")
        ...         status = e.details.get("partial_status", {})
        ...     else:
        ...         print(f"Complete operation failure: {e}")
        ...
        ...         # Analyze failure pattern
        ...         success_rate = (e.details.get("requests_successful", 0) /
        ...                        e.details.get("requests_attempted", 1))
        ...         print(f"Success rate: {success_rate:.1%}")

        Operation retry with exponential backoff:

        >>> def retry_operation_with_backoff(operation_func, max_attempts=3):
        ...     for attempt in range(max_attempts):
        ...         try:
        ...             return operation_func()
        ...         except ArrisOperationError as e:
        ...             # Check if this was a final failure
        ...             if e.details.get("retry_attempts", 0) > 0:
        ...                 # Already retried internally, don't retry again
        ...                 e.details["external_retry_attempted"] = True
        ...                 raise
        ...
        ...             if attempt < max_attempts - 1:
        ...                 backoff_time = 2 ** attempt
        ...                 print(f"Operation failed, retrying in {backoff_time}s...")
        ...                 time.sleep(backoff_time)
        ...                 continue
        ...
        ...             # Final attempt failed
        ...             e.details["total_external_attempts"] = max_attempts
        ...             raise

        Operation health monitoring:

        >>> class OperationHealthMonitor:
        ...     def __init__(self):
        ...         self.operation_stats = {}
        ...
        ...     def record_operation_failure(self, error: ArrisOperationError):
        ...         operation = error.details.get("operation", "unknown")
        ...
        ...         if operation not in self.operation_stats:
        ...             self.operation_stats[operation] = {
        ...                 "total_attempts": 0,
        ...                 "failures": 0,
        ...                 "partial_successes": 0,
        ...                 "complete_failures": 0
        ...             }
        ...
        ...         stats = self.operation_stats[operation]
        ...         stats["total_attempts"] += 1
        ...         stats["failures"] += 1
        ...
        ...         if error.details.get("partial_data"):
        ...             stats["partial_successes"] += 1
        ...         else:
        ...             stats["complete_failures"] += 1
        ...
        ...     def get_operation_health(self, operation):
        ...         if operation not in self.operation_stats:
        ...             return {"status": "unknown", "reason": "no_data"}
        ...
        ...         stats = self.operation_stats[operation]
        ...         failure_rate = stats["failures"] / stats["total_attempts"]
        ...
        ...         if failure_rate > 0.5:
        ...             return {"status": "unhealthy", "failure_rate": failure_rate}
        ...         elif failure_rate > 0.1:
        ...             return {"status": "degraded", "failure_rate": failure_rate}
        ...         else:
        ...             return {"status": "healthy", "failure_rate": failure_rate}

    Integration with Status Retrieval:
        Operation errors in the context of status retrieval:

        >>> class StatusRetriever:
        ...     def get_comprehensive_status(self):
        ...         requests_attempted = 0
        ...         requests_successful = 0
        ...         partial_data = {}
        ...         last_error = None
        ...
        ...         # Attempt multiple data requests
        ...         request_types = ["software_info", "connection_info", "channel_data"]
        ...
        ...         for request_type in request_types:
        ...             requests_attempted += 1
        ...             try:
        ...                 data = self.make_request(request_type)
        ...                 partial_data[request_type] = data
        ...                 requests_successful += 1
        ...             except Exception as e:
        ...                 last_error = str(e)
        ...                 continue
        ...
        ...         # Check if we have enough data for a meaningful status
        ...         if requests_successful == 0:
        ...             raise ArrisOperationError(
        ...                 "Complete status retrieval failure - no data obtained",
        ...                 details={
        ...                     "operation": "get_comprehensive_status",
        ...                     "requests_attempted": requests_attempted,
        ...                     "requests_successful": requests_successful,
        ...                     "requests_failed": requests_attempted - requests_successful,
        ...                     "partial_data": False,
        ...                     "last_error": last_error
        ...                 }
        ...             )
        ...         elif requests_successful < len(request_types) / 2:
        ...             # Less than half succeeded - operation failure but with partial data
        ...             raise ArrisOperationError(
        ...                 f"Insufficient data retrieved - only {requests_successful}/{requests_attempted} requests succeeded",
        ...                 details={
        ...                     "operation": "get_comprehensive_status",
        ...                     "requests_attempted": requests_attempted,
        ...                     "requests_successful": requests_successful,
        ...                     "requests_failed": requests_attempted - requests_successful,
        ...                     "partial_data": True,
        ...                     "partial_status": partial_data,
        ...                     "last_error": last_error
        ...                 }
        ...             )
        ...
        ...         return self.build_status_from_partial_data(partial_data)

        Graceful degradation with operation errors:

        >>> def get_status_with_fallback():
        ...     try:
        ...         # Attempt full status retrieval
        ...         return client.get_status()
        ...     except ArrisOperationError as e:
        ...         if e.details.get("partial_data"):
        ...             # Use what we got
        ...             partial_status = e.details.get("partial_status", {})
        ...
        ...             # Fill in defaults for missing data
        ...             return enhance_partial_status_with_defaults(partial_status)
        ...         else:
        ...             # Complete failure - return minimal status
        ...             return get_minimal_fallback_status()

    Analysis and Debugging:
        Operation errors provide detailed analysis capabilities:

        >>> def analyze_operation_failure(error: ArrisOperationError):
        ...     analysis = {
        ...         "operation": error.details.get("operation"),
        ...         "success_rate": 0,
        ...         "failure_analysis": {},
        ...         "recommendations": []
        ...     }
        ...
        ...     attempted = error.details.get("requests_attempted", 0)
        ...     successful = error.details.get("requests_successful", 0)
        ...
        ...     if attempted > 0:
        ...         analysis["success_rate"] = successful / attempted
        ...
        ...     # Analyze failure patterns
        ...     if successful == 0:
        ...         analysis["failure_analysis"]["type"] = "complete_failure"
        ...         analysis["recommendations"].extend([
        ...             "Check network connectivity",
        ...             "Verify modem is responding",
        ...             "Check authentication credentials"
        ...         ])
        ...     elif analysis["success_rate"] < 0.5:
        ...         analysis["failure_analysis"]["type"] = "high_failure_rate"
        ...         analysis["recommendations"].extend([
        ...             "Check for intermittent connectivity issues",
        ...             "Consider increasing timeout values",
        ...             "Monitor for modem overload conditions"
        ...         ])
        ...
        ...     return analysis

    This operation error exception provides comprehensive context for high-level
    operation failures, enabling sophisticated error handling that can work
    with partial data and provide detailed analysis for debugging and monitoring.
    """


# Convenience function for wrapping standard exceptions
def wrap_connection_error(original_error: Exception, host: str, port: int) -> ArrisConnectionError:
    """
    Wrap a standard connection exception in ArrisConnectionError with detailed context.

    This utility function converts standard Python networking exceptions into
    the library's structured exception hierarchy, preserving the original error
    context while adding Arris-specific details and classification.

    The function analyzes the type of original exception to determine the most
    appropriate ArrisConnectionError subclass and provides structured details
    that aid in debugging and automated error handling.

    Args:
        original_error: The original networking exception that occurred
        host: Hostname or IP address that failed to connect
        port: Port number that failed to connect

    Returns:
        Appropriate ArrisConnectionError subclass with structured details

    Examples:
        Wrapping socket timeouts:

        >>> import socket
        >>> try:
        ...     sock = socket.create_connection(("unreachable.host", 443), timeout=5)
        ... except socket.timeout as e:
        ...     arris_error = wrap_connection_error(e, "unreachable.host", 443)
        ...     print(type(arris_error).__name__)  # "ArrisTimeoutError"
        ...     print(arris_error.details["timeout_type"])  # "connection"

        Wrapping connection refused errors:

        >>> try:
        ...     sock = socket.create_connection(("127.0.0.1", 12345))
        ... except ConnectionRefusedError as e:
        ...     arris_error = wrap_connection_error(e, "127.0.0.1", 12345)
        ...     print("web interface disabled" in str(arris_error))  # True

        Integration with request handling:

        >>> def make_http_request(host, port):
        ...     try:
        ...         return requests.get(f"https://{host}:{port}/", timeout=10)
        ...     except requests.exceptions.ConnectionError as e:
        ...         # Extract underlying socket error
        ...         if hasattr(e, '__cause__') and isinstance(e.__cause__, socket.timeout):
        ...             raise wrap_connection_error(e.__cause__, host, port) from e
        ...         else:
        ...             raise wrap_connection_error(e, host, port) from e

    Error Classification Logic:
        The function determines the appropriate exception type based on the original error:

        * **socket.timeout** → ArrisTimeoutError with timeout_type="connection"
        * **ConnectionRefusedError** → ArrisConnectionError with helpful message about web interface
        * **Other socket/network errors** → ArrisConnectionError with generic network failure message

    Structured Details:
        All wrapped exceptions include standardized details:

        >>> wrapped_error = wrap_connection_error(ConnectionRefusedError(), "192.168.1.1", 443)
        >>> expected_details = {
        ...     "host": "192.168.1.1",
        ...     "port": 443,
        ...     "error_type": "ConnectionRefusedError",
        ...     "original_error": "Connection refused"
        ... }
        >>> # Details are included for debugging and monitoring

    Context Preservation:
        The function preserves full error context through exception chaining:

        >>> try:
        ...     wrapped_error = wrap_connection_error(socket.timeout("Connection timed out"), "host", 443)
        ...     raise wrapped_error
        ... except ArrisTimeoutError as e:
        ...     # Original exception accessible via __cause__
        ...     original = e.__cause__
        ...     print(type(original).__name__)  # "timeout"

    Monitoring Integration:
        Wrapped exceptions provide structured data for monitoring:

        >>> def handle_connection_error(error):
        ...     if isinstance(error, ArrisTimeoutError):
        ...         metrics.increment('connection_timeouts', tags=[
        ...             f'host:{error.details["host"]}',
        ...             f'timeout_type:{error.details.get("timeout_type", "unknown")}'
        ...         ])
        ...     elif isinstance(error, ArrisConnectionError):
        ...         error_type = error.details.get("error_type", "unknown")
        ...         metrics.increment(f'connection_errors.{error_type}')

    This wrapper function provides a clean, consistent way to convert standard
    networking exceptions into the library's structured exception hierarchy
    while preserving all relevant context for debugging and monitoring.
    """
    import socket

    message = f"Failed to connect to {host}:{port}"

    # Determine more specific error type and create appropriate exception
    if isinstance(original_error, socket.timeout):
        return ArrisTimeoutError(
            f"Connection to {host}:{port} timed out",
            details={
                "host": host,
                "port": port,
                "timeout_type": "connection",
                "original_error": str(original_error),
            },
        )

    if isinstance(original_error, ConnectionRefusedError):
        message = f"Connection refused by {host}:{port} - modem may be offline or web interface disabled"

    return ArrisConnectionError(
        message,
        details={
            "host": host,
            "port": port,
            "error_type": type(original_error).__name__,
            "original_error": str(original_error),
        },
    )


# Export all exceptions
__all__ = [
    "ArrisAuthenticationError",
    "ArrisConfigurationError",
    "ArrisConnectionError",
    "ArrisHTTPError",
    "ArrisModemError",
    "ArrisOperationError",
    "ArrisParsingError",
    "ArrisTimeoutError",
    "wrap_connection_error",
]
