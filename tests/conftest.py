"""Shared pytest fixtures for google-workspace-mcp tests.

This module provides reusable fixtures for testing OAuth authentication,
token storage, and Google API mocks.
"""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gworkspace_mcp.auth.models import OAuthToken, StoredToken, TokenMetadata

# =============================================================================
# Token Fixtures
# =============================================================================


@pytest.fixture
def valid_token() -> OAuthToken:
    """Create a valid, non-expired OAuth token."""
    return OAuthToken(
        access_token="test_access_token_abc123",
        refresh_token="test_refresh_token_xyz789",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=[
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/tasks",
        ],
        token_type="Bearer",
    )


@pytest.fixture
def expired_token() -> OAuthToken:
    """Create an expired OAuth token."""
    return OAuthToken(
        access_token="expired_access_token",
        refresh_token="test_refresh_token",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/calendar"],
        token_type="Bearer",
    )


@pytest.fixture
def token_metadata() -> TokenMetadata:
    """Create token metadata for testing."""
    return TokenMetadata(
        service_name="google-workspace",
        provider="google",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )


@pytest.fixture
def stored_token(valid_token: OAuthToken, token_metadata: TokenMetadata) -> StoredToken:
    """Create a complete stored token for testing."""
    return StoredToken(
        version=1,
        metadata=token_metadata,
        token=valid_token,
    )


# =============================================================================
# Token Storage Fixtures
# =============================================================================


@pytest.fixture
def temp_token_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for token storage tests."""
    token_dir = tmp_path / ".gworkspace-mcp"
    token_dir.mkdir(parents=True, mode=0o700)
    return token_dir


@pytest.fixture
def temp_token_path(temp_token_dir: Path) -> Path:
    """Get the path for a temporary tokens.json file."""
    return temp_token_dir / "tokens.json"


@pytest.fixture
def token_storage(temp_token_path: Path):
    """Create a TokenStorage instance with temporary storage."""
    from gworkspace_mcp.auth.token_storage import TokenStorage

    return TokenStorage(token_path=temp_token_path)


# =============================================================================
# OAuth Manager Fixtures
# =============================================================================


@pytest.fixture
def oauth_manager(token_storage):
    """Create an OAuthManager with temporary storage."""
    from gworkspace_mcp.auth.oauth_manager import OAuthManager

    return OAuthManager(storage=token_storage)


# =============================================================================
# Mock Google Credentials
# =============================================================================


@pytest.fixture
def mock_google_credentials() -> MagicMock:
    """Create a mock Google OAuth2 Credentials object."""
    mock_creds = MagicMock()
    mock_creds.token = "mock_access_token"
    mock_creds.refresh_token = "mock_refresh_token"
    mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_creds.expired = False
    mock_creds.valid = True
    mock_creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    return mock_creds


# =============================================================================
# Mock Google API Services
# =============================================================================


def _create_mock_service(service_name: str) -> MagicMock:
    """Create a mock Google API service with common patterns."""
    mock = MagicMock()
    mock._service_name = service_name
    return mock


@pytest.fixture
def mock_gmail_service() -> MagicMock:
    """Create a mock Gmail API service.

    Provides mocks for common Gmail operations:
    - users().messages().list()
    - users().messages().get()
    - users().messages().send()
    - users().labels().list()
    """
    mock = _create_mock_service("gmail")

    # Setup messages mock
    mock_messages = MagicMock()
    mock_messages.list.return_value.execute.return_value = {
        "messages": [
            {"id": "msg1", "threadId": "thread1"},
            {"id": "msg2", "threadId": "thread2"},
        ]
    }
    mock_messages.get.return_value.execute.return_value = {
        "id": "msg1",
        "threadId": "thread1",
        "labelIds": ["INBOX"],
        "snippet": "Test email snippet",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "test@example.com"},
            ]
        },
    }
    mock_messages.send.return_value.execute.return_value = {
        "id": "new_msg_id",
        "threadId": "new_thread_id",
    }

    # Setup labels mock
    mock_labels = MagicMock()
    mock_labels.list.return_value.execute.return_value = {
        "labels": [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "SENT", "name": "SENT", "type": "system"},
            {"id": "Label_1", "name": "Custom Label", "type": "user"},
        ]
    }

    # Wire up the service
    mock.users.return_value.messages.return_value = mock_messages
    mock.users.return_value.labels.return_value = mock_labels

    return mock


@pytest.fixture
def mock_calendar_service() -> MagicMock:
    """Create a mock Google Calendar API service.

    Provides mocks for common Calendar operations:
    - calendarList().list()
    - events().list()
    - events().insert()
    - events().update()
    - events().delete()
    """
    mock = _create_mock_service("calendar")

    # Setup calendar list mock
    mock_calendar_list = MagicMock()
    mock_calendar_list.list.return_value.execute.return_value = {
        "items": [
            {"id": "primary", "summary": "Primary Calendar"},
            {"id": "cal_123", "summary": "Work Calendar"},
        ]
    }

    # Setup events mock
    mock_events = MagicMock()
    mock_events.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "event1",
                "summary": "Test Event",
                "start": {"dateTime": "2025-01-15T10:00:00Z"},
                "end": {"dateTime": "2025-01-15T11:00:00Z"},
            }
        ]
    }
    mock_events.insert.return_value.execute.return_value = {
        "id": "new_event_id",
        "summary": "New Event",
    }

    mock.calendarList.return_value = mock_calendar_list
    mock.events.return_value = mock_events

    return mock


@pytest.fixture
def mock_drive_service() -> MagicMock:
    """Create a mock Google Drive API service.

    Provides mocks for common Drive operations:
    - files().list()
    - files().get()
    - files().create()
    - files().delete()
    """
    mock = _create_mock_service("drive")

    mock_files = MagicMock()
    mock_files.list.return_value.execute.return_value = {
        "files": [
            {
                "id": "file1",
                "name": "Test Document.docx",
                "mimeType": "application/vnd.google-apps.document",
            },
            {
                "id": "file2",
                "name": "Test Spreadsheet.xlsx",
                "mimeType": "application/vnd.google-apps.spreadsheet",
            },
        ]
    }
    mock_files.get.return_value.execute.return_value = {
        "id": "file1",
        "name": "Test Document.docx",
        "mimeType": "application/vnd.google-apps.document",
    }
    mock_files.create.return_value.execute.return_value = {
        "id": "new_file_id",
        "name": "New File.docx",
    }

    mock.files.return_value = mock_files

    return mock


@pytest.fixture
def mock_docs_service() -> MagicMock:
    """Create a mock Google Docs API service.

    Provides mocks for common Docs operations:
    - documents().get()
    - documents().create()
    - documents().batchUpdate()
    """
    mock = _create_mock_service("docs")

    mock_documents = MagicMock()
    mock_documents.get.return_value.execute.return_value = {
        "documentId": "doc1",
        "title": "Test Document",
        "body": {
            "content": [{"paragraph": {"elements": [{"textRun": {"content": "Test content\n"}}]}}]
        },
    }
    mock_documents.create.return_value.execute.return_value = {
        "documentId": "new_doc_id",
        "title": "New Document",
    }
    mock_documents.batchUpdate.return_value.execute.return_value = {
        "documentId": "doc1",
        "replies": [],
    }

    mock.documents.return_value = mock_documents

    return mock


@pytest.fixture
def mock_tasks_service() -> MagicMock:
    """Create a mock Google Tasks API service.

    Provides mocks for common Tasks operations:
    - tasklists().list()
    - tasks().list()
    - tasks().insert()
    - tasks().update()
    """
    mock = _create_mock_service("tasks")

    mock_tasklists = MagicMock()
    mock_tasklists.list.return_value.execute.return_value = {
        "items": [
            {"id": "tasklist1", "title": "My Tasks"},
            {"id": "tasklist2", "title": "Work Tasks"},
        ]
    }

    mock_tasks = MagicMock()
    mock_tasks.list.return_value.execute.return_value = {
        "items": [
            {"id": "task1", "title": "Test Task", "status": "needsAction"},
            {"id": "task2", "title": "Completed Task", "status": "completed"},
        ]
    }
    mock_tasks.insert.return_value.execute.return_value = {
        "id": "new_task_id",
        "title": "New Task",
    }

    mock.tasklists.return_value = mock_tasklists
    mock.tasks.return_value = mock_tasks

    return mock


# =============================================================================
# Google API Build Mock
# =============================================================================


@pytest.fixture
def mock_google_build(
    mock_gmail_service: MagicMock,
    mock_calendar_service: MagicMock,
    mock_drive_service: MagicMock,
    mock_docs_service: MagicMock,
    mock_tasks_service: MagicMock,
) -> Generator[MagicMock, None, None]:
    """Mock googleapiclient.discovery.build to return test service mocks.

    This fixture patches the build function and returns the appropriate
    mock service based on the service name argument.
    """
    services = {
        "gmail": mock_gmail_service,
        "calendar": mock_calendar_service,
        "drive": mock_drive_service,
        "docs": mock_docs_service,
        "tasks": mock_tasks_service,
    }

    def mock_build(service_name: str, version: str, credentials: Any = None, **kwargs) -> MagicMock:
        return services.get(service_name, MagicMock())

    with patch("googleapiclient.discovery.build", side_effect=mock_build) as mock:
        yield mock


# =============================================================================
# CLI Test Fixtures
# =============================================================================


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    from click.testing import CliRunner

    return CliRunner()


# =============================================================================
# Async Test Helpers
# =============================================================================


@pytest.fixture
def event_loop_policy():
    """Provide an event loop policy for async tests.

    Note: pytest-asyncio handles event loop creation automatically.
    This fixture can be used for custom event loop configurations.
    """
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
