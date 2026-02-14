# SnapKit

Windows 个人工具箱 / 启动器。集中管理已安装应用、收藏常用程序、记录待安装软件和各类资源，支持一键启动和数据导出迁移。

## 环境要求

- Windows 10 / 11
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

## 安装

### 1. 安装 uv

打开 PowerShell，运行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装完成后重新打开终端，确认：

```powershell
uv --version
```

### 2. 克隆项目

```powershell
git clone <你的仓库地址> SnapKit
cd SnapKit
```

### 3. 安装依赖

仅 CLI（不含 GUI）：

```powershell
uv sync
```

包含 GUI：

```powershell
uv sync --extra gui
```

安装开发/测试依赖：

```powershell
uv sync --extra dev
```

安装完成后 `snapkit` 命令即可在虚拟环境中使用。以下所有命令均通过 `uv run snapkit` 调用，或者你也可以先激活虚拟环境：

```powershell
.venv\Scripts\activate
snapkit --help
```

## 快速上手

### 扫描已安装应用

从 Windows 注册表扫描本机已安装的程序：

```powershell
uv run snapkit scan
```

如果想用模拟数据测试（非 Windows 环境或快速体验）：

```powershell
uv run snapkit scan --mock
```

### 查看已安装应用

```powershell
uv run snapkit list-installed
```

按标签筛选：

```powershell
uv run snapkit list-installed --tag dev
```

### 收藏（Pin）应用

从 `list-installed` 输出中找到应用 ID，然后收藏：

```powershell
uv run snapkit pin 1
```

查看已收藏：

```powershell
uv run snapkit list-pinned
```

取消收藏（参数是 Pin ID，不是 App ID）：

```powershell
uv run snapkit unpin 1
```

### 启动应用

SnapKit 会自动从安装目录推断可执行文件：

```powershell
uv run snapkit run 1
```

如果自动推断失败，手动指定启动命令：

```powershell
uv run snapkit set-launch 1 "C:\Program Files\Mozilla Firefox\firefox.exe"
uv run snapkit run 1
```

### 记录待安装软件

```powershell
uv run snapkit add-notinstalled Blender --url https://www.blender.org/download/ --tags "3d,modeling"
uv run snapkit list-notinstalled
```

### 管理资源

添加文件、文件夹或 URL：

```powershell
uv run snapkit add-resource "工作笔记" "D:\notes\work.md" --type file --tags "笔记"
uv run snapkit add-resource "项目文档" "https://docs.example.com" --type url
uv run snapkit add-resource "素材库" "D:\assets" --type folder
```

查看和打开：

```powershell
uv run snapkit list-resources
uv run snapkit open-resource 1
```

### 导出 / 导入

导出所有数据到 zip 包（可用于备份或迁移到另一台电脑）：

```powershell
uv run snapkit export my_backup.zip
```

在新机器上导入：

```powershell
uv run snapkit import my_backup.zip --restore-to D:\restored_files
```

### 启动 GUI

需要先安装 GUI 依赖（`uv sync --extra gui`）：

```powershell
uv run snapkit gui
```

GUI 提供四个标签页：已安装应用、已收藏应用、待安装软件、资源管理，每个标签页都有搜索框和操作按钮。

## 命令一览

| 命令 | 说明 |
|------|------|
| `scan [--mock]` | 扫描注册表（或模拟数据） |
| `list-installed [--tag TAG]` | 列出已安装应用 |
| `pin APP_ID` | 收藏应用 |
| `unpin PIN_ID` | 取消收藏 |
| `set-launch PIN_ID COMMAND` | 设置启动命令 |
| `list-pinned` | 列出已收藏应用 |
| `run PIN_ID` | 启动已收藏的应用 |
| `add-notinstalled NAME [--url] [--desc] [--tags]` | 添加待安装软件 |
| `list-notinstalled [--tag TAG]` | 列出待安装软件 |
| `add-resource NAME PATH [--type] [--tags]` | 添加资源 |
| `list-resources [--tag TAG]` | 列出资源 |
| `open-resource RES_ID` | 打开资源 |
| `export [OUTPUT]` | 导出数据为 zip |
| `import ZIP_PATH [--restore-to DIR]` | 从 zip 导入数据 |
| `gui` | 启动图形界面 |

## 数据存储

数据库文件位于 `%USERPROFILE%\.snapkit\snapkit.db`（SQLite），删除此文件即可重置所有数据。

## 运行测试

```powershell
uv sync --extra dev
uv run pytest tests/ -v
```

## 项目结构

```
SnapKit/
├── pyproject.toml              # 项目配置、依赖、入口点
├── src/snapkit/
│   ├── __init__.py
│   ├── db.py                   # 数据库引擎 / 会话
│   ├── models.py               # ORM 模型（4张表）
│   ├── scanner.py              # 注册表扫描 + mock 数据
│   ├── launcher.py             # exe 推断 + 启动
│   ├── exporter.py             # 导出 / 导入 zip
│   ├── cli.py                  # 全部 CLI 命令
│   └── gui/
│       └── main_window.py      # PySide6 图形界面
└── tests/                      # 测试用例
```
