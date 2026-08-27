from __future__ import annotations

import json

import pytest

from gf_dashboard.presentation.qt_bridge.app_bridge import AppBridge


@pytest.fixture
def bridge() -> AppBridge:
    return AppBridge()


def test_invoke_ping_returns_versioned_success(bridge: AppBridge) -> None:
    request = {
        "version": 1,
        "requestId": "request-1",
        "method": "system.ping",
        "payload": {},
    }

    response = json.loads(bridge.invoke(json.dumps(request)))

    assert response == {
        "version": 1,
        "requestId": "request-1",
        "ok": True,
        "data": {"message": "pong", "runtime": "desktop", "bridgeVersion": 1},
    }


@pytest.mark.parametrize(
    ("raw_request", "expected_code"),
    [
        ("not-json", "invalid_request"),
        (json.dumps({"version": 1}), "invalid_request"),
        (
            json.dumps(
                {
                    "version": 1,
                    "requestId": "request-2",
                    "method": "missing.method",
                    "payload": {},
                }
            ),
            "unknown_method",
        ),
    ],
)
def test_invoke_rejects_invalid_or_unknown_requests(
    bridge: AppBridge,
    raw_request: str,
    expected_code: str,
) -> None:
    response = json.loads(bridge.invoke(raw_request))

    assert response["ok"] is False
    assert response["error"]["code"] == expected_code
