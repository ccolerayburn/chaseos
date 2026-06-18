"""Optional OpenAI-backed improv client with offline-safe failure behavior."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class ImprovUnavailable(RuntimeError):
    """Raised when the optional improv API path is disabled or unavailable."""


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class ImprovClient(Protocol):
    def respond(self, history: list[Message]) -> str:
        """Return the next yes-and response."""


class OpenAIImprovClient:
    """Minimal OpenAI chat client gated by env opt-in."""

    def __init__(self) -> None:
        self.enabled = os.environ.get("CHASEOS_IMPROV_API", "").lower() in {"1", "true", "yes"}
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("CHASEOS_IMPROV_MODEL", "gpt-4.1-mini")

    def respond(self, history: list[Message]) -> str:
        if not self.enabled:
            raise ImprovUnavailable("optional improv API is disabled")
        if not self.api_key:
            raise ImprovUnavailable("OPENAI_API_KEY is not set")

        payload = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in history],
            "temperature": 0.85,
            "max_tokens": 140,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise ImprovUnavailable(str(exc)) from exc

        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ImprovUnavailable("improv API returned an unexpected response") from exc
        text = str(content).strip()
        if not text:
            raise ImprovUnavailable("improv API returned an empty response")
        return text
