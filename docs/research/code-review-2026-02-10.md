# Code Review: gworkspace-mcp Project

**Date:** 2026-02-10
**Reviewer:** Claude Code Research Agent
**Scope:** Comprehensive review focusing on DX, Performance, and Code Quality

---

## Executive Summary

The gworkspace-mcp project is a well-structured MCP server providing 66 tools for Google Workspace integration. The codebase demonstrates solid fundamentals with good use of type hints, Pydantic models, and clear organization. However, there are several areas for improvement, particularly around HTTP client management, error handling granularity, and code modularity.

**Overall Assessment:** Good foundation with targeted improvements needed before production use.

---

## Findings by Category

### Developer Experience (DX)

#### DX-1: Error Messages Reference Non-Existent CLI Commands
**Severity:** HIGH
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Lines:** 1534, 1540, 1549-1550

**Issue:** Error messages reference `claude-mpm auth login google` which is incorrect for this standalone package.

```python
# Line 1532-1535
raise RuntimeError(
    f"No OAuth token found for service '{SERVICE_NAME}'. "
    "Please authenticate first using: claude-mpm auth login google"  # Wrong!
)
```

**Impact:** Users will be confused when trying to follow error instructions.

**Recommendation:** Update error messages to reference the correct CLI command:
```python
"Please authenticate first using: workspace setup"
```

---

#### DX-2: Inconsistent Tool Count Documentation
**Severity:** MEDIUM
**Files:**
- `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/cli/main.py` (line 17: "66 tools")
- `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/__init__.py` (line 3: "66 tools")
- CLAUDE.md mentions "65 tools"

**Issue:** Documentation inconsistency about the number of tools.

**Recommendation:** Audit and standardize tool count across all documentation.

---

#### DX-3: Tool Schema Definitions Lack Validation Constraints
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Lines:** 82-1503 (tool definitions)

**Issue:** JSON schemas for tools don't include validation constraints like `minLength`, `maxLength`, `minimum`, `maximum`, or `pattern` validation.

Example - current schema:
```python
"query": {
    "type": "string",
    "description": "Gmail search query",
}
```

**Recommendation:** Add validation constraints:
```python
"query": {
    "type": "string",
    "description": "Gmail search query",
    "minLength": 1,
    "maxLength": 500,
}
```

---

#### DX-4: Missing Input Validation in Tool Handlers
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`

**Issue:** Tool handlers rely on generic exception handling rather than explicit input validation. This leads to less helpful error messages.

Example at line 2455-2457:
```python
async def _send_email(self, arguments: dict[str, Any]) -> dict[str, Any]:
    to = arguments["to"]  # No validation
    subject = arguments["subject"]  # No validation
```

**Recommendation:** Add Pydantic models for input validation:
```python
class SendEmailInput(BaseModel):
    to: str = Field(..., min_length=1, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    subject: str = Field(..., min_length=1, max_length=998)
    body: str
```

---

#### DX-5: CLI Help Text Could Be More Detailed
**Severity:** LOW
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/cli/main.py`

**Issue:** CLI help text lacks examples and doesn't explain OAuth client setup.

**Recommendation:** Add examples and prerequisites:
```python
@click.option(
    "--client-id",
    envvar="GOOGLE_OAUTH_CLIENT_ID",
    help="Google OAuth client ID. Get from https://console.cloud.google.com/apis/credentials"
)
```

---

### Performance

#### PERF-1: HTTP Client Not Reused (Critical Performance Issue)
**Severity:** CRITICAL
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Lines:** 1584, 2077, 2089, 2388, 2639, 3108, 3142, 3178, 3736, 3778, 3911, 3931, 4100, 4340

**Issue:** A new `httpx.AsyncClient()` is created for every API request:

```python
async def _make_request(...):
    async with httpx.AsyncClient() as client:  # New client each time!
        response = await client.request(...)
```

**Impact:**
- Connection establishment overhead (TCP handshake + TLS) for every request
- No connection pooling or keepalive
- Estimated 100-300ms overhead per request
- For Gmail search (which fetches metadata for each message), this multiplies

**Recommendation:** Create a shared HTTP client with connection pooling:

```python
class GoogleWorkspaceServer:
    def __init__(self) -> None:
        self.server = Server("google-workspace-mcp")
        self.storage = TokenStorage()
        self.manager = OAuthManager(storage=self.storage)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._setup_handlers()

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                http2=True,  # Enable HTTP/2 for multiplexing
            )
        return self._http_client

    async def run(self) -> None:
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(...)
        finally:
            if self._http_client:
                await self._http_client.aclose()
```

---

#### PERF-2: Gmail Message Search Makes N+1 Requests
**Severity:** HIGH
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Lines:** 1869-1908

**Issue:** `_search_gmail_messages` makes a separate API call for each message:

```python
for msg in response.get("messages", []):
    # Individual request for EACH message
    msg_url = f"{GMAIL_API_BASE}/users/me/messages/{msg['id']}"
    msg_detail = await self._make_request("GET", msg_url, params={"format": "metadata"})
```

**Impact:** For `max_results=10`, this results in 11 HTTP requests instead of 1.

**Recommendation:** Use Gmail's batch API or the `fields` parameter in the list request:

```python
async def _search_gmail_messages(self, arguments: dict[str, Any]) -> dict[str, Any]:
    # Use batch request or adjust fields parameter
    url = f"{GMAIL_API_BASE}/users/me/messages"
    params = {
        "q": query,
        "maxResults": max_results,
        "fields": "messages(id,threadId,snippet,payload/headers)"
    }
```

Or implement parallel fetching:
```python
import asyncio

message_tasks = [
    self._make_request("GET", f"{GMAIL_API_BASE}/users/me/messages/{msg['id']}",
                       params={"format": "metadata"})
    for msg in response.get("messages", [])
]
message_details = await asyncio.gather(*message_tasks)
```

---

#### PERF-3: No Caching for Token Retrieval
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Line:** 1520-1559

**Issue:** Every API request reads the token from disk:

```python
async def _get_access_token(self) -> str:
    status = self.storage.get_status(SERVICE_NAME)  # Reads from disk
    ...
    stored = self.storage.retrieve(SERVICE_NAME)  # Reads from disk again
```

**Recommendation:** Cache the token in memory with expiration check:

```python
class GoogleWorkspaceServer:
    def __init__(self) -> None:
        ...
        self._cached_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._cached_token and self._token_expires_at and now < self._token_expires_at:
            return self._cached_token

        # Fetch and cache
        stored = self.storage.retrieve(SERVICE_NAME)
        if stored and not stored.token.is_expired():
            self._cached_token = stored.token.access_token
            self._token_expires_at = stored.token.expires_at
            return self._cached_token
```

---

#### PERF-4: Synchronous File Operations in Token Storage
**Severity:** LOW
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/auth/token_storage.py`
**Lines:** 82-100

**Issue:** File I/O is synchronous, which could block the event loop:

```python
with open(self.token_path, "r") as f:
    return json.load(f)
```

**Recommendation:** For high-throughput scenarios, consider using `aiofiles`:

```python
import aiofiles

async def _load_tokens_async(self) -> dict[str, dict]:
    async with aiofiles.open(self.token_path, "r") as f:
        content = await f.read()
        return json.loads(content)
```

---

### Code Quality

#### CQ-1: Monolithic Server File (4,552 lines)
**Severity:** HIGH
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`

**Issue:** Single file contains all 66 tool implementations, making it difficult to:
- Navigate and understand
- Test individual components
- Maintain and extend

**Recommendation:** Split into domain-specific modules:

```
src/google_workspace_mcp/server/
    __init__.py
    server.py              # Main server class and routing
    handlers/
        __init__.py
        calendar.py        # Calendar operations
        gmail.py           # Gmail operations
        drive.py           # Drive operations
        docs.py            # Docs operations
        tasks.py           # Tasks operations
    schemas/
        __init__.py
        calendar.py        # Calendar tool schemas
        gmail.py           # Gmail tool schemas
        ...
```

---

#### CQ-2: Inconsistent Service Name Constant
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Line:** 40

**Issue:** Service name uses "google-workspace-mcp" but OAuthManager uses "google-workspace":

```python
# In server
SERVICE_NAME = "google-workspace-mcp"

# In oauth_manager.py line 61
self._service_name = "google-workspace"
```

**Impact:** Token stored by one won't be found by the other.

**Recommendation:** Centralize service name constant:

```python
# In a shared constants module
GOOGLE_WORKSPACE_SERVICE_NAME = "google-workspace"
```

**UPDATE:** Upon closer inspection, OAuthManager uses "google-workspace" internally, but storage operations should align. This needs verification through testing.

---

#### CQ-3: Type Hints Could Be More Specific
**Severity:** LOW
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`

**Issue:** Extensive use of `dict[str, Any]` loses type safety:

```python
async def _list_calendars(self, arguments: dict[str, Any]) -> dict[str, Any]:
```

**Recommendation:** Define TypedDict or Pydantic models:

```python
from typing import TypedDict

class CalendarListResponse(TypedDict):
    calendars: list[CalendarInfo]
    count: int

class CalendarInfo(TypedDict):
    id: str
    summary: str
    description: Optional[str]
    access_role: str
    primary: bool
```

---

#### CQ-4: Error Handling Could Be More Granular
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`
**Lines:** 1508-1518

**Issue:** All exceptions are caught and converted to generic error messages:

```python
try:
    result = await self._dispatch_tool(name, arguments)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
except Exception as e:
    logger.exception(f"Error calling tool {name}")
    return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]
```

**Impact:**
- HTTP errors (rate limiting, authentication) look the same as validation errors
- No structured error codes for clients to handle programmatically

**Recommendation:** Implement structured error handling:

```python
from enum import Enum

class ErrorCode(str, Enum):
    AUTH_FAILED = "AUTH_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class GoogleWorkspaceError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

try:
    result = await self._dispatch_tool(name, arguments)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        raise GoogleWorkspaceError(ErrorCode.AUTH_FAILED, "Authentication required")
    elif e.response.status_code == 429:
        raise GoogleWorkspaceError(ErrorCode.RATE_LIMITED, "Rate limit exceeded")
except GoogleWorkspaceError as e:
    return [TextContent(type="text", text=json.dumps({
        "error": True,
        "code": e.code.value,
        "message": e.message,
        "details": e.details
    }, indent=2))]
```

---

#### CQ-5: Deprecated asyncio.get_event_loop() Usage
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/auth/oauth_manager.py`
**Lines:** 175, 236

**Issue:** Using deprecated `asyncio.get_event_loop()`:

```python
loop = asyncio.get_event_loop()
credentials = await loop.run_in_executor(None, self._run_oauth_flow, client_config, scopes)
```

**Impact:** Will cause deprecation warnings in Python 3.12+.

**Recommendation:** Use `asyncio.to_thread()` (Python 3.9+):

```python
credentials = await asyncio.to_thread(self._run_oauth_flow, client_config, scopes)
```

---

#### CQ-6: Missing Docstrings in Some Methods
**Severity:** LOW
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`

**Issue:** While most methods have good docstrings, some internal methods lack documentation:
- `_normalize_drive_query` (has docstring but could explain operators better)
- Helper functions in complex operations

**Recommendation:** Ensure all public and complex private methods have docstrings explaining parameters, return values, and potential exceptions.

---

### Security

#### SEC-1: Token Storage Without Encryption
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/auth/token_storage.py`
**Line:** 7 (documented)

**Issue:** Tokens are stored in plain JSON with file permissions as the only protection:

```python
# Tokens are stored in plaintext JSON
# File permissions set to 600, but no encryption
```

**Impact:** Compromised filesystem access exposes refresh tokens.

**Current Mitigation:** File permissions (0o600) are correctly set.

**Recommendation:** Document the security model clearly and consider optional encryption:

```python
class TokenStorage:
    """Simple JSON-based storage for OAuth tokens.

    Security Model:
    - Tokens stored in ~/.google-workspace-mcp/tokens.json
    - File permissions: 600 (owner read/write only)
    - Directory permissions: 700 (owner only)
    - No encryption - relies on filesystem security

    For enhanced security, consider:
    - keyring integration for token storage
    - Fernet encryption with keyring-stored key
    """
```

---

#### SEC-2: Input Sanitization for File Paths
**Severity:** MEDIUM
**File:** `/Users/masa/Projects/gworkspace-mcp/src/google_workspace_mcp/server/google_workspace_server.py`

**Issue:** Rclone operations accept paths without validation, which could lead to unintended file access.

**Recommendation:** Add path validation:

```python
import os

def _validate_local_path(self, path: str) -> str:
    """Validate and normalize local file path."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    # Optionally restrict to certain directories
    return abs_path
```

---

## Test Coverage Assessment

**Current State:**
- Unit tests exist for token storage, token models, and OAuth manager
- Integration test file exists but may be empty/minimal
- Test markers configured (unit, integration, slow)

**Gaps Identified:**
1. No unit tests for server tool handlers
2. No mock-based integration tests for Google API interactions
3. No CLI command tests
4. No error handling path tests

**Recommendation:** Prioritize testing for:
1. Tool handler input validation
2. Error response formatting
3. Token refresh scenarios
4. HTTP error handling (401, 429, 500)

---

## Configuration and Build

#### BUILD-1: pyproject.toml Well-Configured
**Assessment:** Good

The pyproject.toml demonstrates solid configuration:
- Proper Python version constraints (>=3.10)
- Comprehensive dev dependencies
- Ruff configured with sensible rules
- Mypy in strict mode
- Pytest with asyncio support

**Minor Improvement:** Consider adding `hatch` scripts for common tasks:

```toml
[tool.hatch.envs.default.scripts]
test = "pytest {args:tests}"
test-cov = "pytest --cov {args:tests}"
lint = "ruff check src tests"
format = "ruff format src tests"
typecheck = "mypy src"
```

---

## Prioritized Recommendations

### Critical (Fix Before Production)
1. **PERF-1:** Implement HTTP client connection pooling
2. **DX-1:** Fix error messages to reference correct CLI commands
3. **CQ-2:** Verify and align service name constants

### High Priority
4. **PERF-2:** Optimize Gmail search to avoid N+1 queries
5. **CQ-1:** Begin modularizing the server file
6. **CQ-4:** Implement structured error handling

### Medium Priority
7. **CQ-5:** Replace deprecated asyncio patterns
8. **DX-3/DX-4:** Add input validation with Pydantic models
9. **PERF-3:** Implement token caching
10. **SEC-2:** Add path validation for file operations

### Low Priority
11. **DX-2:** Standardize tool count documentation
12. **DX-5:** Improve CLI help text
13. **CQ-3:** Add TypedDict for response types
14. **CQ-6:** Complete docstring coverage

---

## Positive Observations

1. **Excellent Type Hints:** Consistent use of type annotations throughout
2. **Good Pydantic Usage:** Models in auth package are well-structured
3. **Proper Security Basics:** File permissions correctly set for tokens
4. **Clean Test Structure:** Well-organized test files with clear naming
5. **Comprehensive Tool Coverage:** 66 tools covering all major Google Workspace APIs
6. **Good Async Patterns:** Proper use of async/await (except for the deprecated loop pattern)
7. **Clear CLI Structure:** Click-based CLI with good command organization
8. **Solid Documentation:** Module-level docstrings explain purpose and usage

---

## Conclusion

The gworkspace-mcp project provides a solid foundation for Google Workspace integration via MCP. The critical issues around HTTP client management should be addressed before production deployment, as they will significantly impact performance and user experience. The code demonstrates good Python practices overall, with the main areas for improvement being performance optimization and code modularity.

**Estimated Effort for Critical Fixes:** 4-8 hours
**Estimated Effort for All High Priority:** 16-24 hours
**Estimated Effort for Full Remediation:** 40-60 hours

---

*Generated by Claude Code Research Agent*
*Session: 2026-02-10*
