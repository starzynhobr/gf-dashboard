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


def test_validation_profile_requires_uuid_and_exact_arguments() -> None:
    from gf_dashboard.runtime import validation_profile_id

    profile = "12345678-1234-4234-8234-123456789abc"
    assert validation_profile_id(["app"]) is None
    assert validation_profile_id(["app", "--validation-profile", profile]) == profile
    for arguments in (
        ["app", "--validation-profile"],
        ["app", "--validation-profile", "../personal"],
        ["app", "--validation-profile", profile, "extra"],
    ):
        with pytest.raises(ValueError):
            validation_profile_id(arguments)


def test_validation_application_uses_separate_qt_data_path() -> None:
    import os
    import subprocess
    import sys

    profile = "12345678-1234-4234-8234-123456789abc"
    code = (
        "from gf_dashboard.bootstrap import create_application; "
        "from gf_dashboard.infrastructure.persistence import resolve_personal_database_path; "
        "app=create_application(['app','--validation-profile','" + profile + "']); "
        "print(resolve_personal_database_path())"
    )
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, text=True, capture_output=True, check=True
    )
    assert f"GF Farmer Validation {profile}" in result.stdout
    assert "qttest" in result.stdout.lower()
    assert result.stdout.strip().endswith("gf-dashboard.sqlite3")
