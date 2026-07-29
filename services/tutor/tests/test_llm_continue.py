from __future__ import annotations

from app.domain.llm.result import ChatCompletionResult


def test_chat_completion_result_detects_length_finish() -> None:
    result = ChatCompletionResult(content="partial", finish_reason="length", max_tokens=100)
    assert result.truncated is True


def test_chat_completion_result_detects_open_fence() -> None:
    result = ChatCompletionResult(
        content="## Title\n```python\nprint(1)",
        finish_reason="stop",
        max_tokens=8000,
    )
    assert result.truncated is True


def test_chat_completion_result_near_budget_without_finish_reason() -> None:
                                                                                  
    content = "x" * 3000
    result = ChatCompletionResult(content=content, finish_reason="stop", max_tokens=1000)
    assert result.truncated is True


def test_chat_completion_result_complete_short_answer() -> None:
    result = ChatCompletionResult(
        content="Short complete chapter.",
        finish_reason="stop",
        max_tokens=4000,
    )
    assert result.truncated is False
