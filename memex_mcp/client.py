"""Small authenticated HTTP client for the Memex backend API."""

import os
from typing import Any

import httpx


def backend_settings() -> tuple[str, str]:
    base_url = os.environ.get("MEMEX_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("MEMEX_API_TOKEN")
    if not token:
        raise RuntimeError("MEMEX_API_TOKEN must be set")
    return base_url, token


async def request(method: str, path: str, *, json: dict[str, Any] | None = None,
                  params: dict[str, Any] | None = None) -> Any:
    base_url, token = backend_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{base_url}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=json,
            params=params,
        )
        response.raise_for_status()
        return response.json()
