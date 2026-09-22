import json

from gf_dashboard.infrastructure.autostart import (
    InMemoryRegistryBackend,
    WindowsAutostartService,
)
from gf_dashboard.presentation.qt_bridge.app_bridge import AppBridge


def test_autostart_service_toggle():
    backend = InMemoryRegistryBackend()
    service = WindowsAutostartService(
        app_name="GFFarmerTest",
        command="gffarmer.exe",
        backend=backend,
    )

    reg_key = r"Software\Microsoft\Windows\CurrentVersion\Run\GFFarmerTest"

    assert not service.is_enabled()
    assert service.set_enabled(True) is True
    assert service.is_enabled() is True
    assert backend.values[reg_key] == "gffarmer.exe"

    assert service.set_enabled(False) is False
    assert service.is_enabled() is False
    assert reg_key not in backend.values


def test_app_bridge_autostart_integration():
    backend = InMemoryRegistryBackend()
    service = WindowsAutostartService(
        app_name="GFFarmerTest",
        command="gffarmer.exe",
        backend=backend,
    )
    bridge = AppBridge(database=None, autostart_service=service)

    # 1. Query initial autostart status
    req1 = json.dumps({"version": 1, "requestId": "req-1", "method": "system.getAutostart"})
    res1 = json.loads(bridge.invoke(req1))
    assert res1["ok"] is True
    assert res1["data"]["enabled"] is False

    # 2. Enable autostart
    req2 = json.dumps(
        {
            "version": 1,
            "requestId": "req-2",
            "method": "system.setAutostart",
            "payload": {"enabled": True},
        }
    )
    res2 = json.loads(bridge.invoke(req2))
    assert res2["ok"] is True
    assert res2["data"]["enabled"] is True
    assert service.is_enabled() is True

    # 3. Disable autostart
    req3 = json.dumps(
        {
            "version": 1,
            "requestId": "req-3",
            "method": "system.setAutostart",
            "payload": {"enabled": False},
        }
    )
    res3 = json.loads(bridge.invoke(req3))
    assert res3["ok"] is True
    assert res3["data"]["enabled"] is False
    assert service.is_enabled() is False
