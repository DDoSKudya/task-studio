from __future__ import annotations

import uuid
from dataclasses import dataclass


class PackError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class UploadedPack:
    pack_id: uuid.UUID
    version_id: uuid.UUID
    slug: str
    title: str
    version: str
