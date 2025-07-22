"""
Tests for the Arris Modem Status CLI.

This module tests the CLI package with its modular structure.
"""

import argparse
import json
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the module to ensure proper patching
import arris_modem_status.cli.main
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
from arris_modem_status.cli.main import main


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
                "--serial",
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
        assert args.serial is True
        assert args.quick_check is True

    def test_validate_args_valid(self):
        """Test argument validation with valid args."""
        args = argparse.Namespace(timeout=30, workers=2, retries=3, port=443)

        # Should not raise
        validate_args(args)

    def test_validate_args_invalid_timeout(self):
        """Test argument validation with invalid timeout."""
        args = argparse.Namespace(timeout=0, workers=2, retries=3, port=443)

        with pytest.raises(ValueError, match="Timeout must be greater than 0"):
            validate_args(args)

    def test_validate_args_invalid_workers(self):
        """Test argument validation with invalid workers."""
        args = argparse.Namespace(timeout=30, workers=0, retries=3, port=443)

        with pytest.raises(ValueError, match="Workers must be at least 1"):
            validate_args(args)

    def test_validate_args_invalid_port(self):
        """Test argument validation with invalid port."""
        args = argparse.Namespace(timeout=30, workers=2, retries=3, port=70000)

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            validate_args(args)

    @patch("sys.argv", ["arris-modem-status", "--password", "test123"])
    def test_parse_args_integration(self):
        """Test parse_args function with command line arguments."""
        args = parse_args()
        assert args.password == "test123"
        assert args.host == "192.168.100.1"


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
        # socket.create_connection is called with timeout as keyword argument
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
            serial=False,
        )

        json_output = format_json_output(status, args, 1.5, True)

        assert json_output["model_name"] == "S34"
        assert json_output["internet_status"] == "Connected"
        assert json_output["query_host"] == "192.168.100.1"
        assert json_output["elapsed_time"] == 1.5
        assert json_output["configuration"]["max_workers"] == 2
        assert json_output["configuration"]["concurrent_mode"] is True
        assert json_output["configuration"]["quick_check_performed"] is True

    def test_print_summary_to_stderr(self, capsys):
        """Test summary output to stderr."""
        mock_channel = Mock()
        mock_channel.channel_id = "1"
        mock_channel.frequency = "549000000 Hz"
        mock_channel.power = "0.6 dBmV"
        mock_channel.snr = "39.0 dB"

        status = {
            "model_name": "S34",
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
        assert "Internet Status: Connected" in captured.err
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
    """Test main orchestration module."""

    @patch("arris_modem_status.cli.main.ArrisModemStatusClient")
    @patch("sys.argv", ["arris-modem-status", "--password", "test123"])
    def test_main_success(self, mock_client_class):
        """Test successful main execution."""
        # Mock client instance
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock get_status to return valid data
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

        mock_client.get_status.return_value = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [mock_channel],
            "upstream_channels": [],
        }

        # Capture stdout
        stdout_capture = StringIO()

        with patch("sys.stdout", stdout_capture):
            # Should exit normally (code 0)
            try:
                main()
            except SystemExit as e:
                assert e.code is None or e.code == 0

        # Check JSON output
        output = stdout_capture.getvalue()
        json_data = json.loads(output)

        assert json_data["model_name"] == "S34"
        assert json_data["internet_status"] == "Connected"
        assert json_data["query_host"] == "192.168.100.1"

    @patch("arris_modem_status.cli.main.ArrisModemStatusClient")
    @patch(
        "sys.argv",
        ["arris-modem-status", "--password", "test123", "--quick-check"],
    )
    @patch("arris_modem_status.cli.connectivity.quick_connectivity_check")
    def test_main_connectivity_check_failed(self, mock_quick_check, mock_client_class):
        """Test main execution with failed connectivity check."""
        # Mock connectivity check to fail
        mock_quick_check.return_value = (False, "Connection timeout")

        stderr_capture = StringIO()

        with patch("sys.stderr", stderr_capture):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        stderr_output = stderr_capture.getvalue()
        assert "Connection timeout" in stderr_output

        # Client should not be created if connectivity check fails
        mock_client_class.assert_not_called()

    @patch("arris_modem_status.cli.main.ArrisModemStatusClient")
    @patch("sys.argv", ["arris-modem-status", "--password", "test123"])
    def test_main_client_error(self, mock_client_class):
        """Test main execution with client error."""
        # Mock client to raise exception
        mock_client_class.side_effect = Exception("Connection failed")

        stderr_capture = StringIO()

        with patch("sys.stderr", stderr_capture):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        stderr_output = stderr_capture.getvalue()
        assert "Connection failed" in stderr_output
        assert "Troubleshooting suggestions:" in stderr_output

    @patch("arris_modem_status.cli.main.ArrisModemStatusClient")
    @patch("sys.argv", ["arris-modem-status", "--password", "test123", "--quiet"])
    def test_main_quiet_mode(self, mock_client_class):
        """Test main execution in quiet mode."""
        # Mock client instance
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.get_status.return_value = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with patch("sys.stdout", stdout_capture), patch("sys.stderr", stderr_capture):
            try:
                main()
            except SystemExit:
                pass

        # Check that no summary was printed to stderr
        stderr_output = stderr_capture.getvalue()
        assert "ARRIS MODEM STATUS SUMMARY" not in stderr_output

        # But JSON should still be on stdout
        stdout_output = stdout_capture.getvalue()
        json_data = json.loads(stdout_output)
        assert json_data["model_name"] == "S34"

    @patch("sys.argv", ["arris-modem-status", "--password", "test123"])
    def test_main_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        # Patch ArrisModemStatusClient to raise KeyboardInterrupt during initialization
        with patch("arris_modem_status.cli.main.ArrisModemStatusClient") as mock_client_class:
            mock_client_class.side_effect = KeyboardInterrupt()

            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 1
            stderr_output = stderr_capture.getvalue()
            assert "cancelled by user" in stderr_output

    @patch("arris_modem_status.cli.main.ArrisModemStatusClient")
    @patch("sys.argv", ["arris-modem-status", "--password", "test123", "--serial"])
    def test_main_serial_mode(self, mock_client_class):
        """Test main execution in serial mode."""
        # Verify that client is created with concurrent=False
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_status.return_value = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        with patch("sys.stdout", StringIO()):
            try:
                main()
            except SystemExit:
                pass

        # Check that client was created with concurrent=False
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["concurrent"] is False
