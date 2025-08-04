"""Test variable scoping fixes."""

from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import Mock, patch

import pytest

try:
    from arris_modem_status import ArrisModemStatusClient
    from arris_modem_status.cli.main import main  # Import the function, not the module

    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytest.skip("ArrisModemStatusClient not available", allow_module_level=True)


@pytest.mark.unit
class TestVariableScoping:
    """Test variable scoping fixes in CLI and client error paths."""

    def test_client_authentication_error_scoping(self):
        """Test variable scoping in authentication error paths."""
        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import ConnectionError

            mock_post.side_effect = ConnectionError("Connection failed")

            client = ArrisModemStatusClient(password="test", host="test")

            # With the new exception handling, ConnectionError should be raised as ArrisConnectionError
            from arris_modem_status.exceptions import ArrisConnectionError

            with pytest.raises(ArrisConnectionError) as exc_info:
                client.authenticate()

            # Verify the error message contains our connection failed message
            assert "test:443" in str(exc_info.value)

    def test_cli_error_handling_no_undefined_vars(self):
        """Test CLI error handling doesn't have undefined variables."""
        test_argv = ["arris-modem-status", "--password", "test"]

        with patch("sys.argv", test_argv):
            # Create a mock client class that raises an exception
            MockClientClass = Mock()
            MockClientClass.side_effect = Exception("Generic error")

            stderr_capture = StringIO()

            try:
                with redirect_stderr(stderr_capture):
                    # Call main with the mock client class
                    exit_code = main(client_class=MockClientClass)
                    # The function should return 1 on error
                    assert exit_code == 1
            except SystemExit:
                pass  # This is also acceptable if main calls sys.exit()

            # Check no NameError in stderr
            stderr_output = stderr_capture.getvalue()
            assert "NameError" not in stderr_output
