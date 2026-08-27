from __future__ import annotations

import pytest

from gf_dashboard.runtime import validated_dev_url


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:5173", "http://localhost:4173", "http://[::1]:5173"],
)
def test_validated_dev_url_accepts_local_http(url: str) -> None:
    assert validated_dev_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:5173",
        "http://example.com:5173",
        "http://user:password@localhost:5173",
        "http://localhost:5173?token=secret",
    ],
)
def test_validated_dev_url_rejects_non_local_or_credentialed_urls(url: str) -> None:
    with pytest.raises(ValueError, match="GF_DASHBOARD_DEV_URL"):
        validated_dev_url(url)
