# Contributing Guide

Thank you for your interest in contributing to gworkspace-mcp! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A Google Cloud project with OAuth credentials (for testing)

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/gworkspace-mcp.git
   cd gworkspace-mcp
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

5. **Verify installation**:
   ```bash
   workspace --version
   pytest --collect-only
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

Write your code following the project's style guidelines (see below).

### 3. Run Quality Checks

```bash
# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# Run tests
pytest
```

### 4. Commit Changes

Use conventional commit messages:

```bash
git commit -m "feat: add new calendar tool"
git commit -m "fix: handle token refresh edge case"
git commit -m "docs: update authentication guide"
```

**Commit types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code change without feature/fix
- `test`: Test additions/changes
- `chore`: Build/tooling changes

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting.

**Key conventions**:
- Maximum line length: 88 characters
- Use type hints for function parameters and returns
- Use docstrings for public functions and classes
- Prefer `pathlib.Path` over `os.path`

**Example**:

```python
from pathlib import Path
from typing import Optional


def process_file(path: Path, encoding: str = "utf-8") -> Optional[str]:
    """Process a file and return its contents.

    Args:
        path: Path to the file to process.
        encoding: File encoding (default: utf-8).

    Returns:
        File contents as string, or None if file not found.

    Raises:
        ValueError: If path is not a file.
    """
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        return path.read_text(encoding=encoding)
    except FileNotFoundError:
        return None
```

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of function.

    Longer description if needed. Can span multiple lines.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When something is wrong.

    Example:
        >>> function_name("hello", 42)
        True
    """
    pass
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local imports

```python
import json
import logging
from pathlib import Path

import httpx
from pydantic import BaseModel

from gworkspace_mcp.auth import OAuthManager
```

## Project Structure

```
gworkspace-mcp/
├── src/gworkspace_mcp/
│   ├── __init__.py
│   ├── __version__.py
│   ├── cli/
│   │   └── main.py              # CLI commands
│   ├── auth/
│   │   ├── models.py            # Pydantic models
│   │   ├── token_storage.py     # Token persistence
│   │   └── oauth_manager.py     # OAuth flow
│   └── server/
│       ├── __init__.py
│       └── google_workspace_server.py  # MCP server
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── docs/                        # Documentation
└── pyproject.toml               # Project configuration
```

## Adding New Tools

To add a new MCP tool:

1. **Define the tool in `google_workspace_server.py`**:

   ```python
   Tool(
       name="your_tool_name",
       description="Clear description of what the tool does",
       inputSchema={
           "type": "object",
           "properties": {
               "param1": {
                   "type": "string",
                   "description": "What this parameter does",
               },
           },
           "required": ["param1"],
       },
   ),
   ```

2. **Implement the handler in `call_tool`**:

   ```python
   elif name == "your_tool_name":
       param1 = arguments.get("param1")
       # Implementation
       result = await self._your_api_call(param1)
       return [TextContent(type="text", text=json.dumps(result))]
   ```

3. **Add tests**:

   ```python
   # tests/unit/test_your_tool.py
   async def test_your_tool_name():
       # Test implementation
       pass
   ```

4. **Update documentation**:
   - Add to relevant API reference doc in `docs/api/`
   - Update tool counts in `README.md` and `docs/index.md`

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/gworkspace_mcp

# Only unit tests
pytest tests/unit/

# Only integration tests
pytest tests/integration/

# Specific test file
pytest tests/unit/test_oauth_manager.py

# Verbose output
pytest -v
```

### Writing Tests

**Unit test example**:

```python
import pytest
from gworkspace_mcp.auth import TokenStorage


class TestTokenStorage:
    """Tests for TokenStorage class."""

    def test_store_and_retrieve(self, tmp_path):
        """Test that tokens can be stored and retrieved."""
        storage = TokenStorage(storage_dir=tmp_path)
        token = {"access_token": "test", "refresh_token": "refresh"}

        storage.store("test-service", token)
        retrieved = storage.retrieve("test-service")

        assert retrieved["access_token"] == "test"

    def test_retrieve_nonexistent(self, tmp_path):
        """Test retrieving a token that doesn't exist."""
        storage = TokenStorage(storage_dir=tmp_path)

        result = storage.retrieve("nonexistent")

        assert result is None
```

### Test Categories

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions, may use mocked APIs

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`ruff format`)
- [ ] No linting errors (`ruff check`)
- [ ] Type checking passes (`mypy src`)
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional format

### PR Description Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (describe)

## Testing

Describe how you tested these changes.

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG updated (for features/fixes)
```

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/masapasa/gworkspace-mcp/discussions)
- **Bugs**: Open an [Issue](https://github.com/masapasa/gworkspace-mcp/issues)
- **Security**: Email security concerns privately

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
