"""PySide6 single-window GUI for SnapKit."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

from snapkit.db import get_session, init_db
from snapkit.gui.icons import extract_icon, get_resource_icon
from snapkit.gui.styles import DARK_THEME
from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


class AddInstalledAppDialog(QDialog):
    """手动添加已安装应用的对话框."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加已安装应用")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("应用名称 (必填)")
        layout.addRow("名称:", self.name_edit)

        self.publisher_edit = QLineEdit()
        self.publisher_edit.setPlaceholderText("发布者")
        layout.addRow("发布者:", self.publisher_edit)

        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("版本号")
        layout.addRow("版本:", self.version_edit)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("安装路径 (可选)")
        layout.addRow("安装路径:", self.location_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("标签，用逗号分隔")
        layout.addRow("标签:", self.tags_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "publisher": self.publisher_edit.text().strip() or None,
            "version": self.version_edit.text().strip() or None,
            "install_location": self.location_edit.text().strip() or None,
            "tags": self.tags_edit.text().strip() or None,
        }


class AddNotInstalledAppDialog(QDialog):
    """添加待安装应用的对话框."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加待安装应用")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("应用名称 (必填)")
        layout.addRow("名称:", self.name_edit)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("下载链接")
        layout.addRow("下载链接:", self.url_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("描述")
        layout.addRow("描述:", self.desc_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("标签，用逗号分隔")
        layout.addRow("标签:", self.tags_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "download_url": self.url_edit.text().strip() or None,
            "description": self.desc_edit.text().strip() or None,
            "tags": self.tags_edit.text().strip() or None,
        }


class AddResourceDialog(QDialog):
    """添加资源的对话框."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加资源")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("资源名称 (必填)")
        layout.addRow("名称:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["file", "folder", "url"])
        layout.addRow("类型:", self.type_combo)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("路径或 URL (必填)")
        layout.addRow("路径:", self.path_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("标签，用逗号分隔")
        layout.addRow("标签:", self.tags_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "resource_type": self.type_combo.currentText(),
            "path": self.path_edit.text().strip(),
            "tags": self.tags_edit.text().strip() or None,
        }


class MainWindow(QMainWindow):
    def __init__(self, engine: Engine):
        super().__init__()
        self._engine = engine
        init_db(engine)
        self.setWindowTitle("SnapKit")
        self.setMinimumSize(900, 600)

        # 应用深色主题
        self.setStyleSheet(DARK_THEME)

        # 创建主布局
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分隔器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 侧边栏
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(140)

        # 添加导航项
        nav_items = [
            ("📦 已安装", 0),
            ("⭐ 收藏", 1),
            ("📋 待装", 2),
            ("📁 资源", 3),
        ]
        for text, idx in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, idx)
            self._sidebar.addItem(item)

        self._sidebar.setCurrentRow(0)
        self._sidebar.currentRowChanged.connect(self._on_nav_changed)

        # 内容区域
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_installed_tab())
        self._stack.addWidget(self._build_pinned_tab())
        self._stack.addWidget(self._build_notinstalled_tab())
        self._stack.addWidget(self._build_resources_tab())

        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._refresh_all()

    def _on_nav_changed(self, row: int):
        """侧边栏导航切换."""
        self._stack.setCurrentIndex(row)

    def _session(self):
        return get_session(self._engine)

    # ── Installed Apps tab ────────────────────────────────────────────

    def _build_installed_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._installed_search = QLineEdit()
        self._installed_search.setPlaceholderText("搜索已安装应用...")
        self._installed_search.textChanged.connect(self._refresh_installed)
        layout.addWidget(self._installed_search)

        self._installed_table = QTableWidget()
        self._installed_table.setColumnCount(5)
        self._installed_table.setHorizontalHeaderLabels(["", "名称", "发布者", "版本", "标签"])
        self._installed_table.setColumnWidth(0, 40)  # 图标列
        self._installed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._installed_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._installed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._installed_table.setAlternatingRowColors(True)
        self._installed_table.verticalHeader().setVisible(False)
        layout.addWidget(self._installed_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_add_installed)
        scan_btn = QPushButton("扫描 (Mock)")
        scan_btn.setProperty("secondary", True)
        scan_btn.clicked.connect(self._on_scan_mock)
        pin_btn = QPushButton("收藏选中")
        pin_btn.setProperty("secondary", True)
        pin_btn.clicked.connect(self._on_pin_selected)
        btns.addWidget(add_btn)
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
            # 图标列
            icon_item = QTableWidgetItem()
            icon = extract_icon(a.install_location)
            icon_item.setIcon(icon)
            icon_item.setData(Qt.UserRole, a.id)  # 存储 ID
            self._installed_table.setItem(i, 0, icon_item)

            self._installed_table.setItem(i, 1, QTableWidgetItem(a.name))
            self._installed_table.setItem(i, 2, QTableWidgetItem(a.publisher or ""))
            self._installed_table.setItem(i, 3, QTableWidgetItem(a.version or ""))
            self._installed_table.setItem(i, 4, QTableWidgetItem(a.tags or ""))

        self._installed_table.setRowHeight(0, 36)
        for i in range(len(apps)):
            self._installed_table.setRowHeight(i, 36)
        session.close()

    def _on_add_installed(self):
        dialog = AddInstalledAppDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "添加失败", "名称不能为空")
                return
            session = self._session()
            app = InstalledApp(**data)
            session.add(app)
            session.commit()
            session.close()
            self._refresh_installed()

    def _on_scan_mock(self):
        from snapkit.scanner import load_mock_data, save_scanned_apps

        session = self._session()
        apps = load_mock_data()
        added = save_scanned_apps(session, apps)
        session.close()
        self._refresh_installed()
        QMessageBox.information(self, "扫描完成", f"发现 {len(apps)} 个应用，新增 {added} 个。")

    def _on_pin_selected(self):
        row = self._installed_table.currentRow()
        if row < 0:
            return
        app_id = self._installed_table.item(row, 0).data(Qt.UserRole)
        session = self._session()
        existing = session.query(PinnedApp).filter_by(installed_app_id=app_id).first()
        if existing:
            QMessageBox.warning(self, "收藏", "该应用已收藏。")
            session.close()
            return
        session.add(PinnedApp(installed_app_id=app_id))
        session.commit()
        session.close()
        self._refresh_pinned()
        QMessageBox.information(self, "收藏", "已添加到收藏。")

    # ── Pinned Apps tab ───────────────────────────────────────────────

    def _build_pinned_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._pinned_search = QLineEdit()
        self._pinned_search.setPlaceholderText("搜索收藏应用...")
        self._pinned_search.textChanged.connect(self._refresh_pinned)
        layout.addWidget(self._pinned_search)

        self._pinned_table = QTableWidget()
        self._pinned_table.setColumnCount(4)
        self._pinned_table.setHorizontalHeaderLabels(["", "应用名称", "启动命令", "标签"])
        self._pinned_table.setColumnWidth(0, 40)
        self._pinned_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._pinned_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._pinned_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._pinned_table.setAlternatingRowColors(True)
        self._pinned_table.verticalHeader().setVisible(False)
        layout.addWidget(self._pinned_table)

        btns = QHBoxLayout()
        launch_btn = QPushButton("启动")
        launch_btn.clicked.connect(self._on_launch)
        unpin_btn = QPushButton("取消收藏")
        unpin_btn.setProperty("secondary", True)
        unpin_btn.clicked.connect(self._on_unpin)
        btns.addWidget(launch_btn)
        btns.addWidget(unpin_btn)
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
            # 图标列
            icon_item = QTableWidgetItem()
            icon = extract_icon(p.installed_app.install_location)
            icon_item.setIcon(icon)
            icon_item.setData(Qt.UserRole, p.id)
            self._pinned_table.setItem(i, 0, icon_item)

            self._pinned_table.setItem(i, 1, QTableWidgetItem(p.installed_app.name))
            self._pinned_table.setItem(i, 2, QTableWidgetItem(p.launch_command or "(自动)"))
            self._pinned_table.setItem(i, 3, QTableWidgetItem(p.tags or ""))
            self._pinned_table.setRowHeight(i, 36)
        session.close()

    def _on_unpin(self):
        row = self._pinned_table.currentRow()
        if row < 0:
            return
        pin_id = self._pinned_table.item(row, 0).data(Qt.UserRole)
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
        pin_id = self._pinned_table.item(row, 0).data(Qt.UserRole)
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
            QMessageBox.warning(self, "启动失败", "无法推断可执行文件，请手动设置启动命令。")
            return
        launch_app(command)

    # ── Not-Installed tab ─────────────────────────────────────────────

    def _build_notinstalled_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._ni_search = QLineEdit()
        self._ni_search.setPlaceholderText("搜索待安装应用...")
        self._ni_search.textChanged.connect(self._refresh_notinstalled)
        layout.addWidget(self._ni_search)

        self._ni_table = QTableWidget()
        self._ni_table.setColumnCount(4)
        self._ni_table.setHorizontalHeaderLabels(["", "名称", "下载链接", "描述"])
        self._ni_table.setColumnWidth(0, 40)
        self._ni_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._ni_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._ni_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._ni_table.setAlternatingRowColors(True)
        self._ni_table.verticalHeader().setVisible(False)
        layout.addWidget(self._ni_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_add_notinstalled)
        del_btn = QPushButton("删除")
        del_btn.setProperty("secondary", True)
        del_btn.clicked.connect(self._on_delete_ni)
        btns.addWidget(add_btn)
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
            icon_item = QTableWidgetItem()
            icon_item.setIcon(get_resource_icon("file"))
            icon_item.setData(Qt.UserRole, a.id)
            self._ni_table.setItem(i, 0, icon_item)

            self._ni_table.setItem(i, 1, QTableWidgetItem(a.name))
            self._ni_table.setItem(i, 2, QTableWidgetItem(a.download_url or ""))
            self._ni_table.setItem(i, 3, QTableWidgetItem(a.description or ""))
            self._ni_table.setRowHeight(i, 36)
        session.close()

    def _on_add_notinstalled(self):
        dialog = AddNotInstalledAppDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "添加失败", "名称不能为空")
                return
            session = self._session()
            app = NotInstalledApp(**data)
            session.add(app)
            session.commit()
            session.close()
            self._refresh_notinstalled()

    def _on_delete_ni(self):
        row = self._ni_table.currentRow()
        if row < 0:
            return
        ni_id = self._ni_table.item(row, 0).data(Qt.UserRole)
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._res_search = QLineEdit()
        self._res_search.setPlaceholderText("搜索资源...")
        self._res_search.textChanged.connect(self._refresh_resources)
        layout.addWidget(self._res_search)

        self._res_table = QTableWidget()
        self._res_table.setColumnCount(4)
        self._res_table.setHorizontalHeaderLabels(["", "名称", "类型", "路径"])
        self._res_table.setColumnWidth(0, 40)
        self._res_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._res_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._res_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._res_table.setAlternatingRowColors(True)
        self._res_table.verticalHeader().setVisible(False)
        layout.addWidget(self._res_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_add_resource)
        open_btn = QPushButton("打开")
        open_btn.setProperty("secondary", True)
        open_btn.clicked.connect(self._on_open_resource)
        del_btn = QPushButton("删除")
        del_btn.setProperty("secondary", True)
        del_btn.clicked.connect(self._on_delete_resource)
        btns.addWidget(add_btn)
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
            icon_item = QTableWidgetItem()
            icon_item.setIcon(get_resource_icon(r.resource_type))
            icon_item.setData(Qt.UserRole, r.id)
            self._res_table.setItem(i, 0, icon_item)

            self._res_table.setItem(i, 1, QTableWidgetItem(r.name))
            self._res_table.setItem(i, 2, QTableWidgetItem(r.resource_type))
            self._res_table.setItem(i, 3, QTableWidgetItem(r.path))
            self._res_table.setRowHeight(i, 36)
        session.close()

    def _on_add_resource(self):
        dialog = AddResourceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"] or not data["path"]:
                QMessageBox.warning(self, "添加失败", "名称和路径不能为空")
                return
            session = self._session()
            item = ResourceItem(**data)
            session.add(item)
            session.commit()
            session.close()
            self._refresh_resources()

    def _on_open_resource(self):
        import os
        import platform
        import subprocess
        import webbrowser

        row = self._res_table.currentRow()
        if row < 0:
            return
        res_id = self._res_table.item(row, 0).data(Qt.UserRole)
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
        res_id = self._res_table.item(row, 0).data(Qt.UserRole)
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
