from __future__ import annotations

from snapkit.core.entities import UiItem, ViewId
from snapkit.core.protocols import ToolboxRepository

VIEW_META: dict[ViewId, tuple[str, str]] = {
    "local_scan": ("本地应用", "管理并启动电脑上已安装的软件"),
    "installed": ("已收藏", "快速启动你收藏的已安装应用"),
    "not_installed": ("待安装软件", "收藏中当前未安装的软件"),
    "resource_image": ("图片素材", "集中管理图片与设计资源"),
    "resource_video": ("视频文件", "整理常用视频与剪辑素材"),
    "resource_document": ("文档记录", "收藏文档、笔记和参考资料"),
    "resource_url": ("资源网站", "常用网站与在线工具入口"),
}


def list_items(
    repo: ToolboxRepository,
    view_id: ViewId,
    search: str = "",
    limit: int = 300,
    local_filter: str = "all",
) -> tuple[str, str, list[UiItem]]:
    title, subtitle = VIEW_META[view_id]

    if view_id == "local_scan":
        return title, subtitle, repo.list_installed(
            search=search, limit=limit, pinned_filter=local_filter
        )
    if view_id == "installed":
        return title, subtitle, repo.list_pinned(search=search, limit=limit)
    if view_id == "not_installed":
        return title, subtitle, repo.list_not_installed(search=search, limit=limit)

    resource_type = view_id.replace("resource_", "")
    return title, subtitle, repo.list_resources(
        resource_type=resource_type,
        search=search,
        limit=limit,
    )
