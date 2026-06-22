import re
import tkinter as tk


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


def center_window(window):
    """
    将窗口居中显示在屏幕上
    
    参数:
        window: Tkinter 窗口对象
    """
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
    y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
    window.geometry(f"+{x}+{y}")
