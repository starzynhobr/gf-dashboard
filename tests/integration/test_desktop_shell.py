from __future__ import annotations

import time
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.error import URLError

import pytest
from PySide6.QtCore import QTimer
from pytestqt.qtbot import QtBot

from gf_dashboard.desktop.window import MainWindow
from gf_dashboard.infrastructure.migrations.runner import load_migrations
from gf_dashboard.infrastructure.persistence import MigrationRunner, SqliteDatabase


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


@pytest.mark.integration
def test_calculator_opens_without_waiting_for_currency_network(
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = SqliteDatabase(tmp_path / "calculator-smoke.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="test").migrate()

    network_attempts = 0

    def slow_currency_api(*_args: object, **_kwargs: object) -> None:
        nonlocal network_attempts
        network_attempts += 1
        time.sleep(0.35)
        raise URLError("simulated slow currency API")

    monkeypatch.setattr("urllib.request.urlopen", slow_currency_api)
    window = MainWindow(database)
    qtbot.addWidget(window)

    with qtbot.waitSignal(window.web_view.loadFinished, timeout=15_000) as load_signal:
        window.show()

    assert load_signal.args == [True]

    observed: list[Any] = []

    def calculator_is_ready() -> bool:
        window.page.runJavaScript(
            "document.querySelector('[data-testid=bridge-status]')?.textContent ?? ''",
            observed.append,
        )
        return bool(observed and "Online" in str(observed[-1]))

    qtbot.waitUntil(calculator_is_ready, timeout=10_000)

    qt_timer_elapsed: list[float] = []
    timer_started = perf_counter()
    QTimer.singleShot(100, lambda: qt_timer_elapsed.append(perf_counter() - timer_started))

    triggered: list[Any] = []
    window.page.runJavaScript(
        """(() => {
          const button = [...document.querySelectorAll('button')]
            .find((element) => element.textContent?.includes('Calculadora'));
          if (!button) return false;
          button.click();
          return true;
        })()""",
        triggered.append,
    )
    qtbot.waitUntil(lambda: bool(triggered), timeout=5_000)
    assert triggered[-1] is True

    dialog_states: list[Any] = []

    def calculator_is_open() -> bool:
        window.page.runJavaScript(
            "Boolean(document.querySelector('[role=dialog][aria-label=\"Calculadora de gold\"]'))",
            dialog_states.append,
        )
        return bool(dialog_states and dialog_states[-1])

    qtbot.waitUntil(calculator_is_open, timeout=5_000)
    qtbot.waitUntil(lambda: bool(qt_timer_elapsed), timeout=5_000)
    assert perf_counter() - timer_started < 0.5
    assert qt_timer_elapsed[-1] < 0.5
    assert network_attempts == 0
