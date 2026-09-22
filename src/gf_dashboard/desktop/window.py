from __future__ import annotations

import logging

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from gf_dashboard.infrastructure.persistence import SqliteDatabase
from gf_dashboard.presentation.qt_bridge.app_bridge import AppBridge
from gf_dashboard.runtime import app_icon_path, frontend_index_path, validated_dev_url

logger = logging.getLogger(__name__)


class RestrictedPage(QWebEnginePage):
    def __init__(self, allowed_origin: str | None, parent: QWebEngineView) -> None:
        super().__init__(parent)
        self._allowed_origin = allowed_origin

    def acceptNavigationRequest(
        self,
        url: QUrl | str,
        navigation_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        del navigation_type
        resolved_url = QUrl(url) if isinstance(url, str) else url
        if not is_main_frame:
            return True
        if resolved_url.scheme() in {"file", "qrc", "data", "about"}:
            return True
        if self._allowed_origin and resolved_url.toString().startswith(self._allowed_origin):
            return True
        QDesktopServices.openUrl(resolved_url)
        return False


class MainWindow(QMainWindow):
    def __init__(self, database: SqliteDatabase | None = None) -> None:
        super().__init__()
        self.setWindowTitle("GF Farmer")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 640)

        icon_path = app_icon_path()
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        dev_url = validated_dev_url()
        self.web_view = QWebEngineView(self)
        self.page = RestrictedPage(dev_url, self.web_view)
        self.web_view.setPage(self.page)
        self.setCentralWidget(self.web_view)

        self.bridge = AppBridge(database, self)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("appBridge", self.bridge)
        self.page.setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self._on_load_finished)

        if dev_url:
            self.web_view.setUrl(QUrl(dev_url))
        else:
            index_path = frontend_index_path()
            if not index_path.is_file():
                raise FileNotFoundError(
                    f"Frontend não compilado em {index_path}. "
                    "Execute npm --prefix frontend run build."
                )
            self.web_view.setUrl(QUrl.fromLocalFile(str(index_path)))

    def _on_load_finished(self, succeeded: bool) -> None:
        if succeeded:
            logger.info("Frontend carregado em %s", self.web_view.url().toString())
        else:
            logger.error("Falha ao carregar frontend em %s", self.web_view.url().toString())
