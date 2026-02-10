# Development Documentation

This directory contains guides for contributors and developers.

## Contents

- **[contributing.md](./contributing.md)** - How to contribute to the project
- **[testing.md](./testing.md)** - Running and writing tests
- **[releasing.md](./releasing.md)** - Release process and versioning

## Quick Links

| Guide | Purpose |
|-------|---------|
| [Contributing](./contributing.md) | Development setup, code style, PR guidelines |
| [Testing](./testing.md) | pytest usage, writing tests, coverage |
| [Releasing](./releasing.md) | Version management, PyPI publishing |

## Development Quick Start

```bash
# Clone and setup
git clone https://github.com/masapasa/google-workspace-mcp.git
cd google-workspace-mcp
pip install -e ".[dev]"

# Run tests
pytest

# Code quality
ruff format src tests
ruff check src tests
mypy src
```

## Related Documentation

- [Parent Index](../index.md)
- [Getting Started](../getting-started/README.md)
- [API Reference](../api/README.md)
