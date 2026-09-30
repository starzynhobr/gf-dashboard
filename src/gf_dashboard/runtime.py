from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

DEV_URL_ENV = "GF_DASHBOARD_DEV_URL"
ALLOWED_DEV_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def bundle_root() -> Path:
    packaged_root = getattr(sys, "_MEIPASS", None)
    if packaged_root:
        return Path(packaged_root).resolve()
    return Path(__file__).resolve().parents[2]


def frontend_index_path() -> Path:
    return bundle_root() / "frontend" / "dist" / "index.html"


def app_icon_path() -> Path:
    ico_candidate = bundle_root() / "assets" / "app_icon.ico"
    if ico_candidate.is_file():
        return ico_candidate
    dev_ico = bundle_root() / "build_assets" / "app_icon.ico"
    if dev_ico.is_file():
        return dev_ico
    return bundle_root() / "frontend" / "src" / "assets" / "gf-farmer-mark.png"


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


def validation_profile_id(argv: list[str]) -> str | None:
    """Accept only a UUID profile for installed-package acceptance checks."""
    if "--validation-profile" not in argv[1:]:
        return None
    if len(argv) != 3 or argv[1] != "--validation-profile":
        raise ValueError("Use --validation-profile seguido de um UUID")
    return str(UUID(argv[2]))
