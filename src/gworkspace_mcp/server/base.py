"""BaseService with shared HTTP helpers for Google Workspace MCP server."""

import json
import logging
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Any

import httpx

from gworkspace_mcp.auth import OAuthManager, TokenStatus, TokenStorage
from gworkspace_mcp.server.constants import MERMAID_CLI_VERSION, MERMAID_TIMEOUT, SERVICE_NAME

logger = logging.getLogger(__name__)


class BaseService:
    """Shared infrastructure for Google Workspace service operations.

    Provides OAuth token management, HTTP client pooling, and common
    request helpers used by all service modules.

    Attributes:
        storage: TokenStorage for retrieving OAuth tokens.
        manager: OAuthManager for token refresh operations.
    """

    def __init__(self) -> None:
        """Initialize base service with token storage and HTTP client."""
        self.storage = TokenStorage()
        self.manager = OAuthManager(storage=self.storage)
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create shared HTTP client with connection pooling.

        Returns:
            Shared httpx.AsyncClient instance.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                http2=True,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._http_client

    async def close(self) -> None:
        """Close the shared HTTP client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _render_mermaid_image(
        self,
        mermaid_code: str,
        output_format: str = "png",
        theme: str = "default",
        background: str = "white",
    ) -> bytes:
        """Render a single Mermaid diagram to image bytes using mermaid-cli.

        Args:
            mermaid_code: The Mermaid diagram source code.
            output_format: Output format ('svg' or 'png').
            theme: Mermaid theme ('default', 'dark', 'forest', 'neutral').
            background: Background color (e.g. 'white', 'transparent').

        Returns:
            Rendered image as bytes.

        Raises:
            RuntimeError: If npx is unavailable, rendering fails, or times out.
        """
        # Verify npx is available
        try:
            subprocess.run(  # nosec B603 B607 - npx is a trusted executable
                ["npx", "--version"],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError as err:
            raise RuntimeError(
                "npx is not installed. Install Node.js for mermaid support:\n"
                "  https://nodejs.org/"
            ) from err

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_path = tmpdir_path / "diagram.mmd"
            output_path = tmpdir_path / f"diagram.{output_format}"
            config_path = tmpdir_path / "mermaid-config.json"

            input_path.write_text(mermaid_code.strip(), encoding="utf-8")

            mermaid_config: dict[str, Any] = {"theme": theme}
            mermaid_config["backgroundColor"] = (
                "transparent" if background == "transparent" else background
            )
            config_path.write_text(json.dumps(mermaid_config), encoding="utf-8")

            try:
                result = subprocess.run(  # nosec B603 B607 - controlled paths
                    [
                        "npx",
                        "-y",
                        MERMAID_CLI_VERSION,
                        "-i",
                        str(input_path),
                        "-o",
                        str(output_path),
                        "-c",
                        str(config_path),
                    ],
                    capture_output=True,
                    check=True,
                    text=True,
                    timeout=MERMAID_TIMEOUT,
                )
                logger.info("Mermaid rendering output: %s", result.stdout)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Mermaid rendering failed: {e.stderr}\n"
                    "Check syntax at https://mermaid.js.org/intro/"
                ) from e
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"Mermaid rendering timed out (>{MERMAID_TIMEOUT}s). "
                    "Simplify the diagram or try again."
                ) from e

            if not output_path.exists():
                raise RuntimeError(f"Mermaid-cli failed to create output file: {output_path}")

            image_bytes = output_path.read_bytes()
            logger.info("Rendered Mermaid diagram: %d bytes (%s)", len(image_bytes), output_format)
            return image_bytes

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            RuntimeError: If no token is available or refresh fails.
        """
        status = self.storage.get_status(SERVICE_NAME)

        if status == TokenStatus.MISSING:
            raise RuntimeError(
                f"No OAuth token found for service '{SERVICE_NAME}'. "
                "Please authenticate first using: workspace setup"
            )

        if status == TokenStatus.INVALID:
            raise RuntimeError(
                f"OAuth token for service '{SERVICE_NAME}' is invalid or corrupted. "
                "Please re-authenticate using: workspace setup"
            )

        # Try to refresh if expired
        if status == TokenStatus.EXPIRED:
            logger.info("Token expired, attempting refresh...")
            token = await self.manager.refresh_if_needed()
            if token is None:
                raise RuntimeError(
                    "Token refresh failed. Please re-authenticate using: workspace setup"
                )
            return token.access_token

        # Token is valid
        stored = self.storage.retrieve(SERVICE_NAME)
        if stored is None:
            raise RuntimeError("Unexpected error: token retrieval failed")

        return stored.token.access_token

    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated HTTP request to Google APIs.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            params: Optional query parameters.
            json_data: Optional JSON body data.

        Returns:
            JSON response as a dictionary.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        access_token = await self._get_access_token()
        client = await self._get_http_client()

        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def _make_delete_request(self, url: str) -> None:
        """Make an authenticated DELETE request to Google APIs.

        Args:
            url: Full URL to request.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        access_token = await self._get_access_token()
        client = await self._get_http_client()

        response = await client.delete(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()

    async def _make_raw_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        content: bytes | str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Make an authenticated HTTP request returning raw response.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            params: Optional query parameters.
            content: Optional raw body content.
            headers: Optional additional headers.
            timeout: Request timeout in seconds.

        Returns:
            Raw httpx.Response object.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        access_token = await self._get_access_token()
        client = await self._get_http_client()

        request_headers = {"Authorization": f"Bearer {access_token}"}
        if headers:
            request_headers.update(headers)

        response = await client.request(
            method=method,
            url=url,
            params=params,
            content=content,
            headers=request_headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response
