from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from gf_dashboard import __version__
from gf_dashboard.desktop.window import MainWindow
from gf_dashboard.infrastructure.persistence import (
    PersistenceError,
    SqliteDatabase,
    migrate_personal_database,
)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_application(argv: list[str] | None = None) -> QApplication:
    QCoreApplication.setOrganizationName("STZ Labs")
    QCoreApplication.setApplicationName("GF Farmer")
    QCoreApplication.setApplicationVersion(__version__)
    return QApplication(argv if argv is not None else sys.argv)


def main() -> int:
    configure_logging()
    app = create_application()
    try:
        database_path = migrate_personal_database(app_version=app.applicationVersion())
        logging.getLogger(__name__).info("Banco local preparado em %s", database_path)
    except PersistenceError:
        logging.getLogger(__name__).exception("Não foi possível preparar o banco local")
        return 1
    window = MainWindow(SqliteDatabase(database_path))
    window.show()
    return app.exec()
