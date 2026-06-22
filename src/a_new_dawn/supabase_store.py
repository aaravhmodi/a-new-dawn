from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from a_new_dawn.settings import get_settings


class SupabaseStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.supabase_url
        self.server_key = settings.resolved_server_key
        self.publishable_key = settings.resolved_publishable_key

    def signup(self, *, email: str, password: str, handle: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/auth/v1/signup",
            auth_key=self.publishable_key,
            json={"email": email, "password": password, "data": {"handle": handle}},
        )

    def login(self, *, email: str, password: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/auth/v1/token?grant_type=password",
            auth_key=self.publishable_key,
            json={"email": email, "password": password},
        )

    def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request(
            "POST",
            f"/rest/v1/{table}",
            headers={"Prefer": "return=representation"},
            json=payload,
        )
        return data[0]

    def bulk_insert(self, table: str, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._request(
            "POST",
            f"/rest/v1/{table}",
            headers={"Prefer": "return=representation"},
            json=payload,
        )

    def select_one(self, table: str, *, filters: dict[str, Any], order: str | None = None) -> dict[str, Any] | None:
        rows = self.select(table, filters=filters, limit=1, order=order)
        return rows[0] if rows else None

    def select(self, table: str, *, filters: dict[str, Any] | None = None, limit: int | None = None, order: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {"select": "*"}
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        if limit is not None:
            params["limit"] = str(limit)
        if order:
            params["order"] = order
        return self._request("GET", f"/rest/v1/{table}", params=params)

    def update(self, table: str, *, filters: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        return self._request(
            "PATCH",
            f"/rest/v1/{table}",
            params=params,
            headers={"Prefer": "return=representation"},
            json=payload,
        )

    def upsert(self, table: str, *, payload: dict[str, Any], on_conflict: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            f"/rest/v1/{table}",
            params={"on_conflict": on_conflict},
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            json=payload,
        )
        return data[0]

    def healthcheck_rest(self) -> dict[str, Any]:
        return self._request("GET", "/rest/v1/", params={})

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth_key: str | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json: Any = None,
    ) -> Any:
        key = auth_key or self.server_key
        request_headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }
        if headers:
            request_headers.update(headers)
        response = httpx.request(
            method,
            f"{self.base_url}{path}",
            headers=request_headers,
            params=params,
            json=json,
            timeout=60.0,
        )
        response.raise_for_status()
        if not response.text:
            return {}
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text
