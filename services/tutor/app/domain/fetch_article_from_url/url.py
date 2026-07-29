from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.domain.errors import TutorError
from fastapi import status

_FETCH_TIMEOUT = 25.0
_MAX_REDIRECTS = 5
_MAX_RAW_CHARS = 120_000

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
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


                                                            
_is_blocked_host = is_blocked_host
