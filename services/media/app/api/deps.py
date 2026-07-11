from __future__ import annotations

from typing import Annotated

from app.config import MediaSettings
from fastapi import Depends, Request
from minio import Minio


def get_media_settings(request: Request) -> MediaSettings:
    return request.app.state.media_settings


def get_minio_client(request: Request) -> Minio:
    return request.app.state.minio_client


type Settings = Annotated[MediaSettings, Depends(get_media_settings)]
type MinioClient = Annotated[Minio, Depends(get_minio_client)]
