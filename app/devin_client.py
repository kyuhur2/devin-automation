import os
from typing import Any

import httpx


class DevinClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("DEVIN_API_KEY")
        self.org_id = os.environ.get("DEVIN_ORG_ID")
        self.base_url = os.environ.get("DEVIN_API_BASE_URL", "https://api.devin.ai").rstrip("/")

        if not self.api_key:
            raise RuntimeError("DEVIN_API_KEY is required")
        if not self.org_id:
            raise RuntimeError("DEVIN_ORG_ID is required for the v3 organization sessions API")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def sessions_url(self) -> str:
        return f"{self.base_url}/v3/organizations/{self.org_id}/sessions"

    def session_url(self, devin_session_id: str) -> str:
        return f"{self.sessions_url}/{devin_session_id}"

    async def create_session(self, prompt: str) -> dict[str, Any]:
        payload = {"prompt": prompt}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.sessions_url,
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()
            return response.json()

    async def get_session(self, devin_session_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                self.session_url(devin_session_id),
                headers=self.headers,
            )

            response.raise_for_status()
            return response.json()