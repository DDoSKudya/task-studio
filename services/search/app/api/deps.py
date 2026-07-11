from __future__ import annotations

from typing import Annotated

from app.config import SearchSettings
from fastapi import Depends, Request
from meilisearch.client import Client


def get_settings(request: Request) -> SearchSettings:
    return request.app.state.search_settings


def get_meili_client(request: Request) -> Client:
    return request.app.state.meili_client


type Settings = Annotated[SearchSettings, Depends(get_settings)]
type MeiliClient = Annotated[Client, Depends(get_meili_client)]
