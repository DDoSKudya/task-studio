from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatCompletionResult:
    content: str
    finish_reason: str | None = None
    max_tokens: int | None = None

    @property
    def truncated(self) -> bool:
        reason = (self.finish_reason or "").casefold()
        if reason in {"length", "max_tokens"}:
            return True
        text = self.content or ""
        if text.count("```") % 2 == 1:
            return True
        if not self.max_tokens or reason == "stop":
            return False
        chars_per_token = 2.8 if reason else 1.6
        return len(text) >= int(self.max_tokens * chars_per_token)
