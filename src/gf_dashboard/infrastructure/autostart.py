from __future__ import annotations

import logging
import sys
from typing import Protocol

logger = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "GFFarmer"


def get_default_command() -> str:
    """Returns the executable command line for Windows autostart."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m gf_dashboard'


class RegistryBackend(Protocol):
    def read_value(self, key_path: str, value_name: str) -> str | None: ...
    def write_value(self, key_path: str, value_name: str, value: str) -> None: ...
    def delete_value(self, key_path: str, value_name: str) -> None: ...


class WinregBackend:
    """Access Windows registry using standard winreg module."""

    def read_value(self, key_path: str, value_name: str) -> str | None:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, value_name)
                return str(val) if val else None
        except (FileNotFoundError, OSError):
            return None

    def write_value(self, key_path: str, value_name: str, value: str) -> None:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value)

    def delete_value(self, key_path: str, value_name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, value_name)
        except (FileNotFoundError, OSError):
            pass


class InMemoryRegistryBackend:
    """In-memory registry for testing and non-Windows fallback."""

    def __init__(self, initial_values: dict[str, str] | None = None) -> None:
        self.values: dict[str, str] = dict(initial_values or {})

    def read_value(self, key_path: str, value_name: str) -> str | None:
        return self.values.get(f"{key_path}\\{value_name}")

    def write_value(self, key_path: str, value_name: str, value: str) -> None:
        self.values[f"{key_path}\\{value_name}"] = value

    def delete_value(self, key_path: str, value_name: str) -> None:
        self.values.pop(f"{key_path}\\{value_name}", None)


class WindowsAutostartService:
    """Manages application autostart via Windows Registry (HKCU Run)."""

    def __init__(
        self,
        app_name: str = APP_NAME,
        command: str | None = None,
        backend: RegistryBackend | None = None,
    ) -> None:
        self._app_name = app_name
        self._command = command
        if backend is not None:
            self._backend = backend
        elif sys.platform == "win32":
            self._backend = WinregBackend()
        else:
            self._backend = InMemoryRegistryBackend()

    @property
    def command(self) -> str:
        return self._command if self._command is not None else get_default_command()

    def is_enabled(self) -> bool:
        try:
            val = self._backend.read_value(RUN_KEY_PATH, self._app_name)
            return bool(val)
        except Exception:
            logger.exception("Erro ao verificar autostart")
            return False

    def set_enabled(self, enabled: bool) -> bool:
        try:
            if enabled:
                self._backend.write_value(RUN_KEY_PATH, self._app_name, self.command)
                return True
            else:
                self._backend.delete_value(RUN_KEY_PATH, self._app_name)
                return False
        except Exception:
            logger.exception("Erro ao configurar autostart")
            return self.is_enabled()
