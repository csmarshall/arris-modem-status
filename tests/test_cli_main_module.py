"""
Tests for the CLI main module.

This module tests the main orchestration functionality of the Arris
Modem Status CLI.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Use the refactored testable import structure
from arris_modem_status.cli.main import main
from arris_modem_status.exceptions import ArrisModemError


@pytest.mark.unit
@pytest.mark.cli
class TestCLIMainModule:
    """Test CLI main module functionality."""

    def test_main_function_exists(self):
        """Test that main function is properly imported."""
        assert callable(main)

    def test_main_keyboard_interrupt_handling(self):
        """Test that KeyboardInterrupt is handled gracefully."""
        # Create a mock client class that raises KeyboardInterrupt
        MockClientClass = Mock()
        MockClientClass.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            result = main(client_class=MockClientClass)

        assert result == 1

    def test_main_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        # Create a mock client class that raises an unexpected error
        MockClientClass = Mock()
        MockClientClass.side_effect = RuntimeError("Unexpected error")

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]), patch("sys.stderr"):
            # Suppress error output
            result = main(client_class=MockClientClass)

        assert result == 1

    def test_main_arris_modem_error_handling(self):
        """Test handling of ArrisModemError."""
        MockClientClass = Mock()
        # Use MagicMock for context manager support
        mock_client_instance = MagicMock()
        MockClientClass.return_value = mock_client_instance

        # Make get_status raise ArrisModemError
        mock_client_instance.get_status.side_effect = ArrisModemError("Test error")

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]), patch("sys.stderr"):
            # Suppress error output
            result = main(client_class=MockClientClass)

        assert result == 1

    def test_cli_module_import(self):
        """Test that CLI module can be imported and run."""
        # This tests the import structure is correct
        from arris_modem_status import cli

        assert hasattr(cli, "main")
        assert hasattr(cli, "main_function")

    def test_cli_entry_point(self):
        """Test CLI entry point via subprocess (integration test)."""
        project_root = Path(__file__).parent.parent

        # Run as module using -m flag
        result = subprocess.run(
            [sys.executable, "-m", "arris_modem_status.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
        )

        # Help should work - check both return code and output
        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")

        assert result.returncode == 0 or "usage:" in result.stdout or "usage:" in result.stderr

    def test_cli_help_output(self):
        """Test that help output works correctly."""
        project_root = Path(__file__).parent.parent

        # Run as module using -m flag instead of running __main__.py directly
        result = subprocess.run(
            [sys.executable, "-m", "arris_modem_status.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
        )

        # Help should work - check both stdout and stderr as argparse may use either
        assert (
            "Query Arris cable modem status" in result.stdout
            or "Query Arris cable modem status" in result.stderr
            or "usage:" in result.stdout
            or "usage:" in result.stderr
        )

    def test_cli_missing_password(self):
        """Test CLI with missing required password argument."""
        project_root = Path(__file__).parent.parent

        # Run without password
        result = subprocess.run(
            [sys.executable, "-m", "arris_modem_status.cli"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,
        )

        # Should fail with error about missing password
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "password" in result.stderr.lower()

    def test_main_function_direct_call(self):
        """Test calling main function directly with no arguments."""
        # When called with no arguments, argparse should exit
        with patch("sys.argv", ["arris-modem-status"]), pytest.raises(SystemExit):
            main()
