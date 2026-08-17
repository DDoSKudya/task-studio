from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.domain.errors import TutorError
from fastapi import status

_FETCH_TIMEOUT = 25.0
_MAX_REDIRECTS = 5
MAX_BATCH_URLS = 20

_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"'`|,;]+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:!?)】」』\"'"
_URL_LIST_SPLIT = re.compile(r"[\n\r,;|]+")

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Linux"',
}

_READER_HEADERS = {
    "User-Agent": _BROWSER_HEADERS["User-Agent"],
    "Accept": "text/markdown,text/plain,*/*;q=0.8",
    "Accept-Language": _BROWSER_HEADERS["Accept-Language"],
    "X-Return-Format": "markdown",
}


def is_blocked_host(hostname: str) -> bool:
    host = hostname.strip(".").lower()
    if not host or host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def _strip_url_noise(raw: str) -> str:
    text = (raw or "").strip()
    while text and text[-1] in _TRAILING_PUNCT:
        text = text[:-1]
    return text.strip()


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise TutorError(status.HTTP_400_BAD_REQUEST, "url must be http or https")
    if not parsed.hostname:
        raise TutorError(status.HTTP_400_BAD_REQUEST, "url host required")
    if parsed.username or parsed.password:
        raise TutorError(status.HTTP_400_BAD_REQUEST, "url credentials not allowed")
    if is_blocked_host(parsed.hostname):
        raise TutorError(status.HTTP_400_BAD_REQUEST, "url host is not allowed")
    return parsed.geturl()


def extract_http_urls(*chunks: str, limit: int = MAX_BATCH_URLS) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    cap = max(1, min(limit, MAX_BATCH_URLS))

    def add(candidate: str) -> None:
        cleaned = _strip_url_noise(candidate)
        if not cleaned.startswith(("http://", "https://")):
            return
        try:
            normalized = validate_public_http_url(cleaned)
        except TutorError:
            return
        if normalized in seen:
            return
        seen.add(normalized)
        found.append(normalized)

    for chunk in chunks:
        if not chunk:
            continue
        for line in _URL_LIST_SPLIT.sub("\n", chunk).splitlines():
            piece = line.strip()
            if piece.startswith(("http://", "https://")) and " " not in piece:
                add(piece)
        for match in _URL_IN_TEXT.finditer(chunk):
            add(match.group(0))
            if len(found) >= cap:
                return found[:cap]
    return found[:cap]
