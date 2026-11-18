from __future__ import annotations

import json
import time
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.error import URLError

import pytest
from PySide6.QtCore import QTimer
from pytestqt.qtbot import QtBot

from gf_dashboard.application.fixtures import create_golden_fixture
from gf_dashboard.desktop.window import MainWindow
from gf_dashboard.infrastructure.migrations.runner import load_migrations
from gf_dashboard.infrastructure.persistence import MigrationRunner, SqliteDatabase
from gf_dashboard.infrastructure.sqlite_repositories import SqliteUnitOfWork
from tests.helpers import create_memory_context


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

    toolbar_heights: list[Any] = []

    def action_buttons_have_uniform_height() -> bool:
        window.page.runJavaScript(
            "JSON.stringify(Array.from(document.querySelectorAll('.page-title-actions > button'))"
            ".map((button) => button.getBoundingClientRect().height))",
            toolbar_heights.append,
        )
        return bool(toolbar_heights)

    qtbot.waitUntil(action_buttons_have_uniform_height, timeout=5_000)
    assert json.loads(toolbar_heights[-1]) == [50] * 6


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


@pytest.mark.integration
def test_tower_configuration_round_trip_in_built_react(qtbot: QtBot, tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "tower-smoke.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="test").migrate()
    _, ids, clock = create_memory_context()
    create_golden_fixture(SqliteUnitOfWork(database), ids, clock)
    window = MainWindow(database)
    qtbot.addWidget(window)
    window.resize(1680, 941)

    def evaluate(script: str) -> Any:
        results: list[Any] = []
        window.page.runJavaScript(script, results.append)
        qtbot.waitUntil(lambda: bool(results), timeout=5_000)
        return results[-1]

    def click_button(text: str) -> None:
        assert evaluate(
            "(() => { const button = [...document.querySelectorAll('button')]"
            ".find((element) => (element.getAttribute('aria-label')"
            f" || element.textContent.trim()) === {json.dumps(text)});"
            "if (!button || button.disabled) return false; button.click(); return true; })()"
        ), text

    def fill_field(label: str, value: str) -> None:
        assert evaluate(
            "(() => { const field = [...document.querySelectorAll('label')]"
            f".find((element) => element.textContent.trim() === {json.dumps(label)});"
            "const input = field?.querySelector('input'); if (!input) return false;"
            "Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call("
            f"input, {json.dumps(value)});"
            "input.dispatchEvent(new Event('input', {bubbles:true}));"
            "return true; })()"
        ), label

    def capture(name: str) -> None:
        evaluate(
            "window.towerQAPainted = false; requestAnimationFrame(() => "
            "requestAnimationFrame(() => { window.towerQAPainted = true; }));"
        )
        qtbot.waitUntil(lambda: evaluate("window.towerQAPainted === true"), timeout=5_000)
        # WebEngine's compositor presents a frame after the DOM/animation callbacks.
        qtbot.wait(150)
        assert window.grab().save(str(tmp_path / name))

    with qtbot.waitSignal(window.web_view.loadFinished, timeout=15_000) as signal:
        window.show()
    assert signal.args == [True]
    qtbot.waitUntil(
        lambda: "Online"
        in str(evaluate("document.querySelector('[data-testid=bridge-status]')?.textContent")),
        timeout=10_000,
    )
    click_button("Configurar Torre")
    qtbot.waitUntil(
        lambda: evaluate(
            "Boolean([...document.querySelectorAll('label')].find("
            "element => element.textContent.trim() === 'Guilda'))"
        ),
        timeout=10_000,
    )
    fill_field("Guilda", "Guilda de teste")
    fill_field("Custo da abertura (gold)", "30000")
    click_button("Adicionar item")
    fill_field("Nome do item 1", "Astúcia")
    fill_field("Valor estimado do item 1 (gold)", "200000")
    click_button("Salvar configuração")
    qtbot.waitUntil(
        lambda: evaluate(
            "[...document.querySelectorAll('[role=status]')]"
            ".some(element => element.textContent.includes('Configuração salva'))"
        ),
        timeout=10_000,
    )
    click_button("Fechar")
    qtbot.waitUntil(
        lambda: evaluate("document.querySelector('[role=dialog]') === null"), timeout=5_000
    )
    assert evaluate("document.body.textContent.includes('200.000 gold')")
    assert evaluate("document.body.textContent.includes('Itens da Torre')")
    assert evaluate("document.body.textContent.includes('Astúcia')")

    window.close()
    window = MainWindow(database)
    qtbot.addWidget(window)
    window.resize(1680, 941)
    with qtbot.waitSignal(window.web_view.loadFinished, timeout=15_000) as signal:
        window.show()
    assert signal.args == [True]
    qtbot.waitUntil(
        lambda: evaluate("document.body.textContent.includes('200.000 gold')"), timeout=10_000
    )
    capture("tower-items-home-1680x941.png")
    click_button("Configurar Torre")
    qtbot.waitUntil(
        lambda: evaluate(
            "[...document.querySelectorAll('input')]"
            ".some(input => input.value === 'Guilda de teste')"
        ),
        timeout=5_000,
    )

    for width, height in ((1680, 941), (1440, 810), (1280, 720)):
        window.resize(width, height)
        qtbot.waitUntil(
            lambda width=width: evaluate(f"window.innerWidth === {width}"), timeout=5_000
        )
        assert evaluate(
            "(() => { const dialog = document.querySelector('[role=dialog]');"
            "const rect = dialog.getBoundingClientRect();"
            "return rect.left >= 0 && rect.right <= innerWidth"
            "&& rect.top >= 0 && rect.bottom <= innerHeight"
            "&& dialog.scrollWidth <= dialog.clientWidth; })()"
        )
        capture(f"tower-configuration-{width}x{height}.png")

    window.resize(1680, 941)
    for scale in (1.25, 1.5):
        window.web_view.setZoomFactor(scale)
        qtbot.waitUntil(
            lambda scale=scale: evaluate(f"Math.abs(innerWidth - 1680 / {scale}) < 2"),
            timeout=5_000,
        )
        assert evaluate(
            "(() => { const dialog = document.querySelector('[role=dialog]');"
            "const rect = dialog.getBoundingClientRect();"
            "return rect.left >= 0 && rect.right <= innerWidth"
            "&& rect.top >= 0 && rect.bottom <= innerHeight"
            "&& dialog.scrollWidth <= dialog.clientWidth; })()"
        )
        capture(f"tower-configuration-zoom{int(scale * 100)}.png")

    connection = database.connect()
    try:
        assert connection.execute("SELECT COUNT(*) FROM farm_sessions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM farm_session_items").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        configuration = connection.execute(
            "SELECT guild_name, entry_cost_gold FROM tower_configurations"
        ).fetchone()
        assert tuple(configuration) == ("Guilda de teste", 30_000)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()

    window.web_view.setZoomFactor(1.0)
    click_button("Registrar sessão")
    qtbot.waitUntil(
        lambda: evaluate("document.body.textContent.includes('Quantidade de Astúcia')"),
        timeout=5_000,
    )
    assert evaluate(
        "[...document.querySelectorAll('label')]"
        ".find(element => element.textContent.trim() === 'Quantidade de Astúcia')"
        ".querySelector('input').value === '0'"
    )
    fill_field("Quantidade de Astúcia", "2")
    click_button("Confirmar sessão")
    qtbot.waitUntil(
        lambda: evaluate("document.querySelector('[role=dialog]') === null"), timeout=5_000
    )
    connection = database.connect()
    try:
        assert connection.execute("SELECT COUNT(*) FROM farm_sessions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM farm_session_items").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT entry_cost_gold_snapshot FROM tower_session_details"
            ).fetchone()[0]
            == 30_000
        )
        drop = connection.execute(
            "SELECT quantity, estimated_unit_value_at_drop FROM farm_session_items"
        ).fetchone()
        assert tuple(drop) == (2, 200_000)
    finally:
        connection.close()
    print(f"Torre QA: {tmp_path}")
