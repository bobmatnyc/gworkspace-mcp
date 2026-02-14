"""CLI tests for the setup command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from gworkspace_mcp.cli.main import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.mark.unit
class TestSetupCommand:
    """Tests for the setup CLI command."""

    def test_should_show_error_without_credentials(self, cli_runner: CliRunner) -> None:
        """Verify error shown when client ID/secret not provided."""
        result = cli_runner.invoke(main, ["setup"])

        assert result.exit_code == 1
        assert "OAuth client credentials required" in result.output

    def test_should_run_authentication_with_credentials(self, cli_runner: CliRunner) -> None:
        """Verify authentication runs when credentials provided."""
        with patch("gworkspace_mcp.auth.OAuthManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.has_valid_tokens.return_value = False
            mock_manager.authenticate = AsyncMock()
            mock_manager.token_path = "/tmp/tokens.json"
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main,
                [
                    "setup",
                    "--client-id=test_id",
                    "--client-secret=test_secret",
                ],
            )

            # Verify authenticate was called
            mock_manager.authenticate.assert_called_once_with(
                client_id="test_id",
                client_secret="test_secret",  # pragma: allowlist secret
            )
            assert "Authentication successful" in result.output

    def test_should_show_browser_message(self, cli_runner: CliRunner) -> None:
        """Verify message about browser opening is shown."""
        with patch("gworkspace_mcp.auth.OAuthManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.has_valid_tokens.return_value = False
            mock_manager.authenticate = AsyncMock()
            mock_manager.token_path = "/tmp/tokens.json"
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main,
                [
                    "setup",
                    "--client-id=test_id",
                    "--client-secret=test_secret",
                ],
            )

            assert "Browser will open" in result.output
