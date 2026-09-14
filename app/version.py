"""应用版本信息"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from typing import Optional

__version__ = "1.0.0"
APP_NAME = "FRPC 客户端"
RELEASE_NAME_PREFIX = "frp-desktop"
RELEASE_INFO_FILE = "release_info.json"

# 显示用东八区（与常见国内发布习惯一致）
_DISPLAY_TZ = timezone(timedelta(hours=8))


def _resource_path(relative_path: str) -> str:
    """获取资源路径，兼容开发环境与 PyInstaller 打包后路径。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


def write_release_info(root_dir: str, released_at: Optional[datetime] = None) -> str:
    """
    写入发布信息文件，供打包脚本与运行时读取。

    返回写入的文件绝对路径。
    """
    when = released_at or datetime.now(_DISPLAY_TZ)
    if when.tzinfo is None:
        when = when.replace(tzinfo=_DISPLAY_TZ)
    else:
        when = when.astimezone(_DISPLAY_TZ)
    payload = {
        "version": __version__,
        "released_at": when.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "UTC+8",
    }
    path = os.path.join(root_dir, RELEASE_INFO_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    load_release_info.cache_clear()
    return path


@lru_cache(maxsize=1)
def load_release_info() -> dict:
    """
    读取发布信息。

    - 打包后：优先读取随包嵌入的 release_info.json
    - 开发运行：仅在存在该文件时读取发布时间；版本号始终以 __version__ 为准
    """
    info = {
        "version": __version__,
        "released_at": "",
    }
    path = _resource_path(RELEASE_INFO_FILE)
    if not os.path.exists(path):
        return info
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return info
        released_at = str(data.get("released_at") or "").strip()
        info["released_at"] = released_at
        # 打包产物中版本以发布文件为准，避免与当时写入内容不一致
        if getattr(sys, "frozen", False):
            version = str(data.get("version") or __version__).strip()
            info["version"] = version or __version__
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return info


def get_version_display() -> str:
    """返回用于界面显示的版本字符串"""
    info = load_release_info()
    return f"v{info['version']}"


def get_release_time_display() -> str:
    """返回发布时间显示文本；无发布时间时返回空字符串"""
    return load_release_info().get("released_at", "")


def get_version_detail_display() -> str:
    """返回侧栏/状态页用的版本详情文本"""
    version = get_version_display()
    released_at = get_release_time_display()
    if released_at:
        return f"{version}\n发布于 {released_at}"
    return version


def get_release_exe_basename() -> str:
    """返回发布包文件名（不含扩展名），例如 frp-desktop-1.0.0"""
    return f"{RELEASE_NAME_PREFIX}-{__version__}"


def get_release_exe_name() -> str:
    """返回发布包完整文件名，例如 frp-desktop-1.0.0.exe"""
    return f"{get_release_exe_basename()}.exe"
