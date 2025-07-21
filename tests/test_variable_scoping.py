"""Test variable scoping fixes."""

import pytest
from unittest.mock import patch
from io import StringIO
from contextlib import redirect_stderr

try:
    from arris_modem_status import ArrisModemStatusClient
    from arris_modem_status.cli import main
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytest.skip("ArrisModemStatusClient not available", allow_module_level=True)


@pytest.mark.unit
class TestVariableScoping:
    """Test variable scoping fixes in CLI and client error paths."""

    def test_client_authentication_error_scoping(self):
        """Test variable scoping in authentication error paths."""
        with patch('requests.Session.post') as mock_post:
            from requests.exceptions import ConnectionError
            mock_post.side_effect = ConnectionError("Connection failed")

            client = ArrisModemStatusClient(password="test", host="test")
            result = client.authenticate()
            assert result is False

    def test_cli_error_handling_no_undefined_vars(self):
        """Test CLI error handling doesn't have undefined variables."""
        test_argv = ['arris-modem-status', '--password', 'test']

        with patch('sys.argv', test_argv):
            with patch('arris_modem_status.cli.main.ArrisModemStatusClient') as mock_client:
                mock_client.side_effect = Exception("Generic error")

                stderr_capture = StringIO()

                try:
                    with redirect_stderr(stderr_capture):
                        main()
                except SystemExit:
                    pass  # Expected

                # Check no NameError in stderr
                stderr_output = stderr_capture.getvalue()
                assert "NameError" not in stderr_output
