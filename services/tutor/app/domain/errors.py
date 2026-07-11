from __future__ import annotations


class TutorError(Exception):
    __slots__ = ("status_code", "detail")

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
