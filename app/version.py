"""应用版本信息"""

__version__ = "1.0.0"
APP_NAME = "FRPC 客户端"


def get_version_display() -> str:
    """返回用于界面显示的版本字符串"""
    return f"v{__version__}"
