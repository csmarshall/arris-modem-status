"""
Custom exceptions for Arris Modem Status Client.

This module defines all custom exceptions used throughout the arris-modem-status
library. All exceptions inherit from ArrisModemError for easy catching of
library-specific errors.

Example usage:
    try:
        client = ArrisModemStatusClient(password="wrong")
        client.authenticate()
    except ArrisAuthenticationError as e:
        print(f"Authentication failed: {e}")
    except ArrisModemError as e:
        print(f"Arris modem error: {e}")

Author: Charles Marshall
License: MIT
"""

from typing import Any, Optional


class ArrisModemError(Exception):
    """
    Base exception for all Arris Modem Status Client errors.

    This is the base class for all exceptions raised by the arris-modem-status
    library. Catching this exception will catch all library-specific errors.

    All exceptions include contextual details to help with debugging and
    monitoring integration.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context

    Examples:
        Catching all library errors:

        >>> try:
        ...     client = ArrisModemStatusClient(password="wrong")
        ...     client.authenticate()
        ... except ArrisModemError as e:
        ...     print(f"Arris error: {e}")
        ...     if e.details:
        ...         print(f"Details: {e.details}")

        Specific error handling:

        >>> try:
        ...     status = client.get_status()
        ... except ArrisAuthenticationError:
        ...     print("Check your password")
        ... except ArrisConnectionError:
        ...     print("Check network connectivity")
        ... except ArrisModemError as e:
        ...     print(f"Other modem error: {e}")
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """
        Initialize ArrisModemError.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ArrisAuthenticationError(ArrisModemError):
    """
    Raised when authentication with the modem fails.

    This exception is raised when:
    - Invalid credentials are provided
    - Authentication challenge fails
    - Login response indicates failure
    - Authentication tokens cannot be generated

    Attributes:
        message: Human-readable error message
        details: May include 'phase' (challenge/login), 'status_code', etc.
    """


class ArrisConnectionError(ArrisModemError):
    """
    Raised when connection to the modem fails.

    This exception is raised when:
    - Network connection cannot be established
    - Modem is unreachable
    - Socket errors occur
    - SSL/TLS handshake fails

    Attributes:
        message: Human-readable error message
        details: May include 'host', 'port', 'timeout', 'original_error'
    """


class ArrisTimeoutError(ArrisConnectionError):
    """
    Raised when a timeout occurs communicating with the modem.

    This is a specific type of connection error that occurs when:
    - Connection timeout is exceeded
    - Read timeout is exceeded
    - Overall operation timeout is exceeded

    Attributes:
        message: Human-readable error message
        details: May include 'timeout_type', 'timeout_value', 'operation'
    """


class ArrisHTTPError(ArrisModemError):
    """
    Raised when HTTP-level errors occur.

    This exception is raised when:
    - HTTP status codes indicate errors (4xx, 5xx)
    - HTTP parsing fails
    - Invalid HTTP responses are received

    Attributes:
        message: Human-readable error message
        details: May include 'status_code', 'response_body', 'headers'
        status_code: HTTP status code if available
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize ArrisHTTPError.

        Args:
            message: Human-readable error message
            status_code: HTTP status code if available
            details: Optional dictionary with additional error context
        """
        super().__init__(message, details)
        self.status_code = status_code
        if status_code and self.details is not None:
            self.details["status_code"] = status_code


class ArrisParsingError(ArrisModemError):
    """
    Raised when parsing modem responses fails.

    This exception is raised when:
    - JSON parsing fails
    - Channel data parsing fails
    - Response structure is unexpected
    - Data validation fails

    Attributes:
        message: Human-readable error message
        details: May include 'response_type', 'raw_data', 'parse_error'
    """


class ArrisConfigurationError(ArrisModemError):
    """
    Raised when configuration validation fails.

    This exception is raised when:
    - Invalid configuration parameters are provided
    - Required parameters are missing
    - Parameter values are out of valid range

    Attributes:
        message: Human-readable error message
        details: May include 'parameter', 'value', 'valid_range'
    """


class ArrisOperationError(ArrisModemError):
    """
    Raised when a modem operation fails.

    This exception is raised when:
    - Status retrieval fails after retries
    - Required operations cannot be completed
    - Modem returns error responses

    Attributes:
        message: Human-readable error message
        details: May include 'operation', 'attempts', 'last_error'
    """


# Convenience function for wrapping standard exceptions
def wrap_connection_error(original_error: Exception, host: str, port: int) -> ArrisConnectionError:
    """
    Wrap a standard connection exception in ArrisConnectionError.

    Args:
        original_error: The original exception
        host: Host that failed to connect
        port: Port that failed to connect

    Returns:
        ArrisConnectionError with context
    """
    import socket

    message = f"Failed to connect to {host}:{port}"

    # Determine more specific error type
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
