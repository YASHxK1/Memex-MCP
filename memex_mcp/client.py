"""Small authenticated HTTP client for the Memex backend API."""

from typing import Any

import httpx

from .config import api_token, backend_url


def backend_settings() -> tuple[str, str]:
    return backend_url(), api_token()


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
        if not response.content:
            return None
        return response.json()
