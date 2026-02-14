# Testing Guide

This guide covers running and writing tests for gworkspace-mcp.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_oauth_manager.py
│   ├── test_token_models.py
│   └── test_token_storage.py
└── integration/             # Integration tests
    ├── __init__.py
    └── test_google_workspace_server.py
```

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src/gworkspace_mcp

# Run with coverage and HTML report
pytest --cov=src/gworkspace_mcp --cov-report=html
```

### Running Specific Tests

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_token_storage.py

# Run specific test function
pytest tests/unit/test_token_storage.py::test_store_token

# Run tests matching a pattern
pytest -k "token"
```

### Test Markers

```bash
# Run only tests marked as "unit"
pytest -m unit

# Run only tests marked as "integration"
pytest -m integration

# Run tests excluding slow tests
pytest -m "not slow"
```

## Writing Tests

### Test File Naming

- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`

### Basic Test Structure

```python
import pytest
from gworkspace_mcp.auth import TokenStorage


class TestTokenStorage:
    """Tests for TokenStorage class."""

    def test_initialization(self, tmp_path):
        """Test that TokenStorage initializes correctly."""
        storage = TokenStorage(storage_dir=tmp_path)
        assert storage.storage_dir == tmp_path

    def test_store_token(self, tmp_path):
        """Test storing a token."""
        storage = TokenStorage(storage_dir=tmp_path)
        token_data = {"access_token": "test123"}

        storage.store("test-service", token_data)

        assert (tmp_path / "tokens.json").exists()

    def test_retrieve_nonexistent(self, tmp_path):
        """Test retrieving a token that doesn't exist returns None."""
        storage = TokenStorage(storage_dir=tmp_path)

        result = storage.retrieve("nonexistent")

        assert result is None
```

### Using Fixtures

**Shared fixtures in `conftest.py`**:

```python
import pytest
from pathlib import Path


@pytest.fixture
def sample_token():
    """Provide a sample OAuth token."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@pytest.fixture
def mock_storage(tmp_path):
    """Provide a TokenStorage instance with temp directory."""
    from gworkspace_mcp.auth import TokenStorage
    return TokenStorage(storage_dir=tmp_path)
```

**Using fixtures in tests**:

```python
def test_store_token(mock_storage, sample_token):
    """Test storing a token using fixtures."""
    mock_storage.store("test-service", sample_token)
    retrieved = mock_storage.retrieve("test-service")
    assert retrieved["access_token"] == sample_token["access_token"]
```

### Async Tests

For async functions, use `pytest-asyncio`:

```python
import pytest


@pytest.mark.asyncio
async def test_async_operation():
    """Test an async function."""
    from gworkspace_mcp.server import GoogleWorkspaceServer

    server = GoogleWorkspaceServer()
    # Test async methods
    tools = await server.list_tools()
    assert len(tools) > 0
```

### Mocking

**Mocking external services**:

```python
from unittest.mock import patch, MagicMock


def test_api_call_with_mock():
    """Test API call with mocked response."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Your test code here
        pass


@pytest.fixture
def mock_google_api():
    """Mock Google API responses."""
    with patch("gworkspace_mcp.server.httpx.AsyncClient") as mock:
        yield mock
```

**Mocking OAuth manager**:

```python
@pytest.fixture
def mock_oauth_manager():
    """Provide a mocked OAuthManager."""
    with patch("gworkspace_mcp.auth.OAuthManager") as mock:
        mock_instance = MagicMock()
        mock_instance.get_credentials.return_value = MagicMock(
            token="fake_token",
            valid=True,
        )
        mock.return_value = mock_instance
        yield mock_instance
```

### Testing Error Cases

```python
import pytest


def test_invalid_input_raises_error():
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError) as exc_info:
        # Call function with invalid input
        validate_email("not-an-email")

    assert "Invalid email format" in str(exc_info.value)


def test_file_not_found():
    """Test handling of missing files."""
    storage = TokenStorage(storage_dir=Path("/nonexistent"))

    with pytest.raises(FileNotFoundError):
        storage.retrieve("test")
```

### Parametrized Tests

```python
import pytest


@pytest.mark.parametrize("query,expected_count", [
    ("from:test@example.com", 5),
    ("is:unread", 10),
    ("subject:meeting", 3),
])
def test_gmail_search(query, expected_count, mock_gmail_api):
    """Test Gmail search with various queries."""
    # Configure mock
    mock_gmail_api.return_value = {"messages": [{}] * expected_count}

    # Execute search
    result = search_gmail_messages(query)

    assert len(result) == expected_count
```

## Test Categories

### Unit Tests

Unit tests verify individual components in isolation:

```python
# tests/unit/test_token_models.py

from gworkspace_mcp.auth.models import OAuthToken, TokenStatus


class TestOAuthToken:
    """Unit tests for OAuthToken model."""

    def test_create_token(self):
        """Test creating an OAuthToken."""
        token = OAuthToken(
            access_token="abc123",
            refresh_token="refresh456",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert token.access_token == "abc123"

    def test_token_expiration(self):
        """Test token expiration detection."""
        expired_token = OAuthToken(
            access_token="abc123",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert expired_token.is_expired()
```

### Integration Tests

Integration tests verify component interactions:

```python
# tests/integration/test_google_workspace_server.py

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_server_lists_tools():
    """Test that server returns expected tools."""
    from gworkspace_mcp.server import GoogleWorkspaceServer

    server = GoogleWorkspaceServer()
    tools = await server.server.list_tools()

    assert len(tools) >= 65
    tool_names = [t.name for t in tools]
    assert "search_gmail_messages" in tool_names
    assert "list_calendars" in tool_names
```

## Coverage

### Viewing Coverage

```bash
# Terminal coverage report
pytest --cov=src/gworkspace_mcp --cov-report=term-missing

# HTML coverage report
pytest --cov=src/gworkspace_mcp --cov-report=html
open htmlcov/index.html
```

### Coverage Targets

| Component | Target |
|-----------|--------|
| Auth module | 90%+ |
| CLI module | 80%+ |
| Server module | 80%+ |
| Overall | 85%+ |

## Continuous Integration

Tests run automatically on:
- Pull requests to `main`
- Pushes to `main`

See `.github/workflows/ci.yml` for CI configuration.

## Troubleshooting

### Common Issues

**Tests fail with "No module named"**:
```bash
# Ensure package is installed in development mode
pip install -e ".[dev]"
```

**Async test warnings**:
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

**Coverage not detecting files**:
```bash
# Use source path explicitly
pytest --cov=src/gworkspace_mcp --cov-report=term-missing
```

### Debugging Tests

```bash
# Run with print output visible
pytest -s

# Run with debugger on failure
pytest --pdb

# Run specific test with debugging
pytest tests/unit/test_token_storage.py::test_store_token -v --pdb
```

## Best Practices

1. **One assertion per test** - Keep tests focused
2. **Descriptive test names** - `test_<what>_<condition>_<expected>`
3. **Use fixtures** - Avoid repetition, improve maintainability
4. **Test edge cases** - Empty inputs, invalid data, boundaries
5. **Mock external services** - Tests should not require network
6. **Keep tests fast** - Unit tests should run in milliseconds
7. **Test behavior, not implementation** - Focus on outputs

## Related Documentation

- [Contributing Guide](contributing.md)
- [Release Process](releasing.md)
