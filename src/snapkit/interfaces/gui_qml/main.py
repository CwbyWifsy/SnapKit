from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from snapkit.app.service import SnapKitService
from snapkit.infra.db.repo_sqlalchemy import SqlAlchemyToolboxRepository
from snapkit.interfaces.gui_qml.viewmodels.app_list_vm import AppListViewModel


def run_gui(engine):
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    QQuickStyle.setStyle("Basic")

    qapp = QApplication.instance() or QApplication(sys.argv)

    repository = SqlAlchemyToolboxRepository(engine)
    service = SnapKitService(repository, engine)
    view_model = AppListViewModel(service)

    qml_engine = QQmlApplicationEngine()
    qml_engine.rootContext().setContextProperty("appVm", view_model)

    qml_file = Path(__file__).resolve().parent / "qml" / "Main.qml"
    qml_engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not qml_engine.rootObjects():
        raise RuntimeError(f"QML load failed: {qml_file}")

    view_model.refresh("local_scan", "")
    sys.exit(qapp.exec())
