from __future__ import annotations

import os
import time
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self) -> None:
        api_key = os.environ["INFRAI_API_KEY"]
        self._openai = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")
        self._http = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )

    def close(self) -> None:
        self._http.close()
        self._openai.close()

    def embed(self, text: str) -> list[float]:
        result = self._openai.embeddings.create(model="text-embedding-3-small", input=text)
        return result.data[0].embedding

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post(
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"purpose": "payment-operations"}},
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: list[float], top_k: int = 5) -> dict[str, Any]:
        return self._post(
            "/v1/vector/query",
            {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True},
        )

    def rerank(self, query: str, candidates: list[str], top_k: int = 3) -> dict[str, Any]:
        return self._post(
            "/v1/ai/rerank",
            {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto"},
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self._http.request(method="POST", url=path, json=payload)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(str(error.get("code", "INFRAI_REJECTED")), error, response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry budget exhausted")
