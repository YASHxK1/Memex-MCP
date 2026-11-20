"""Environment and command-line configuration for the MCP server."""

import argparse
import os
from dataclasses import dataclass
from typing import Literal

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def backend_url() -> str:
    """Return the configured Memex Backend base URL without a trailing slash."""
    return os.environ.get("MEMEX_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def api_token() -> str:
    """Return the shared Memex bearer token, or fail if it is not configured."""
    token = os.environ.get("MEMEX_API_TOKEN")
    if not token:
        raise RuntimeError("MEMEX_API_TOKEN must be set")
    return token


def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def allowed_hosts() -> list[str]:
    """Return optional Host header allowlist for DNS rebinding protection."""
    return _csv_env("MCP_ALLOWED_HOSTS")


def allowed_origins() -> list[str]:
    """Return optional Origin header allowlist for DNS rebinding protection."""
    return _csv_env("MCP_ALLOWED_ORIGINS")


@dataclass(frozen=True)
class ServerConfig:
    """Resolved transport and listener configuration."""

    transport: Literal["stdio", "http"]
    host: str
    port: int


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _host(value: str) -> str:
    host = value.strip()
    if not host:
        raise argparse.ArgumentTypeError("host must not be empty")
    return host


def _default_host() -> str:
    return os.environ.get("MCP_HOST") or DEFAULT_HOST


def _default_port() -> str:
    # PORT is a common platform-provided port (for example Render and Heroku).
    return os.environ.get("MCP_PORT") or os.environ.get("PORT") or str(DEFAULT_PORT)


def load_server_config(argv: list[str] | None = None) -> ServerConfig:
    """Parse CLI flags, falling back to environment variables and defaults."""
    parser = argparse.ArgumentParser(
        prog="memex-mcp",
        description="Memex MCP server (local stdio or remote Streamable HTTP)",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="transport to serve (default: stdio)",
    )
    parser.add_argument(
        "--host",
        type=_host,
        default=_default_host(),
        help=f"HTTP bind host (default: MCP_HOST or {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=_default_port(),
        help=f"HTTP bind port (default: MCP_PORT, PORT, or {DEFAULT_PORT})",
    )
    args = parser.parse_args(argv)
    return ServerConfig(transport=args.transport, host=args.host, port=args.port)
