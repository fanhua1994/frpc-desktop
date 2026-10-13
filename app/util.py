import os
import re
import sys
import tkinter as tk

# 配置与日志目录（相对程序运行目录）
CONFIG_DIR = "configs"
FRPC_TOML_FILE = os.path.join(CONFIG_DIR, "frpc.toml")
FRPC_CONFIG_JSON = os.path.join(CONFIG_DIR, "frpc_config.json")
# 展示/提示用正斜杠路径
FRPC_TOML_DISPLAY = "configs/frpc.toml"
FRPC_CONFIG_JSON_DISPLAY = "configs/frpc_config.json"

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "frpc.log")
# 写入 frpc.toml 时使用正斜杠，避免 Windows 反斜杠转义问题
LOG_FILE_TOML = "logs/frpc.log"


def ensure_config_dir() -> str:
    """确保配置目录存在，返回目录路径。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return CONFIG_DIR


def ensure_log_dir() -> str:
    """确保日志目录存在，返回日志文件相对路径。"""
    os.makedirs(LOG_DIR, exist_ok=True)
    return LOG_FILE


def _move_if_exists(src: str, dest: str) -> bool:
    """若源文件存在且目标不存在，则移动到目标路径。"""
    if not os.path.exists(src) or os.path.exists(dest):
        return False
    ensure_config_dir()
    try:
        os.replace(src, dest)
        return True
    except OSError:
        try:
            import shutil
            shutil.move(src, dest)
            return True
        except OSError:
            return False


def migrate_legacy_config_files() -> bool:
    """
    将根目录旧版配置迁移到 configs/。
    返回是否发生了迁移。
    """
    ensure_config_dir()
    moved_toml = _move_if_exists("frpc.toml", FRPC_TOML_FILE)
    moved_json = _move_if_exists("frpc_config.json", FRPC_CONFIG_JSON)
    return moved_toml or moved_json


def migrate_log_path_in_frpc_toml(toml_path=None) -> bool:
    """
    将旧版根目录日志路径迁移到 logs/frpc.log。
    若文件不存在或无需修改则返回 False。
    """
    if toml_path is None:
        toml_path = FRPC_TOML_FILE
    if not os.path.exists(toml_path):
        return False
    try:
        with open(toml_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return False

    patterns = (
        'log.to = "frpc.log"',
        "log.to = 'frpc.log'",
    )
    if not any(p in content for p in patterns):
        return False

    new_content = content
    for old in patterns:
        new_content = new_content.replace(old, f'log.to = "{LOG_FILE_TOML}"')
    if new_content == content:
        return False

    ensure_log_dir()
    try:
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError:
        return False
    return True


def resource_path(relative_path):
    """获取资源文件路径，兼容开发环境和 PyInstaller 打包后的路径"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


def apply_window_icon(window, icon_name="logo.ico"):
    """为窗口设置应用图标"""
    icon_path = resource_path(icon_name)
    if not os.path.exists(icon_path):
        return
    try:
        window.iconbitmap(icon_path)
    except tk.TclError:
        pass



def validate_ip_address(ip):
    """
    验证 IP 地址格式
    支持 IPv4 地址
    
    参数:
        ip: IP 地址字符串
    
    返回:
        bool: 是否为有效的 IPv4 地址
    """
    if not ip or not isinstance(ip, str):
        return False
    
    # IPv4 地址格式验证
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False


def validate_server_address(address):
    """
    验证服务器地址格式
    支持 IPv4 地址和域名
    
    参数:
        address: 服务器地址字符串（IP 或域名）
    
    返回:
        bool: 是否为有效的服务器地址
    """
    if not address or not isinstance(address, str):
        return False
    
    address = address.strip()
    if not address:
        return False
    
    # 首先尝试作为 IP 地址验证
    if validate_ip_address(address):
        return True
    
    # 如果不是 IP 地址，则作为域名验证
    # 域名基本规则：
    # 1. 只能包含字母、数字、连字符和点
    # 2. 不能以连字符或点开头或结尾
    # 3. 至少包含一个点（顶级域名）
    # 4. 每个标签长度不超过 63 个字符
    # 5. 总长度不超过 253 个字符
    
    # 检查总长度
    if len(address) > 253:
        return False
    
    # 检查是否以连字符或点开头/结尾
    if address.startswith('-') or address.endswith('-'):
        return False
    if address.startswith('.') or address.endswith('.'):
        return False
    
    # 检查是否包含至少一个点
    if '.' not in address:
        return False
    
    # 使用正则表达式验证域名格式
    # 允许的字符：字母、数字、连字符、点
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    
    if re.match(domain_pattern, address):
        # 验证每个标签的长度不超过 63 个字符
        labels = address.split('.')
        for label in labels:
            if len(label) > 63:
                return False
        return True
    
    return False


def validate_port(port, min_port=1, max_port=65535):
    """
    验证端口号是否在有效范围内
    
    参数:
        port: 端口号（可以是字符串或整数）
        min_port: 最小端口号，默认 1
        max_port: 最大端口号，默认 65535
    
    返回:
        (is_valid, port_int): (是否有效, 端口整数)
    """
    try:
        port_int = int(port)
        if min_port <= port_int <= max_port:
            return True, port_int
        else:
            return False, port_int
    except (ValueError, TypeError):
        return False, None


def center_window(window, width=None, height=None):
    """
    将窗口居中显示在屏幕上

    参数:
        window: Tkinter 窗口对象
        width: 窗口宽度（可选，已知时可避免闪烁）
        height: 窗口高度（可选，已知时可避免闪烁）
    """
    window.update_idletasks()
    win_width = width if width is not None else window.winfo_width()
    win_height = height if height is not None else window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (win_width // 2)
    y = (window.winfo_screenheight() // 2) - (win_height // 2)
    if width is not None and height is not None:
        window.geometry(f"{width}x{height}+{x}+{y}")
    else:
        window.geometry(f"+{x}+{y}")
