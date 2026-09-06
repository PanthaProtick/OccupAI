from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.assistant.provider import AssistantProviderRequest


_MODEL_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAssistantProvider:
    """Fixed-purpose Gemini phrasing adapter with no tools or data access."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        if not api_key.strip():
            raise ValueError("Gemini requires ASSISTANT_API_KEY")
        if not _MODEL_NAME.fullmatch(model):
            raise ValueError("ASSISTANT_MODEL is not a valid Gemini model identifier")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def rewrite(self, request: AssistantProviderRequest) -> str:
        safe_results = [result.model_dump(mode="json") for result in request.results]
        body = {
            "systemInstruction": {
                "parts": [{
                    "text": (
                        "Improve the wording of the supplied OccupAI answer. Preserve its meaning. "
                        "Use only facts in the supplied verified results and deterministic answer. "
                        "Do not add rooms, numbers, percentages, claims, advice, links, or availability "
                        "guarantees. Return plain text only."
                    )
                }]
            },
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": json.dumps({
                        "deterministic_answer": request.deterministic_answer,
                        "verified_results": safe_results,
                    }, separators=(",", ":"), ensure_ascii=False)
                }],
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
            },
        }
        http_request = Request(
            f"{_BASE_URL}/{self._model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Gemini phrasing request failed") from exc
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            answer = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise RuntimeError("Gemini returned an invalid response") from exc
        if not answer:
            raise RuntimeError("Gemini returned an empty response")
        return answer
