from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

DEV_URL_ENV = "GF_DASHBOARD_DEV_URL"
ALLOWED_DEV_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def bundle_root() -> Path:
    packaged_root = getattr(sys, "_MEIPASS", None)
    if packaged_root:
        return Path(packaged_root).resolve()
    return Path(__file__).resolve().parents[2]


def frontend_index_path() -> Path:
    return bundle_root() / "frontend" / "dist" / "index.html"


def validated_dev_url(raw_url: str | None = None) -> str | None:
    candidate = raw_url if raw_url is not None else os.getenv(DEV_URL_ENV)
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme != "http" or parsed.hostname not in ALLOWED_DEV_HOSTS:
        raise ValueError(f"{DEV_URL_ENV} deve usar HTTP em localhost")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"{DEV_URL_ENV} não pode conter credenciais, query ou fragmento")
    return candidate.rstrip("/")
