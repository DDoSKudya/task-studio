from __future__ import annotations

import re

_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "cf-challenge",
    "cf-turnstile",
    "challenge-platform",
    "just a moment",
    "checking your browser",
    "attention required",
    "enable javascript and cookies",
    "ddos-guard",
    "bot detection",
    "captcha-delivery",
    "hcaptcha.com",
    "challenges.cloudflare.com",
    "google.com/recaptcha",
    "g-recaptcha-response",
    "verify you are human",
    "are you a robot",
    "__cf_chl",
    "ray id",
)

_SCRIPT_TAG = re.compile(r"<script\b", re.I)
_P_TAG = re.compile(r"<p\b", re.I)
_ARTICLE_TAG = re.compile(r"<article\b", re.I)


def looks_like_challenge_html(raw: str) -> bool:
    sample = raw[:12_000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    scripts = len(_SCRIPT_TAG.findall(sample))
    paragraphs = len(_P_TAG.findall(sample))
    articles = len(_ARTICLE_TAG.findall(sample))
    return scripts >= 8 and paragraphs + articles <= 1 and len(sample) < 40_000
