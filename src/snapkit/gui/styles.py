"""深色主题样式表 for SnapKit GUI."""

DARK_THEME = """
/* 全局样式 */
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* 侧边栏导航 */
QListWidget#sidebar {
    background-color: #252526;
    border: none;
    border-right: 1px solid #3c3c3c;
    padding: 8px 4px;
    min-width: 120px;
    max-width: 140px;
}

QListWidget#sidebar::item {
    padding: 12px 16px;
    border-radius: 6px;
    margin: 2px 4px;
    color: #cccccc;
}

QListWidget#sidebar::item:hover {
    background-color: #2d2d2d;
}

QListWidget#sidebar::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}

/* 搜索框 */
QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #0078d4;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
}

QLineEdit::placeholder {
    color: #808080;
}

/* 表格 */
QTableWidget, QTableView {
    background-color: #1e1e1e;
    alternate-background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    gridline-color: #3c3c3c;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

QTableWidget::item, QTableView::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #0078d4;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #cccccc;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid #3c3c3c;
    font-weight: 600;
}

QHeaderView::section:first {
    border-top-left-radius: 6px;
}

QHeaderView::section:last {
    border-top-right-radius: 6px;
}

/* 按钮 */
QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #1a86d9;
}

QPushButton:pressed {
    background-color: #006cbd;
}

QPushButton:disabled {
    background-color: #3c3c3c;
    color: #808080;
}

/* 次要按钮 */
QPushButton[secondary="true"] {
    background-color: #3c3c3c;
    color: #cccccc;
}

QPushButton[secondary="true"]:hover {
    background-color: #4a4a4a;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #5a5a5a;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6a6a6a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #5a5a5a;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #6a6a6a;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* 对话框 */
QDialog {
    background-color: #2d2d2d;
}

QLabel {
    color: #cccccc;
}

/* 下拉框 */
QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    min-width: 100px;
}

QComboBox:hover {
    border: 1px solid #5a5a5a;
}

QComboBox:focus {
    border: 1px solid #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #cccccc;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    border: 1px solid #5a5a5a;
    border-radius: 6px;
    selection-background-color: #0078d4;
    color: #ffffff;
}

/* 消息框 */
QMessageBox {
    background-color: #2d2d2d;
}

QMessageBox QLabel {
    color: #cccccc;
}

/* 分隔器 */
QSplitter::handle {
    background-color: #3c3c3c;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* 工具提示 */
QToolTip {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 4px 8px;
}
"""
