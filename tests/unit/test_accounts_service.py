"""Unit tests for the accounts service module (list_accounts tool)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from gworkspace_mcp.server.services.accounts import TOOLS, get_handlers


def _make_service(profiles: list[dict]) -> MagicMock:
    """Build a minimal mock BaseService with storage.list_profiles() set up."""
    service = MagicMock()
    service.storage.list_profiles.return_value = profiles
    return service


@pytest.mark.unit
class TestListAccountsTool:
    """Tests for the list_accounts Tool definition."""

    def test_tool_name(self) -> None:
        """Verify the tool is named list_accounts."""
        assert len(TOOLS) == 1
        assert TOOLS[0].name == "list_accounts"

    def test_tool_has_no_required_parameters(self) -> None:
        """Verify list_accounts requires no input parameters."""
        schema = TOOLS[0].inputSchema
        assert schema.get("required", []) == []
        assert schema.get("properties", {}) == {}

    def test_tool_has_description(self) -> None:
        """Verify the tool has a non-empty description."""
        assert TOOLS[0].description
        assert len(TOOLS[0].description) > 0

    def test_tool_description_mentions_account_parameter(self) -> None:
        """Verify description guides users toward the account parameter."""
        assert "account" in TOOLS[0].description.lower()


@pytest.mark.unit
class TestListAccountsHandler:
    """Tests for the list_accounts handler function."""

    @pytest.mark.asyncio
    async def test_returns_empty_accounts_when_no_profiles(self) -> None:
        """Verify handler returns empty list when no profiles are stored."""
        service = _make_service([])
        handlers = get_handlers(service)

        result = await handlers["list_accounts"]({})

        assert result["accounts"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_all_profiles(self) -> None:
        """Verify handler returns every configured profile."""
        profiles = [
            {
                "profile_name": "work",
                "email": "work@example.com",
                "is_default": True,
                "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "last_refreshed": None,
            },
            {
                "profile_name": "personal",
                "email": "personal@example.com",
                "is_default": False,
                "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
                "last_refreshed": None,
            },
        ]
        service = _make_service(profiles)
        handlers = get_handlers(service)

        result = await handlers["list_accounts"]({})

        assert result["total"] == 2
        assert len(result["accounts"]) == 2

    @pytest.mark.asyncio
    async def test_account_entry_shape(self) -> None:
        """Verify each account entry contains expected keys."""
        profiles = [
            {
                "profile_name": "gworkspace-mcp",
                "email": "user@gmail.com",
                "is_default": True,
                "created_at": datetime(2025, 3, 15, tzinfo=timezone.utc),
                "last_refreshed": None,
            }
        ]
        service = _make_service(profiles)
        handlers = get_handlers(service)

        result = await handlers["list_accounts"]({})
        account = result["accounts"][0]

        assert account["profile"] == "gworkspace-mcp"
        assert account["email"] == "user@gmail.com"
        assert account["is_default"] is True
        assert "created_at" in account

    @pytest.mark.asyncio
    async def test_default_is_default_false_when_missing(self) -> None:
        """Verify is_default defaults to False when not present in profile data."""
        profiles = [
            {
                "profile_name": "work",
                "email": None,
                # is_default key intentionally omitted
                "created_at": None,
                "last_refreshed": None,
            }
        ]
        service = _make_service(profiles)
        handlers = get_handlers(service)

        result = await handlers["list_accounts"]({})

        assert result["accounts"][0]["is_default"] is False

    @pytest.mark.asyncio
    async def test_created_at_none_when_missing(self) -> None:
        """Verify created_at is None when profile has no created_at."""
        profiles = [
            {
                "profile_name": "work",
                "email": "work@example.com",
                "is_default": False,
                "created_at": None,
                "last_refreshed": None,
            }
        ]
        service = _make_service(profiles)
        handlers = get_handlers(service)

        result = await handlers["list_accounts"]({})

        assert result["accounts"][0]["created_at"] is None

    @pytest.mark.asyncio
    async def test_response_includes_hint(self) -> None:
        """Verify response includes a usage hint referencing the account parameter."""
        service = _make_service([])
        handlers = get_handlers(service)

        result = await handlers["list_accounts"]({})

        assert "hint" in result
        assert "account" in result["hint"].lower()

    @pytest.mark.asyncio
    async def test_handler_calls_list_profiles(self) -> None:
        """Verify handler calls storage.list_profiles() exactly once."""
        service = _make_service([])
        handlers = get_handlers(service)

        await handlers["list_accounts"]({})

        service.storage.list_profiles.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_accounts_registered_in_handlers(self) -> None:
        """Verify list_accounts key is present in the handlers dict."""
        service = _make_service([])
        handlers = get_handlers(service)

        assert "list_accounts" in handlers
        assert callable(handlers["list_accounts"])
