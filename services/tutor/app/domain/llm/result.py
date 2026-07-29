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
                                                                                      
        return bool(self.max_tokens and len(text) >= int(self.max_tokens * 2.8))
