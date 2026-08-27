from __future__ import annotations

from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from gf_dashboard.desktop.window import MainWindow


@pytest.mark.integration
def test_desktop_shell_loads_built_react_and_connects_bridge(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    with qtbot.waitSignal(window.web_view.loadFinished, timeout=15_000) as load_signal:
        window.show()

    assert load_signal.args == [True]

    observed: list[Any] = []

    def bridge_is_ready() -> bool:
        window.page.runJavaScript(
            "document.querySelector('[data-testid=bridge-status]')?.textContent ?? ''",
            observed.append,
        )
        return bool(observed and "Online" in str(observed[-1]))

    qtbot.waitUntil(bridge_is_ready, timeout=10_000)
