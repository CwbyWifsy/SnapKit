"""PySide6 single-window GUI for SnapKit."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

from snapkit.db import get_session, init_db
from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


class MainWindow(QMainWindow):
    def __init__(self, engine: Engine):
        super().__init__()
        self._engine = engine
        init_db(engine)
        self.setWindowTitle("SnapKit")
        self.setMinimumSize(900, 600)

        tabs = QTabWidget()
        tabs.addTab(self._build_installed_tab(), "Installed Apps")
        tabs.addTab(self._build_pinned_tab(), "Pinned Apps")
        tabs.addTab(self._build_notinstalled_tab(), "Not Installed")
        tabs.addTab(self._build_resources_tab(), "Resources")
        self.setCentralWidget(tabs)

        self._refresh_all()

    def _session(self):
        return get_session(self._engine)

    # ── Installed Apps tab ────────────────────────────────────────────

    def _build_installed_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._installed_search = QLineEdit()
        self._installed_search.setPlaceholderText("Search installed apps...")
        self._installed_search.textChanged.connect(self._refresh_installed)
        layout.addWidget(self._installed_search)

        self._installed_table = QTableWidget()
        self._installed_table.setColumnCount(5)
        self._installed_table.setHorizontalHeaderLabels(["ID", "Name", "Publisher", "Version", "Tags"])
        self._installed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._installed_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._installed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._installed_table)

        btns = QHBoxLayout()
        scan_btn = QPushButton("Scan (Mock)")
        scan_btn.clicked.connect(self._on_scan_mock)
        pin_btn = QPushButton("Pin Selected")
        pin_btn.clicked.connect(self._on_pin_selected)
        btns.addWidget(scan_btn)
        btns.addWidget(pin_btn)
        btns.addStretch()
        layout.addLayout(btns)
        return w

    def _refresh_installed(self):
        session = self._session()
        query = session.query(InstalledApp)
        search = self._installed_search.text().strip()
        if search:
            query = query.filter(InstalledApp.name.ilike(f"%{search}%"))
        apps = query.order_by(InstalledApp.name).all()

        self._installed_table.setRowCount(len(apps))
        for i, a in enumerate(apps):
            self._installed_table.setItem(i, 0, QTableWidgetItem(str(a.id)))
            self._installed_table.setItem(i, 1, QTableWidgetItem(a.name))
            self._installed_table.setItem(i, 2, QTableWidgetItem(a.publisher or ""))
            self._installed_table.setItem(i, 3, QTableWidgetItem(a.version or ""))
            self._installed_table.setItem(i, 4, QTableWidgetItem(a.tags or ""))
        session.close()

    def _on_scan_mock(self):
        from snapkit.scanner import load_mock_data, save_scanned_apps

        session = self._session()
        apps = load_mock_data()
        added = save_scanned_apps(session, apps)
        session.close()
        self._refresh_installed()
        QMessageBox.information(self, "Scan", f"{len(apps)} apps found, {added} new.")

    def _on_pin_selected(self):
        row = self._installed_table.currentRow()
        if row < 0:
            return
        app_id = int(self._installed_table.item(row, 0).text())
        session = self._session()
        existing = session.query(PinnedApp).filter_by(installed_app_id=app_id).first()
        if existing:
            QMessageBox.warning(self, "Pin", "Already pinned.")
            session.close()
            return
        session.add(PinnedApp(installed_app_id=app_id))
        session.commit()
        session.close()
        self._refresh_pinned()
        QMessageBox.information(self, "Pin", "App pinned.")

    # ── Pinned Apps tab ───────────────────────────────────────────────

    def _build_pinned_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._pinned_search = QLineEdit()
        self._pinned_search.setPlaceholderText("Search pinned apps...")
        self._pinned_search.textChanged.connect(self._refresh_pinned)
        layout.addWidget(self._pinned_search)

        self._pinned_table = QTableWidget()
        self._pinned_table.setColumnCount(4)
        self._pinned_table.setHorizontalHeaderLabels(["Pin ID", "App Name", "Launch Command", "Tags"])
        self._pinned_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._pinned_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._pinned_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._pinned_table)

        btns = QHBoxLayout()
        unpin_btn = QPushButton("Unpin")
        unpin_btn.clicked.connect(self._on_unpin)
        launch_btn = QPushButton("Launch")
        launch_btn.clicked.connect(self._on_launch)
        btns.addWidget(unpin_btn)
        btns.addWidget(launch_btn)
        btns.addStretch()
        layout.addLayout(btns)
        return w

    def _refresh_pinned(self):
        session = self._session()
        pins = session.query(PinnedApp).all()
        search = self._pinned_search.text().strip().lower()
        if search:
            pins = [p for p in pins if search in p.installed_app.name.lower()]

        self._pinned_table.setRowCount(len(pins))
        for i, p in enumerate(pins):
            self._pinned_table.setItem(i, 0, QTableWidgetItem(str(p.id)))
            self._pinned_table.setItem(i, 1, QTableWidgetItem(p.installed_app.name))
            self._pinned_table.setItem(i, 2, QTableWidgetItem(p.launch_command or "(auto)"))
            self._pinned_table.setItem(i, 3, QTableWidgetItem(p.tags or ""))
        session.close()

    def _on_unpin(self):
        row = self._pinned_table.currentRow()
        if row < 0:
            return
        pin_id = int(self._pinned_table.item(row, 0).text())
        session = self._session()
        entry = session.get(PinnedApp, pin_id)
        if entry:
            session.delete(entry)
            session.commit()
        session.close()
        self._refresh_pinned()

    def _on_launch(self):
        from snapkit.launcher import infer_exe, launch_app

        row = self._pinned_table.currentRow()
        if row < 0:
            return
        pin_id = int(self._pinned_table.item(row, 0).text())
        session = self._session()
        entry = session.get(PinnedApp, pin_id)
        if not entry:
            session.close()
            return

        command = entry.launch_command
        if not command:
            loc = entry.installed_app.install_location
            command = infer_exe(loc, entry.installed_app.name) if loc else None
        session.close()

        if not command:
            QMessageBox.warning(self, "Launch", "Cannot infer exe. Set launch command manually.")
            return
        launch_app(command)

    # ── Not-Installed tab ─────────────────────────────────────────────

    def _build_notinstalled_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._ni_search = QLineEdit()
        self._ni_search.setPlaceholderText("Search not-installed apps...")
        self._ni_search.textChanged.connect(self._refresh_notinstalled)
        layout.addWidget(self._ni_search)

        self._ni_table = QTableWidget()
        self._ni_table.setColumnCount(5)
        self._ni_table.setHorizontalHeaderLabels(["ID", "Name", "URL", "Description", "Tags"])
        self._ni_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._ni_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._ni_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._ni_table)

        btns = QHBoxLayout()
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._on_delete_ni)
        btns.addWidget(del_btn)
        btns.addStretch()
        layout.addLayout(btns)
        return w

    def _refresh_notinstalled(self):
        session = self._session()
        query = session.query(NotInstalledApp)
        search = self._ni_search.text().strip()
        if search:
            query = query.filter(NotInstalledApp.name.ilike(f"%{search}%"))
        apps = query.order_by(NotInstalledApp.name).all()

        self._ni_table.setRowCount(len(apps))
        for i, a in enumerate(apps):
            self._ni_table.setItem(i, 0, QTableWidgetItem(str(a.id)))
            self._ni_table.setItem(i, 1, QTableWidgetItem(a.name))
            self._ni_table.setItem(i, 2, QTableWidgetItem(a.download_url or ""))
            self._ni_table.setItem(i, 3, QTableWidgetItem(a.description or ""))
            self._ni_table.setItem(i, 4, QTableWidgetItem(a.tags or ""))
        session.close()

    def _on_delete_ni(self):
        row = self._ni_table.currentRow()
        if row < 0:
            return
        ni_id = int(self._ni_table.item(row, 0).text())
        session = self._session()
        entry = session.get(NotInstalledApp, ni_id)
        if entry:
            session.delete(entry)
            session.commit()
        session.close()
        self._refresh_notinstalled()

    # ── Resources tab ─────────────────────────────────────────────────

    def _build_resources_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._res_search = QLineEdit()
        self._res_search.setPlaceholderText("Search resources...")
        self._res_search.textChanged.connect(self._refresh_resources)
        layout.addWidget(self._res_search)

        self._res_table = QTableWidget()
        self._res_table.setColumnCount(5)
        self._res_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Path", "Tags"])
        self._res_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._res_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._res_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._res_table)

        btns = QHBoxLayout()
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._on_open_resource)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._on_delete_resource)
        btns.addWidget(open_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        layout.addLayout(btns)
        return w

    def _refresh_resources(self):
        session = self._session()
        query = session.query(ResourceItem)
        search = self._res_search.text().strip()
        if search:
            query = query.filter(ResourceItem.name.ilike(f"%{search}%"))
        items = query.order_by(ResourceItem.name).all()

        self._res_table.setRowCount(len(items))
        for i, r in enumerate(items):
            self._res_table.setItem(i, 0, QTableWidgetItem(str(r.id)))
            self._res_table.setItem(i, 1, QTableWidgetItem(r.name))
            self._res_table.setItem(i, 2, QTableWidgetItem(r.resource_type))
            self._res_table.setItem(i, 3, QTableWidgetItem(r.path))
            self._res_table.setItem(i, 4, QTableWidgetItem(r.tags or ""))
        session.close()

    def _on_open_resource(self):
        import os
        import platform
        import subprocess
        import webbrowser

        row = self._res_table.currentRow()
        if row < 0:
            return
        res_id = int(self._res_table.item(row, 0).text())
        session = self._session()
        entry = session.get(ResourceItem, res_id)
        if not entry:
            session.close()
            return

        target = entry.path
        rtype = entry.resource_type
        session.close()

        if rtype == "url":
            webbrowser.open(target)
        elif platform.system() == "Windows":
            os.startfile(target)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])

    def _on_delete_resource(self):
        row = self._res_table.currentRow()
        if row < 0:
            return
        res_id = int(self._res_table.item(row, 0).text())
        session = self._session()
        entry = session.get(ResourceItem, res_id)
        if entry:
            session.delete(entry)
            session.commit()
        session.close()
        self._refresh_resources()

    # ── Helpers ───────────────────────────────────────────────────────

    def _refresh_all(self):
        self._refresh_installed()
        self._refresh_pinned()
        self._refresh_notinstalled()
        self._refresh_resources()


def run_gui(engine: Engine):
    """Entry point for the GUI."""
    qapp = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(engine)
    window.show()
    sys.exit(qapp.exec())
