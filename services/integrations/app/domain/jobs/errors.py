from __future__ import annotations


class JobError(Exception):
    __slots__ = ("detail",)

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)
