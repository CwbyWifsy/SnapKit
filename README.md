# SnapKit

SnapKit 是一个面向 Windows 的个人工具箱，核心目标是把「本地应用启动 + 收藏管理 + 资源归档（图片/视频/文档/网站）」放到一个统一界面里，减少在系统菜单、文件管理器、浏览器收藏夹之间来回切换。

## 适用场景

- 想快速启动常用本地软件，并做收藏分组
- 希望维护“已收藏但当前未安装”的软件清单
- 需要统一管理本地与网络资源（图片、视频、文档、网站）
- 希望用 Python 构建可维护、可扩展的桌面工具

## 当前能力

- 扫描已安装应用（Windows 注册表 / MSI / 可选 Appx）
- 本地应用列表：启动、管理员启动、打开目录、卸载、重命名、收藏
- 收藏视图：独立查看已收藏应用
- 待安装视图：展示收藏中但当前未安装的软件
- 资源管理：图片、视频、文档、网站统一卡片展示
- 快速添加：
  - 本地应用（exe/lnk/bat/cmd）
  - 待安装软件
  - 资源网站（URL）
  - 文档/图片/视频资源（本地路径或网络 URL）
- 图标能力：
  - 本地应用可自定义图标（从 exe 提取）
  - 网站资源自动尝试解析 favicon（失败回退字母图标）
- 数据导出/导入（zip 包）
- QML GUI + CLI 双入口

## 技术栈

- Python 3.10+
- SQLAlchemy 2.x
- SQLite
- Typer + Rich（CLI）
- PySide6 + Qt Quick/QML（GUI）

## 架构说明

项目按分层组织，便于后续扩展和替换：

- `core`：领域实体与仓储协议
- `app`：用例与应用服务（业务编排）
- `infra`：SQLAlchemy 仓储实现、外部适配
- `interfaces`：CLI 与 QML 界面适配层

这套结构适合你当前“功能迭代快 + UI 持续打磨”的阶段：业务逻辑集中在 `app/service`，界面可独立重构。

## 安装与运行（Conda）

```powershell
conda create -n snapkit python=3.11 -y
conda activate snapkit
pip install -e .
pip install PySide6 pywin32
```

启动 GUI：

```powershell
snapkit gui
```

常用 CLI：

```powershell
snapkit scan
snapkit list-installed
snapkit list-notinstalled
```

## 测试

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

## 目录结构

```text
src/snapkit/
  core/              # 实体与仓储协议
  app/               # 用例、服务层
  infra/             # 仓储实现、外部适配
  interfaces/
    gui_qml/         # QML 界面 + ViewModel + ListModel
  cli.py             # CLI 命令入口
  db.py              # 数据库初始化/会话
  models.py          # ORM 模型
  scanner.py         # Windows 软件扫描
  launcher.py        # 启动逻辑
  exporter.py        # 数据导入导出
```

## 说明

- 当前以 Windows 为主目标平台。
- 扫描结果受系统注册表与安装器写入质量影响，个别软件需要手动补充。
- 本项目处于持续迭代阶段，欢迎按你的工作流继续定制 UI 和操作逻辑。

