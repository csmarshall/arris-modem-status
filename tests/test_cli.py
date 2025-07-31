"""
Tests for the Arris Modem Status CLI.

This module tests the CLI package with its modular structure.
Fixed version that uses the refactored testable structure.
"""

import argparse
import json
import time
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

# Now we can import both the module and the function
from arris_modem_status.cli.args import create_parser, parse_args, validate_args
from arris_modem_status.cli.connectivity import (
    get_optimal_timeouts,
    print_connectivity_troubleshooting,
    quick_connectivity_check,
)
from arris_modem_status.cli.formatters import (
    format_channel_data_for_display,
    format_json_output,
    print_error_suggestions,
    print_json_output,
    print_summary_to_stderr,
)
from arris_modem_status.cli.logging_setup import get_logger, setup_logging
from arris_modem_status.cli.main import create_client, main, perform_connectivity_check, process_modem_status
from arris_modem_status.exceptions import (
    ArrisAuthenticationError,
    ArrisConfigurationError,
    ArrisConnectionError,
    ArrisModemError,
    ArrisOperationError,
    ArrisTimeoutError,
)


@pytest.mark.unit
@pytest.mark.cli
class TestCLIArgs:
    """Test argument parsing module."""

    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog is not None

    def test_parse_required_args(self):
        """Test parsing with required arguments."""
        parser = create_parser()
        args = parser.parse_args(["--password", "test123"])

        assert args.password == "test123"
        assert args.host == "192.168.100.1"  # default
        assert args.port == 443  # default
        assert args.username == "admin"  # default
        assert args.parallel is False  # default

    def test_parse_all_args(self):
        """Test parsing with all arguments."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "--password",
                "test123",
                "--host",
                "192.168.1.1",
                "--port",
                "8443",
                "--username",
                "user",
                "--debug",
                "--quiet",
                "--timeout",
                "60",
                "--workers",
                "4",
                "--retries",
                "5",
                "--serial",  # deprecated but still parsed
                "--parallel",  # new flag
                "--quick-check",
            ]
        )

        assert args.password == "test123"
        assert args.host == "192.168.1.1"
        assert args.port == 8443
        assert args.username == "user"
        assert args.debug is True
        assert args.quiet is True
        assert args.timeout == 60
        assert args.workers == 4
        assert args.retries == 5
        assert args.serial is True  # deprecated
        assert args.parallel is True  # new flag
        assert args.quick_check is True

    def test_validate_args_valid(self):
        """Test argument validation with valid args."""
        args = argparse.Namespace(timeout=30, workers=2, retries=3, port=443, parallel=False)

        # Should not raise
        validate_args(args)

    def test_validate_args_invalid_timeout(self):
        """Test argument validation with invalid timeout."""
        args = argparse.Namespace(timeout=0, workers=2, retries=3, port=443, parallel=False)

        with pytest.raises(ArrisConfigurationError) as exc_info:
            validate_args(args)

        assert "Timeout must be greater than 0" in str(exc_info.value)
        assert exc_info.value.details["parameter"] == "timeout"

    def test_validate_args_invalid_workers(self):
        """Test argument validation with invalid workers."""
        args = argparse.Namespace(timeout=30, workers=0, retries=3, port=443, parallel=False)

        with pytest.raises(ArrisConfigurationError) as exc_info:
            validate_args(args)

        assert "Workers must be at least 1" in str(exc_info.value)
        assert exc_info.value.details["parameter"] == "workers"

    def test_validate_args_invalid_port(self):
        """Test argument validation with invalid port."""
        args = argparse.Namespace(timeout=30, workers=2, retries=3, port=70000, parallel=False)

        with pytest.raises(ArrisConfigurationError) as exc_info:
            validate_args(args)

        assert "Port must be between 1 and 65535" in str(exc_info.value)
        assert exc_info.value.details["parameter"] == "port"
        assert exc_info.value.details["value"] == 70000

    @patch("sys.argv", ["arris-modem-status", "--password", "test123"])
    def test_parse_args_integration(self):
        """Test parse_args function with command line arguments."""
        args = parse_args()
        assert args.password == "test123"
        assert args.host == "192.168.100.1"
        assert args.parallel is False  # default


@pytest.mark.unit
@pytest.mark.cli
class TestCLIConnectivity:
    """Test connectivity module."""

    @patch("socket.create_connection")
    def test_quick_connectivity_check_success(self, mock_create_connection):
        """Test successful connectivity check."""
        mock_socket = MagicMock()
        mock_create_connection.return_value.__enter__.return_value = mock_socket

        is_reachable, error_msg = quick_connectivity_check("192.168.100.1", 443, 2.0)

        assert is_reachable is True
        assert error_msg is None
        mock_create_connection.assert_called_once_with(("192.168.100.1", 443), timeout=2.0)

    @patch("socket.create_connection")
    def test_quick_connectivity_check_timeout(self, mock_create_connection):
        """Test connectivity check with timeout."""
        import socket

        mock_create_connection.side_effect = socket.timeout("Connection timeout")

        is_reachable, error_msg = quick_connectivity_check("192.168.100.1", 443, 2.0)

        assert is_reachable is False
        assert "timeout" in error_msg
        assert "192.168.100.1:443" in error_msg

    @patch("socket.create_connection")
    def test_quick_connectivity_check_refused(self, mock_create_connection):
        """Test connectivity check with connection refused."""
        mock_create_connection.side_effect = ConnectionRefusedError("Connection refused")

        is_reachable, error_msg = quick_connectivity_check("192.168.100.1", 443, 2.0)

        assert is_reachable is False
        assert "refused" in error_msg

    @patch("socket.create_connection")
    def test_quick_connectivity_check_dns_error(self, mock_create_connection):
        """Test connectivity check with DNS error."""
        import socket

        mock_create_connection.side_effect = socket.gaierror("Name or service not known")

        is_reachable, error_msg = quick_connectivity_check("invalid.host", 443, 2.0)

        assert is_reachable is False
        assert "DNS" in error_msg

    def test_get_optimal_timeouts_local(self):
        """Test optimal timeout calculation for local addresses."""
        local_addresses = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "localhost",
            "127.0.0.1",
        ]

        for addr in local_addresses:
            connect_timeout, read_timeout = get_optimal_timeouts(addr)
            assert connect_timeout == 2
            assert read_timeout == 8

    def test_get_optimal_timeouts_remote(self):
        """Test optimal timeout calculation for remote addresses."""
        remote_addresses = ["8.8.8.8", "example.com", "1.1.1.1"]

        for addr in remote_addresses:
            connect_timeout, read_timeout = get_optimal_timeouts(addr)
            assert connect_timeout == 5
            assert read_timeout == 15

    def test_print_connectivity_troubleshooting(self, capsys):
        """Test troubleshooting suggestions output."""
        print_connectivity_troubleshooting("192.168.100.1", 443, "Connection timeout")

        captured = capsys.readouterr()
        assert "TROUBLESHOOTING" in captured.err
        assert "timeout" in captured.err
        assert "ping 192.168.100.1" in captured.err


@pytest.mark.unit
@pytest.mark.cli
class TestCLIFormatters:
    """Test formatting module."""

    def test_format_channel_data_for_display(self):
        """Test channel data formatting."""
        # Create mock channel objects
        mock_channel = Mock()
        mock_channel.channel_id = "1"
        mock_channel.frequency = "549000000 Hz"
        mock_channel.power = "0.6 dBmV"
        mock_channel.snr = "39.0 dB"
        mock_channel.modulation = "256QAM"
        mock_channel.lock_status = "Locked"
        mock_channel.corrected_errors = "15"
        mock_channel.uncorrected_errors = "0"
        mock_channel.channel_type = "downstream"

        status = {
            "downstream_channels": [mock_channel],
            "upstream_channels": [],
        }

        formatted = format_channel_data_for_display(status)

        assert len(formatted["downstream_channels"]) == 1
        channel_dict = formatted["downstream_channels"][0]
        assert channel_dict["channel_id"] == "1"
        assert channel_dict["frequency"] == "549000000 Hz"
        assert channel_dict["power"] == "0.6 dBmV"

    def test_format_json_output(self):
        """Test JSON output formatting."""
        status = {"model_name": "S34", "internet_status": "Connected"}

        args = argparse.Namespace(
            host="192.168.100.1",
            workers=2,
            retries=3,
            timeout=30,
            parallel=False,  # Changed from serial to parallel
        )

        json_output = format_json_output(status, args, 1.5, True)

        assert json_output["model_name"] == "S34"
        assert json_output["internet_status"] == "Connected"
        assert json_output["query_host"] == "192.168.100.1"
        assert json_output["elapsed_time"] == 1.5
        assert json_output["configuration"]["max_workers"] == 2
        assert json_output["configuration"]["concurrent_mode"] is False  # Based on parallel=False
        assert json_output["configuration"]["quick_check_performed"] is True

    def test_print_summary_to_stderr(self, capsys):
        """Test summary output to stderr."""
        mock_channel = Mock()
        mock_channel.channel_id = "1"
        mock_channel.frequency = "549000000 Hz"
        mock_channel.power = "0.6 dBmV"
        mock_channel.snr = "39.0 dB"
        mock_channel.corrected_errors = "15"
        mock_channel.uncorrected_errors = "0"

        status = {
            "model_name": "S34",
            "firmware_version": "AT01.01.010.042324_S3.04.735",
            "hardware_version": "1.0",
            "system_uptime": "7 days 14:23:56",
            "internet_status": "Connected",
            "connection_status": "Allowed",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "downstream_channels": [mock_channel],
            "upstream_channels": [],
            "channel_data_available": True,
        }

        print_summary_to_stderr(status)

        captured = capsys.readouterr()
        assert "ARRIS MODEM STATUS SUMMARY" in captured.err
        assert "Model: S34" in captured.err
        assert "Firmware: AT01.01.010.042324_S3.04.735" in captured.err
        assert "Uptime: 7 days 14:23:56" in captured.err
        assert "Internet: Connected" in captured.err
        assert "MAC Address: AA:BB:CC:DD:EE:FF" in captured.err

    def test_print_json_output(self, capsys):
        """Test JSON output to stdout."""
        data = {"test": "value", "number": 42}

        print_json_output(data)

        captured = capsys.readouterr()
        output_data = json.loads(captured.out)
        assert output_data["test"] == "value"
        assert output_data["number"] == 42

    def test_print_error_suggestions_normal(self, capsys):
        """Test error suggestions in normal mode."""
        print_error_suggestions(debug=False)

        captured = capsys.readouterr()
        assert "Troubleshooting suggestions:" in captured.err
        assert "Try with --debug" in captured.err

    @patch("traceback.print_exc")
    def test_print_error_suggestions_debug(self, mock_traceback, capsys):
        """Test error suggestions in debug mode."""
        print_error_suggestions(debug=True)

        mock_traceback.assert_called_once()


@pytest.mark.unit
@pytest.mark.cli
class TestCLILogging:
    """Test logging setup module."""

    def test_setup_logging_info_level(self):
        """Test logging setup with info level."""
        import logging

        setup_logging(debug=False)

        # Check root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

        # Check third-party loggers are set to WARNING
        urllib3_logger = logging.getLogger("urllib3")
        assert urllib3_logger.level == logging.WARNING

    def test_setup_logging_debug_level(self):
        """Test logging setup with debug level."""
        import logging

        setup_logging(debug=True)

        # Check root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"


@pytest.mark.integration
@pytest.mark.cli
class TestCLIMainIntegration:
    """Test main orchestration module with the new testable structure."""

    def test_main_success(self):
        """Test successful main execution using the new testable structure."""
        # Create a proper mock channel object
        mock_channel = Mock()
        mock_channel.channel_id = "1"
        mock_channel.frequency = "549000000 Hz"
        mock_channel.power = "0.6 dBmV"
        mock_channel.snr = "39.0 dB"
        mock_channel.modulation = "256QAM"
        mock_channel.lock_status = "Locked"
        mock_channel.corrected_errors = "15"
        mock_channel.uncorrected_errors = "0"
        mock_channel.channel_type = "downstream"

        # Create the return value for get_status
        mock_status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [mock_channel],
            "upstream_channels": [],
        }

        # Create a mock client class
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance
        mock_client_instance.get_status.return_value = mock_status

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            # Capture output
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            with patch("sys.stdout", stdout_capture), patch("sys.stderr", stderr_capture):
                # Execute main with our mock client class
                result = main(client_class=MockClientClass)

                # On success, main() returns None
                assert result is None

            # Check JSON output
            output = stdout_capture.getvalue()
            json_data = json.loads(output)

            assert json_data["model_name"] == "S34"
            assert json_data["internet_status"] == "Connected"
            assert json_data["query_host"] == "192.168.100.1"

    def test_main_connectivity_check_failed(self):
        """Test main execution with failed connectivity check."""
        with (
            patch("sys.argv", ["arris-modem-status", "--password", "test123", "--quick-check"]),
            patch("arris_modem_status.cli.main.quick_connectivity_check") as mock_quick_check,
        ):
            # Mock the connectivity check to fail
            mock_quick_check.return_value = (False, "Connection timeout")

            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                # Execute main - no need to pass client_class since connectivity fails first
                result = main()

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Connection timeout" in stderr_output

    def test_main_client_error(self):
        """Test main execution with client error."""
        # Create a mock client class that raises an exception
        MockClientClass = Mock()
        MockClientClass.side_effect = Exception("Connection failed")

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Connection failed" in stderr_output

    def test_main_quiet_mode(self):
        """Test main execution in quiet mode."""
        mock_status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        # Create a mock client class
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance
        mock_client_instance.get_status.return_value = mock_status

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123", "--quiet"]):
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            with patch("sys.stdout", stdout_capture), patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)
                assert result is None

            # Check that no summary was printed to stderr
            stderr_output = stderr_capture.getvalue()
            assert "ARRIS MODEM STATUS SUMMARY" not in stderr_output

            # But JSON should still be on stdout
            stdout_output = stdout_capture.getvalue()
            json_data = json.loads(stdout_output)
            assert json_data["model_name"] == "S34"

    def test_main_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        # Create a mock client class that raises KeyboardInterrupt
        MockClientClass = Mock()
        MockClientClass.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Operation cancelled by user" in stderr_output

    def test_main_serial_mode(self):
        """Test main execution in serial mode (deprecated flag)."""
        mock_status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        # Create a mock client class
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance
        mock_client_instance.get_status.return_value = mock_status

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123", "--serial"]):
            with patch("sys.stdout", StringIO()):
                result = main(client_class=MockClientClass)
                assert result is None

            # Verify client was created with concurrent=False (serial is ignored)
            MockClientClass.assert_called_once()
            call_kwargs = MockClientClass.call_args[1]
            assert call_kwargs["concurrent"] is False  # Still False because --parallel not used

    def test_main_parallel_mode(self):
        """Test main execution in parallel mode."""
        mock_status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        # Create a mock client class
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance
        mock_client_instance.get_status.return_value = mock_status

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123", "--parallel"]):
            with patch("sys.stdout", StringIO()):
                result = main(client_class=MockClientClass)
                assert result is None

            # Verify client was created with concurrent=True
            MockClientClass.assert_called_once()
            call_kwargs = MockClientClass.call_args[1]
            assert call_kwargs["concurrent"] is True  # True because --parallel used

    def test_main_configuration_error(self):
        """Test main execution with configuration error."""
        with patch("sys.argv", ["arris-modem-status", "--password", "test123", "--port", "0"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main()

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Configuration error" in stderr_output
            assert "Run with --help" in stderr_output

    def test_main_authentication_error(self):
        """Test main execution with authentication error."""
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise AuthenticationError
        mock_client_instance.get_status.side_effect = ArrisAuthenticationError(
            "Invalid password", details={"username": "admin"}
        )

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "wrong_password"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Authentication error" in stderr_output
            assert "verify your password" in stderr_output

    def test_main_timeout_error(self):
        """Test main execution with timeout error."""
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise TimeoutError
        mock_client_instance.get_status.side_effect = ArrisTimeoutError("Request timed out", details={"timeout": 30})

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Timeout error" in stderr_output
            assert "--timeout" in stderr_output

    def test_main_connection_error(self):
        """Test main execution with connection error."""
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise ConnectionError
        mock_client_instance.get_status.side_effect = ArrisConnectionError(
            "Cannot reach modem", details={"host": "192.168.100.1", "port": 443}
        )

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Connection error" in stderr_output

    def test_main_operation_error_concurrent(self):
        """Test main execution with operation error in concurrent mode."""
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise OperationError
        mock_client_instance.get_status.side_effect = ArrisOperationError("No data received", details={"attempts": 3})

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123", "--parallel"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Operation error" in stderr_output
            assert "removing --parallel flag" in stderr_output

    def test_main_operation_error_serial(self):
        """Test main execution with operation error in serial mode."""
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise OperationError
        mock_client_instance.get_status.side_effect = ArrisOperationError("No data received", details={"attempts": 3})

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Operation error" in stderr_output
            assert "--retries" in stderr_output  # Different message for serial mode

    def test_main_generic_modem_error(self):
        """Test main execution with generic ArrisModemError."""
        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise generic ArrisModemError
        mock_client_instance.get_status.side_effect = ArrisModemError("Something went wrong")

        # Setup context manager
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            assert "Something went wrong" in stderr_output
            assert "Troubleshooting suggestions" in stderr_output


@pytest.mark.unit
@pytest.mark.cli
class TestCLIHelperFunctions:
    """Test the new helper functions."""

    def test_create_client(self):
        """Test create_client factory function."""
        args = argparse.Namespace(
            host="192.168.100.1",
            port=443,
            username="admin",
            password="test123",
            parallel=False,  # Changed from serial to parallel
            workers=2,
            retries=3,
            timeout=30,
        )

        MockClientClass = Mock()
        mock_instance = Mock()
        MockClientClass.return_value = mock_instance

        client = create_client(args, client_class=MockClientClass)

        assert client == mock_instance
        MockClientClass.assert_called_once_with(
            host="192.168.100.1",
            port=443,
            username="admin",
            password="test123",
            concurrent=False,  # Based on parallel=False
            max_workers=2,
            max_retries=3,
            timeout=(2, 8),  # Based on local IP
        )

    def test_perform_connectivity_check_not_requested(self):
        """Test perform_connectivity_check when not requested."""
        args = argparse.Namespace(quick_check=False)

        result = perform_connectivity_check(args)
        assert result is True

    def test_perform_connectivity_check_success(self):
        """Test perform_connectivity_check when successful."""
        args = argparse.Namespace(quick_check=True, host="192.168.100.1", port=443)

        with patch("arris_modem_status.cli.main.quick_connectivity_check") as mock_check:
            mock_check.return_value = (True, None)

            result = perform_connectivity_check(args)
            assert result is True

    def test_perform_connectivity_check_failure(self):
        """Test perform_connectivity_check when it fails."""
        args = argparse.Namespace(quick_check=True, host="192.168.100.1", port=443)

        with patch("arris_modem_status.cli.main.quick_connectivity_check") as mock_check:
            mock_check.return_value = (False, "Connection refused")

            with patch("sys.stderr", StringIO()):
                result = perform_connectivity_check(args)
                assert result is False

    def test_process_modem_status(self):
        """Test process_modem_status function."""
        # Create mock client
        mock_client = MagicMock()
        mock_status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }
        mock_client.get_status.return_value = mock_status
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        # Create args
        args = argparse.Namespace(
            host="192.168.100.1",
            port=443,
            quiet=False,
            workers=2,
            retries=3,
            timeout=30,
            parallel=False,  # Changed from serial to parallel
        )

        # Capture output
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with patch("sys.stdout", stdout_capture), patch("sys.stderr", stderr_capture):
            process_modem_status(mock_client, args, time.time(), True)

        # Check that summary was printed to stderr
        stderr_output = stderr_capture.getvalue()
        assert "ARRIS MODEM STATUS SUMMARY" in stderr_output

        # Check that JSON was printed to stdout
        stdout_output = stdout_capture.getvalue()
        json_data = json.loads(stdout_output)
        assert json_data["model_name"] == "S34"

    def test_create_client_default_class(self):
        """Test create_client with default client class."""
        args = argparse.Namespace(
            host="192.168.100.1",
            port=443,
            username="admin",
            password="test123",
            parallel=False,  # Changed from serial to parallel
            workers=2,
            retries=3,
            timeout=30,
        )

        # Patch the ArrisModemStatusClient at the module level
        with patch("arris_modem_status.cli.main.ArrisModemStatusClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            client = create_client(args)

            assert client == mock_instance
            mock_client_class.assert_called_once()

    def test_main_with_parallel_debug_quiet_options(self):
        """Test main with combination of options."""
        mock_status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        MockClientClass = Mock()
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance
        mock_client_instance.get_status.return_value = mock_status
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None

        with patch("sys.argv", ["arris-modem-status", "--password", "test123", "--parallel", "--debug", "--quiet"]):
            stdout_capture = StringIO()
            stderr_capture = StringIO()

            with patch("sys.stdout", stdout_capture), patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)
                assert result is None

            # In quiet mode, no summary should be printed
            stderr_output = stderr_capture.getvalue()
            assert "ARRIS MODEM STATUS SUMMARY" not in stderr_output

            # Verify parallel mode was used
            call_kwargs = MockClientClass.call_args[1]
            assert call_kwargs["concurrent"] is True  # True because --parallel flag
