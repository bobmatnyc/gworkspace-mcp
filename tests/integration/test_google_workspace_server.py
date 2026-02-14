"""Integration tests for Google Workspace MCP server.

Tests a representative sample of MCP tools (not all 65) from each category:
- Gmail: search_gmail_messages, get_gmail_message_content, send_email
- Calendar: list_calendars, create_event
- Drive: search_drive_files, get_drive_file_content
- Docs: create_document, get_document
- Tasks: list_task_lists, create_task

All Google API calls are mocked via httpx.AsyncClient patching.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gworkspace_mcp.server.google_workspace_server import GoogleWorkspaceServer


@pytest.fixture
def mock_token_storage():
    """Create a mock token storage that returns valid tokens."""
    from gworkspace_mcp.auth.models import TokenStatus

    mock_storage = MagicMock()
    mock_storage.get_status.return_value = TokenStatus.VALID

    stored_token = MagicMock()
    stored_token.token.access_token = "mock_access_token_12345"
    mock_storage.retrieve.return_value = stored_token

    return mock_storage


@pytest.fixture
def server(mock_token_storage):
    """Create a GoogleWorkspaceServer instance with mocked token storage."""
    with patch(
        "gworkspace_mcp.server.google_workspace_server.TokenStorage",
        return_value=mock_token_storage,
    ):
        with patch("gworkspace_mcp.server.google_workspace_server.OAuthManager"):
            server = GoogleWorkspaceServer()
            server.storage = mock_token_storage
            return server


def create_mock_response(json_data: dict[str, Any], status_code: int = 200) -> MagicMock:
    """Create a mock httpx Response object."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.text = ""
    mock_response.raise_for_status = MagicMock()
    return mock_response


# =============================================================================
# Gmail Integration Tests
# =============================================================================


@pytest.mark.integration
class TestGmailTools:
    """Integration tests for Gmail MCP tools."""

    @pytest.mark.asyncio
    async def test_search_gmail_messages_success(self, server):
        """Test searching Gmail messages returns formatted results."""
        # Arrange: Mock responses for list and subsequent get calls
        list_response = {
            "messages": [
                {"id": "msg_001", "threadId": "thread_001"},
                {"id": "msg_002", "threadId": "thread_002"},
            ]
        }
        msg_detail_001 = {
            "id": "msg_001",
            "threadId": "thread_001",
            "snippet": "Meeting tomorrow at 10am",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Team Meeting"},
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Date", "value": "Mon, 10 Feb 2025 09:00:00 -0500"},
                ]
            },
        }
        msg_detail_002 = {
            "id": "msg_002",
            "threadId": "thread_002",
            "snippet": "Project update attached",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Project Status"},
                    {"name": "From", "value": "charlie@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Date", "value": "Mon, 10 Feb 2025 10:00:00 -0500"},
                ]
            },
        }

        call_count = [0]

        async def mock_request(method, url, **kwargs):
            call_count[0] += 1
            if "messages" in url and "msg_001" in url:
                return create_mock_response(msg_detail_001)
            if "messages" in url and "msg_002" in url:
                return create_mock_response(msg_detail_002)
            return create_mock_response(list_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._search_gmail_messages(
                {"query": "from:alice@example.com", "max_results": 10}
            )

            # Assert
            assert result["count"] == 2
            assert len(result["messages"]) == 2
            assert result["messages"][0]["id"] == "msg_001"
            assert result["messages"][0]["subject"] == "Team Meeting"
            assert result["messages"][0]["from"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_gmail_message_content_success(self, server):
        """Test retrieving full Gmail message content."""
        # Arrange
        import base64

        body_text = "Hello, this is the email body content."
        encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()

        message_response = {
            "id": "msg_001",
            "threadId": "thread_001",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Cc", "value": "cc@example.com"},
                    {"name": "Date", "value": "Mon, 10 Feb 2025 09:00:00 -0500"},
                ],
                "body": {"data": encoded_body},
            },
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(message_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._get_gmail_message_content({"message_id": "msg_001"})

            # Assert
            assert result["id"] == "msg_001"
            assert result["subject"] == "Test Subject"
            assert result["from"] == "sender@example.com"
            assert result["body"] == body_text
            assert "INBOX" in result["labels"]

    @pytest.mark.asyncio
    async def test_send_email_success(self, server):
        """Test sending email returns success response."""
        # Arrange
        send_response = {
            "id": "sent_msg_001",
            "threadId": "new_thread_001",
            "labelIds": ["SENT"],
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(send_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._send_email(
                {
                    "to": "recipient@example.com",
                    "subject": "Test Email",
                    "body": "This is a test email body.",
                }
            )

            # Assert
            assert result["status"] == "sent"
            assert result["id"] == "sent_msg_001"
            assert result["thread_id"] == "new_thread_001"

    @pytest.mark.asyncio
    async def test_search_gmail_messages_empty_results(self, server):
        """Test searching Gmail with no matches returns empty list."""
        list_response = {"messages": []}

        async def mock_request(method, url, **kwargs):
            return create_mock_response(list_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._search_gmail_messages({"query": "nonexistent@example.com"})

            # Assert
            assert result["count"] == 0
            assert result["messages"] == []


# =============================================================================
# Calendar Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCalendarTools:
    """Integration tests for Calendar MCP tools."""

    @pytest.mark.asyncio
    async def test_list_calendars_success(self, server):
        """Test listing calendars returns formatted calendar list."""
        # Arrange
        calendar_list_response = {
            "items": [
                {
                    "id": "primary",
                    "summary": "Primary Calendar",
                    "description": "Main calendar",
                    "accessRole": "owner",
                    "primary": True,
                },
                {
                    "id": "work_cal_123",
                    "summary": "Work Calendar",
                    "description": "Work events",
                    "accessRole": "writer",
                    "primary": False,
                },
            ]
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(calendar_list_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._list_calendars({})

            # Assert
            assert result["count"] == 2
            assert len(result["calendars"]) == 2
            assert result["calendars"][0]["id"] == "primary"
            assert result["calendars"][0]["primary"] is True
            assert result["calendars"][1]["summary"] == "Work Calendar"

    @pytest.mark.asyncio
    async def test_create_event_success(self, server):
        """Test creating calendar event returns created event details."""
        # Arrange
        create_response = {
            "id": "event_001",
            "summary": "Team Standup",
            "start": {"dateTime": "2025-02-15T10:00:00Z"},
            "end": {"dateTime": "2025-02-15T10:30:00Z"},
            "htmlLink": "https://calendar.google.com/event?eid=event_001",
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(create_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._create_event(
                {
                    "summary": "Team Standup",
                    "start_time": "2025-02-15T10:00:00Z",
                    "end_time": "2025-02-15T10:30:00Z",
                    "description": "Daily standup meeting",
                }
            )

            # Assert
            assert result["status"] == "created"
            assert result["id"] == "event_001"
            assert result["summary"] == "Team Standup"
            assert "calendar.google.com" in result["html_link"]

    @pytest.mark.asyncio
    async def test_create_event_with_attendees(self, server):
        """Test creating event with attendees includes attendee emails."""
        create_response = {
            "id": "event_002",
            "summary": "Project Review",
            "start": {"dateTime": "2025-02-16T14:00:00Z"},
            "end": {"dateTime": "2025-02-16T15:00:00Z"},
            "htmlLink": "https://calendar.google.com/event?eid=event_002",
            "attendees": [
                {"email": "alice@example.com"},
                {"email": "bob@example.com"},
            ],
        }

        captured_body = {}

        async def mock_request(method, url, **kwargs):
            if kwargs.get("json"):
                captured_body.update(kwargs["json"])
            return create_mock_response(create_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._create_event(
                {
                    "summary": "Project Review",
                    "start_time": "2025-02-16T14:00:00Z",
                    "end_time": "2025-02-16T15:00:00Z",
                    "attendees": ["alice@example.com", "bob@example.com"],
                }
            )

            # Assert
            assert result["status"] == "created"
            assert "attendees" in captured_body
            assert len(captured_body["attendees"]) == 2


# =============================================================================
# Drive Integration Tests
# =============================================================================


@pytest.mark.integration
class TestDriveTools:
    """Integration tests for Drive MCP tools."""

    @pytest.mark.asyncio
    async def test_search_drive_files_success(self, server):
        """Test searching Drive files returns formatted file list."""
        # Arrange
        search_response = {
            "files": [
                {
                    "id": "file_001",
                    "name": "Project Proposal.docx",
                    "mimeType": "application/vnd.google-apps.document",
                    "modifiedTime": "2025-02-10T12:00:00Z",
                    "size": "15360",
                    "webViewLink": "https://docs.google.com/document/d/file_001",
                    "owners": [{"emailAddress": "owner@example.com"}],
                },
                {
                    "id": "file_002",
                    "name": "Budget.xlsx",
                    "mimeType": "application/vnd.google-apps.spreadsheet",
                    "modifiedTime": "2025-02-09T15:30:00Z",
                    "size": "8192",
                    "webViewLink": "https://docs.google.com/spreadsheets/d/file_002",
                    "owners": [{"emailAddress": "owner@example.com"}],
                },
            ]
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(search_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._search_drive_files({"query": "project", "max_results": 10})

            # Assert
            assert result["count"] == 2
            assert len(result["files"]) == 2
            assert result["files"][0]["name"] == "Project Proposal.docx"
            assert result["files"][0]["owners"] == ["owner@example.com"]

    @pytest.mark.asyncio
    async def test_get_drive_file_content_google_doc(self, server):
        """Test getting content from a Google Doc exports as plain text."""
        # Arrange
        metadata_response = {
            "id": "doc_001",
            "name": "Meeting Notes.docx",
            "mimeType": "application/vnd.google-apps.document",
            "size": "1024",
        }
        export_content = "Meeting Notes\n\n1. Action items\n2. Next steps"

        call_urls = []

        async def mock_request(method, url, **kwargs):
            call_urls.append(url)
            return create_mock_response(metadata_response)

        async def mock_get(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.text = export_content
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._get_drive_file_content({"file_id": "doc_001"})

            # Assert
            assert result["id"] == "doc_001"
            assert result["name"] == "Meeting Notes.docx"
            assert result["content"] == export_content

    @pytest.mark.asyncio
    async def test_search_drive_files_empty_results(self, server):
        """Test Drive search with no matches returns empty list."""
        search_response = {"files": []}

        async def mock_request(method, url, **kwargs):
            return create_mock_response(search_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._search_drive_files({"query": "nonexistent_file_xyz"})

            # Assert
            assert result["count"] == 0
            assert result["files"] == []


# =============================================================================
# Docs Integration Tests
# =============================================================================


@pytest.mark.integration
class TestDocsTools:
    """Integration tests for Docs MCP tools."""

    @pytest.mark.asyncio
    async def test_create_document_success(self, server):
        """Test creating a new Google Doc returns document details."""
        # Arrange
        create_response = {
            "documentId": "new_doc_001",
            "title": "New Project Plan",
            "revisionId": "rev_001",
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(create_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._create_document({"title": "New Project Plan"})

            # Assert
            assert result["status"] == "created"
            assert result["document_id"] == "new_doc_001"
            assert result["title"] == "New Project Plan"
            assert result["revision_id"] == "rev_001"

    @pytest.mark.asyncio
    async def test_get_document_success(self, server):
        """Test retrieving a Google Doc returns content and metadata."""
        # Arrange
        doc_response = {
            "documentId": "doc_001",
            "title": "Quarterly Report",
            "revisionId": "rev_123",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Executive Summary\n"}},
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Q1 results exceeded expectations.\n"}},
                            ]
                        }
                    },
                ]
            },
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(doc_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._get_document({"document_id": "doc_001"})

            # Assert
            assert result["document_id"] == "doc_001"
            assert result["title"] == "Quarterly Report"
            assert "Executive Summary" in result["text_content"]
            assert "Q1 results" in result["text_content"]


# =============================================================================
# Tasks Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTasksTools:
    """Integration tests for Tasks MCP tools."""

    @pytest.mark.asyncio
    async def test_list_task_lists_success(self, server):
        """Test listing task lists returns formatted list."""
        # Arrange
        tasklists_response = {
            "items": [
                {
                    "id": "tasklist_001",
                    "title": "My Tasks",
                    "updated": "2025-02-10T12:00:00Z",
                    "selfLink": "https://tasks.googleapis.com/tasks/v1/users/@me/lists/tasklist_001",
                },
                {
                    "id": "tasklist_002",
                    "title": "Work Tasks",
                    "updated": "2025-02-09T15:30:00Z",
                    "selfLink": "https://tasks.googleapis.com/tasks/v1/users/@me/lists/tasklist_002",
                },
            ]
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(tasklists_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._list_task_lists({})

            # Assert
            assert result["count"] == 2
            assert len(result["task_lists"]) == 2
            assert result["task_lists"][0]["title"] == "My Tasks"
            assert result["task_lists"][1]["id"] == "tasklist_002"

    @pytest.mark.asyncio
    async def test_create_task_success(self, server):
        """Test creating a task returns created task details."""
        # Arrange
        create_response = {
            "id": "task_001",
            "title": "Review PR #123",
            "notes": "Check the new authentication logic",
            "status": "needsAction",
            "due": "2025-02-15T00:00:00Z",
            "updated": "2025-02-10T14:00:00Z",
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(create_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._create_task(
                {
                    "title": "Review PR #123",
                    "notes": "Check the new authentication logic",
                    "due": "2025-02-15T00:00:00Z",
                }
            )

            # Assert
            assert result["status"] == "created"
            assert result["id"] == "task_001"
            assert result["title"] == "Review PR #123"
            assert result["notes"] == "Check the new authentication logic"

    @pytest.mark.asyncio
    async def test_create_task_minimal(self, server):
        """Test creating a task with only required title field."""
        create_response = {
            "id": "task_002",
            "title": "Simple Task",
            "status": "needsAction",
            "updated": "2025-02-10T14:00:00Z",
        }

        async def mock_request(method, url, **kwargs):
            return create_mock_response(create_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act
            result = await server._create_task({"title": "Simple Task"})

            # Assert
            assert result["status"] == "created"
            assert result["title"] == "Simple Task"


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_api_error_propagates(self, server):
        """Test that HTTP errors from the API are properly raised."""

        async def mock_request(method, url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_resp,
            )
            return mock_resp

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Act & Assert
            with pytest.raises(httpx.HTTPStatusError):
                await server._list_calendars({})

    @pytest.mark.asyncio
    async def test_missing_token_raises_error(self, mock_token_storage):
        """Test that missing token raises RuntimeError."""
        from gworkspace_mcp.auth.models import TokenStatus

        mock_token_storage.get_status.return_value = TokenStatus.MISSING

        with patch(
            "gworkspace_mcp.server.google_workspace_server.TokenStorage",
            return_value=mock_token_storage,
        ):
            with patch("gworkspace_mcp.server.google_workspace_server.OAuthManager"):
                server = GoogleWorkspaceServer()
                server.storage = mock_token_storage

                # Act & Assert
                with pytest.raises(RuntimeError) as exc_info:
                    await server._get_access_token()

                assert "No OAuth token found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_expired_token_triggers_refresh(self, mock_token_storage):
        """Test that expired token triggers refresh mechanism."""
        from gworkspace_mcp.auth.models import TokenStatus

        # First call returns EXPIRED, triggering refresh
        mock_token_storage.get_status.return_value = TokenStatus.EXPIRED

        mock_oauth_manager = MagicMock()
        refreshed_token = MagicMock()
        refreshed_token.access_token = "refreshed_token_xyz"
        mock_oauth_manager.refresh_if_needed = AsyncMock(return_value=refreshed_token)

        with patch(
            "gworkspace_mcp.server.google_workspace_server.TokenStorage",
            return_value=mock_token_storage,
        ):
            with patch(
                "gworkspace_mcp.server.google_workspace_server.OAuthManager",
                return_value=mock_oauth_manager,
            ):
                server = GoogleWorkspaceServer()
                server.storage = mock_token_storage
                server.manager = mock_oauth_manager

                # Act
                token = await server._get_access_token()

                # Assert
                assert token == "refreshed_token_xyz"
                mock_oauth_manager.refresh_if_needed.assert_called_once()
