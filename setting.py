import os
import json
import re
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from util import validate_ip_address, validate_server_address, validate_port, center_window


def check_frpc_config():
    """检测当前目录下是否存在 frpc.toml 文件"""
    return os.path.exists('frpc.toml')


def get_frpc_exe_path():
    """获取保存的 frpc.exe 路径（从 frpc_config.json 读取）"""
    return get_config_from_json('frpc_exe_path', '')


def save_frpc_exe_path(path):
    """保存 frpc.exe 路径"""
    config_file = 'frpc_config.json'
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            pass
    
    config['frpc_exe_path'] = path
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_port_range():
    """获取保存的端口范围配置（从 frpc_config.json 读取）"""
    min_port = get_config_from_json('port_range_min', 1)
    max_port = get_config_from_json('port_range_max', 65535)
    return min_port, max_port


def save_port_range(min_port, max_port):
    """保存端口范围配置"""
    config_file = 'frpc_config.json'
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            pass
    
    config['port_range_min'] = min_port
    config['port_range_max'] = max_port
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def save_web_auth(username, password):
    """保存 Web 服务认证信息到 frpc_config.json"""
    config_file = 'frpc_config.json'
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            pass
    
    config['web_username'] = username if username else ''
    config['web_password'] = password if password else ''
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_web_auth_from_json():
    """从 frpc_config.json 获取 Web 服务认证信息"""
    config_file = 'frpc_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                username = config.get('web_username', '')
                password = config.get('web_password', '')
                if username and password:
                    return username, password
        except:
            pass
    return '', ''


def save_all_config_to_json(
    server_addr=None,
    server_port=None,
    token=None,
    web_addr=None,
    web_port=None,
    web_username=None,
    web_password=None,
    log_level=None,
    frpc_exe_path=None,
    port_range_min=None,
    port_range_max=None,
    enable_subdomain=None
):
    """保存所有配置到 frpc_config.json"""
    config_file = 'frpc_config.json'
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            pass
    
    # 只更新提供的配置项
    if server_addr is not None:
        config['server_addr'] = server_addr
    if server_port is not None:
        config['server_port'] = server_port
    if token is not None:
        config['token'] = token
    if web_addr is not None:
        config['web_addr'] = web_addr
    if web_port is not None:
        config['web_port'] = web_port
    if web_username is not None:
        config['web_username'] = web_username
    if web_password is not None:
        config['web_password'] = web_password
    if log_level is not None:
        config['log_level'] = log_level
    if frpc_exe_path is not None:
        config['frpc_exe_path'] = frpc_exe_path
    if port_range_min is not None:
        config['port_range_min'] = port_range_min
    if port_range_max is not None:
        config['port_range_max'] = port_range_max
    if enable_subdomain is not None:
        config['enable_subdomain'] = enable_subdomain
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_config_from_json(key, default=None):
    """从 frpc_config.json 获取指定配置项"""
    config_file = 'frpc_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get(key, default)
        except:
            pass
    return default


def get_web_auth():
    """从 frpc.toml 获取 Web 服务认证信息"""
    config = load_frpc_toml()
    if config:
        username = config.get('web_user', '')
        password = config.get('web_password', '')
        return username, password
    return '', ''


def load_frpc_toml():
    """加载并解析 frpc.toml 配置文件"""
    if not os.path.exists('frpc.toml'):
        return None
    
    try:
        with open('frpc.toml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        config = {}
        
        # 解析 serverAddr
        match = re.search(r'serverAddr\s*=\s*"([^"]+)"', content)
        if match:
            config['server_addr'] = match.group(1)
        
        # 解析 serverPort
        match = re.search(r'serverPort\s*=\s*(\d+)', content)
        if match:
            config['server_port'] = match.group(1)
        
        # 解析 auth.token
        match = re.search(r'auth\.token\s*=\s*"([^"]+)"', content)
        if match:
            config['token'] = match.group(1)
        
        # 解析 webServer.addr
        match = re.search(r'webServer\.addr\s*=\s*"([^"]+)"', content)
        if match:
            config['web_addr'] = match.group(1)
        
        # 解析 webServer.port
        match = re.search(r'webServer\.port\s*=\s*(\d+)', content)
        if match:
            config['web_port'] = match.group(1)
        
        # 解析 webServer.user
        match = re.search(r'webServer\.user\s*=\s*"([^"]+)"', content)
        if match:
            config['web_user'] = match.group(1)
        
        # 解析 webServer.password
        match = re.search(r'webServer\.password\s*=\s*"([^"]+)"', content)
        if match:
            config['web_password'] = match.group(1)
        
        # 解析 log.to
        match = re.search(r'log\.to\s*=\s*"([^"]+)"', content)
        if match:
            config['log_to'] = match.group(1)
        
        # 解析 log.level
        match = re.search(r'log\.level\s*=\s*"([^"]+)"', content)
        if match:
            config['log_level'] = match.group(1)
        
        # 解析代理配置
        proxies = []
        # 使用更简单的正则表达式匹配 [[proxies]] 块
        proxy_blocks = re.split(r'\[\[proxies\]\]', content)
        
        for block in proxy_blocks[1:]:  # 跳过第一个（配置头部）
            proxy = {}
            
            # 解析 name
            name_match = re.search(r'name\s*=\s*"([^"]+)"', block)
            if name_match:
                proxy['name'] = name_match.group(1)
            
            # 解析 type
            type_match = re.search(r'type\s*=\s*"([^"]+)"', block)
            if type_match:
                proxy['type'] = type_match.group(1)
            
            # 解析 enabled
            enabled_match = re.search(r'enabled\s*=\s*(true|false)', block)
            if enabled_match:
                proxy['enabled'] = enabled_match.group(1) == 'true'
            
            # 解析 localIP
            local_ip_match = re.search(r'localIP\s*=\s*"([^"]+)"', block)
            if local_ip_match:
                proxy['localIP'] = local_ip_match.group(1)
            
            # 解析 localPort
            local_port_match = re.search(r'localPort\s*=\s*(\d+)', block)
            if local_port_match:
                proxy['localPort'] = int(local_port_match.group(1))
            
            # 解析 remotePort
            remote_port_match = re.search(r'remotePort\s*=\s*(\d+)', block)
            if remote_port_match:
                proxy['remotePort'] = int(remote_port_match.group(1))
            
            # 解析 subdomain
            subdomain_match = re.search(r'subdomain\s*=\s*"([^"]+)"', block)
            if subdomain_match:
                proxy['subdomain'] = subdomain_match.group(1)
            
            # 解析 customDomains
            custom_domains_matches = re.finditer(r'customDomains\s*=\s*\[(.*?)\]', block, re.DOTALL)
            for match in custom_domains_matches:
                domains_str = match.group(1)
                # 解析数组中的字符串
                domain_list = re.findall(r'"([^"]+)"', domains_str)
                if domain_list:
                    proxy['customDomains'] = domain_list
                    break
            
            # 解析 annotations
            annotations = {}
            annotation_matches = re.finditer(r'annotations\.([^\s=]+)\s*=\s*"([^"]+)"', block)
            for ann_match in annotation_matches:
                key = ann_match.group(1)
                value = ann_match.group(2)
                annotations[key] = value
            if annotations:
                proxy['annotations'] = annotations
            
            if proxy.get('name') and proxy.get('type'):
                proxies.append(proxy)
        
        if proxies:
            config['proxies'] = proxies
        
        return config
    except Exception as e:
        print(f"解析配置文件失败: {e}")
        return None


def generate_frpc_toml(server_addr, server_port, token=None, web_addr="127.0.0.1", web_port=7400, log_level="info", web_user=None, web_password=None):
    """
    根据用户输入生成 frpc.toml 基础配置文件
    只生成基础配置，保留现有的代理配置
    
    参数:
        server_addr: 服务器地址
        server_port: 服务器端口
        token: 认证 token（可选）
        web_addr: Web 服务地址
        web_port: Web 服务端口
        log_level: 日志级别
        web_user: Web 服务用户名（可选）
        web_password: Web 服务密码（可选）
    """
    # 读取现有配置文件，提取代理配置部分
    existing_proxies_content = ""
    if os.path.exists('frpc.toml'):
        try:
            with open('frpc.toml', 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # 查找第一个 [[proxies]] 的位置
            proxy_start = existing_content.find('[[proxies]]')
            if proxy_start != -1:
                # 保留代理配置部分
                existing_proxies_content = '\n' + existing_content[proxy_start:].strip()
        except:
            pass
    
    # 生成基础配置
    config_content = f'''serverAddr = "{server_addr}"
serverPort = {server_port}

# 认证配置
auth.method = "token"
'''
    
    if token:
        config_content += f'auth.token = "{token}"\n'
    else:
        config_content += '# auth.token = ""\n'
    
    config_content += f'''
# 监控
webServer.addr = "{web_addr}"
webServer.port = {web_port}
'''
    
    # 添加 Web 服务用户名和密码（如果提供）
    if web_user and web_password:
        config_content += f'webServer.user = "{web_user}"\n'
        config_content += f'webServer.password = "{web_password}"\n'
    
    config_content += f'''
# 日志配置
log.to = "frpc.log"
log.level = "{log_level}"
'''
    
    # 追加现有的代理配置
    if existing_proxies_content:
        config_content += existing_proxies_content
    
    with open('frpc.toml', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    return True


def show_settings_window(parent=None):
    """
    显示设置窗口
    
    参数:
        parent: 父窗口，如果提供则作为 Toplevel 窗口打开，否则作为独立窗口
    
    返回:
        bool: 如果用户保存了配置返回 True，如果取消或关闭窗口返回 False
    """
    if parent:
        root = tk.Toplevel(parent)
        root.transient(parent)
        root.grab_set()
    else:
        root = tk.Tk()
    
    root.title("FRPC 配置设置")
    root.geometry("500x650")
    root.resizable(False, False)
    
    # 居中显示窗口
    center_window(root)
    
    # 用于跟踪用户是否保存了配置
    config_saved = [False]  # 使用列表以便在嵌套函数中修改
    
    # 创建输入框和标签
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # 加载现有配置
    existing_config = load_frpc_toml()
    
    # 服务器地址（支持 IP 或域名）
    ttk.Label(frame, text="服务器地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
    server_ip_entry = ttk.Entry(frame, width=30)
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    server_ip_from_json = get_config_from_json('server_addr')
    if server_ip_from_json:
        server_ip_entry.insert(0, server_ip_from_json)
    elif existing_config and 'server_addr' in existing_config:
        server_ip_entry.insert(0, existing_config['server_addr'])
    server_ip_entry.grid(row=0, column=1, pady=5, padx=10)
    
    # 服务器端口
    ttk.Label(frame, text="服务器端口:").grid(row=1, column=0, sticky=tk.W, pady=5)
    server_port_entry = ttk.Entry(frame, width=30)
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    server_port_from_json = get_config_from_json('server_port')
    if server_port_from_json:
        server_port_entry.insert(0, str(server_port_from_json))
    elif existing_config and 'server_port' in existing_config:
        server_port_entry.insert(0, existing_config['server_port'])
    else:
        server_port_entry.insert(0, "7000")
    server_port_entry.grid(row=1, column=1, pady=5, padx=10)
    
    # 访问 token（可选）
    ttk.Label(frame, text="访问 token (可选):").grid(row=2, column=0, sticky=tk.W, pady=5)
    token_entry = ttk.Entry(frame, width=30)
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    token_from_json = get_config_from_json('token')
    if token_from_json:
        token_entry.insert(0, token_from_json)
    elif existing_config and 'token' in existing_config:
        token_entry.insert(0, existing_config['token'])
    token_entry.grid(row=2, column=1, pady=5, padx=10)
    
    # Web 服务 IP
    ttk.Label(frame, text="Web 服务 IP:").grid(row=3, column=0, sticky=tk.W, pady=5)
    web_ip_entry = ttk.Entry(frame, width=30)
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    web_ip_from_json = get_config_from_json('web_addr')
    if web_ip_from_json:
        web_ip_entry.insert(0, web_ip_from_json)
    elif existing_config and 'web_addr' in existing_config:
        web_ip_entry.insert(0, existing_config['web_addr'])
    else:
        web_ip_entry.insert(0, "127.0.0.1")
    web_ip_entry.grid(row=3, column=1, pady=5, padx=10)
    
    # Web 服务端口
    ttk.Label(frame, text="Web 服务端口:").grid(row=4, column=0, sticky=tk.W, pady=5)
    web_port_entry = ttk.Entry(frame, width=30)
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    web_port_from_json = get_config_from_json('web_port')
    if web_port_from_json:
        web_port_entry.insert(0, str(web_port_from_json))
    elif existing_config and 'web_port' in existing_config:
        web_port_entry.insert(0, existing_config['web_port'])
    else:
        web_port_entry.insert(0, "7400")
    web_port_entry.grid(row=4, column=1, pady=5, padx=10)
    
    # Web 服务用户名（可选）
    ttk.Label(frame, text="Web 服务用户名 (可选):").grid(row=5, column=0, sticky=tk.W, pady=5)
    web_username_entry = ttk.Entry(frame, width=30)
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    web_username_from_json, _ = get_web_auth_from_json()
    if web_username_from_json:
        web_username_entry.insert(0, web_username_from_json)
    elif existing_config and 'web_user' in existing_config:
        web_username_entry.insert(0, existing_config['web_user'])
    web_username_entry.grid(row=5, column=1, pady=5, padx=10)
    
    # Web 服务密码（可选）
    ttk.Label(frame, text="Web 服务密码 (可选):").grid(row=6, column=0, sticky=tk.W, pady=5)
    web_password_entry = ttk.Entry(frame, width=30, show="*")
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    _, web_password_from_json = get_web_auth_from_json()
    if web_password_from_json:
        web_password_entry.insert(0, web_password_from_json)
    elif existing_config and 'web_password' in existing_config:
        web_password_entry.insert(0, existing_config['web_password'])
    web_password_entry.grid(row=6, column=1, pady=5, padx=10)
    
    # 日志等级
    ttk.Label(frame, text="日志等级:").grid(row=7, column=0, sticky=tk.W, pady=5)
    log_level_combo = ttk.Combobox(frame, width=27, state="readonly")
    log_level_combo['values'] = ('trace', 'debug', 'info', 'warn', 'error')
    # 优先从 frpc_config.json 读取，如果没有则从 frpc.toml 读取
    log_level_from_json = get_config_from_json('log_level')
    if log_level_from_json:
        log_level_combo.set(log_level_from_json)
    elif existing_config and 'log_level' in existing_config:
        log_level_combo.set(existing_config['log_level'])
    else:
        log_level_combo.set('info')
    log_level_combo.grid(row=7, column=1, pady=5, padx=10, sticky=tk.W)
    
    # 服务器端口范围
    ttk.Label(frame, text="服务器端口范围:").grid(row=8, column=0, sticky=tk.W, pady=5)
    port_range_frame = ttk.Frame(frame)
    port_range_frame.grid(row=8, column=1, pady=5, padx=10, sticky=tk.W)
    
    # 加载已保存的端口范围（从 frpc_config.json 读取）
    saved_min_port = get_config_from_json('port_range_min', 1)
    saved_max_port = get_config_from_json('port_range_max', 65535)
    
    min_port_entry = ttk.Entry(port_range_frame, width=10)
    min_port_entry.insert(0, str(saved_min_port))
    min_port_entry.pack(side=tk.LEFT)
    
    ttk.Label(port_range_frame, text=" ~ ").pack(side=tk.LEFT)
    
    max_port_entry = ttk.Entry(port_range_frame, width=10)
    max_port_entry.insert(0, str(saved_max_port))
    max_port_entry.pack(side=tk.LEFT)
    
    ttk.Label(port_range_frame, text=" (1-65535)").pack(side=tk.LEFT, padx=(5, 0))
    
    # FRPC.exe 路径
    ttk.Label(frame, text="FRPC.exe 路径:").grid(row=9, column=0, sticky=tk.W, pady=5)
    frpc_path_frame = ttk.Frame(frame)
    frpc_path_frame.grid(row=9, column=1, pady=5, padx=10, sticky=tk.EW)
    
    frpc_path_entry = ttk.Entry(frpc_path_frame, width=25)
    frpc_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 加载已保存的路径（从 frpc_config.json 读取）
    saved_path = get_config_from_json('frpc_exe_path', '')
    if saved_path:
        frpc_path_entry.insert(0, saved_path)
    
    def browse_frpc_exe():
        """浏览选择 frpc.exe 文件"""
        file_path = filedialog.askopenfilename(
            title="选择 frpc.exe 文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if file_path:
            frpc_path_entry.delete(0, tk.END)
            frpc_path_entry.insert(0, file_path)
    
    browse_button = ttk.Button(frpc_path_frame, text="浏览", command=browse_frpc_exe)
    browse_button.pack(side=tk.LEFT, padx=(5, 0))

    # 是否开启子域名（控制代理弹窗中是否显示“子域名”选项）
    ttk.Label(frame, text="是否开启子域名:").grid(row=10, column=0, sticky=tk.W, pady=5)
    enable_subdomain_var = tk.BooleanVar()
    enable_subdomain_var.set(bool(get_config_from_json('enable_subdomain', False)))
    enable_subdomain_check = ttk.Checkbutton(frame, variable=enable_subdomain_var)
    enable_subdomain_check.grid(row=10, column=1, pady=5, padx=10, sticky=tk.W)
    
    def save_config():
        """保存配置"""
        server_ip = server_ip_entry.get().strip()
        server_port = server_port_entry.get().strip()
        token = token_entry.get().strip()
        web_ip = web_ip_entry.get().strip()
        web_port = web_port_entry.get().strip()
        web_username = web_username_entry.get().strip()
        web_password = web_password_entry.get().strip()
        min_port_str = min_port_entry.get().strip()
        max_port_str = max_port_entry.get().strip()
        
        # 验证必填项
        if not server_ip:
            messagebox.showerror("错误", "请输入服务器地址")
            return
        
        # 校验服务器地址（支持 IP 地址或域名）
        if not validate_server_address(server_ip):
            messagebox.showerror("错误", "服务器地址格式不正确，请输入有效的 IP 地址或域名")
            return
        
        if not server_port:
            messagebox.showerror("错误", "请输入服务器端口")
            return
        
        # 验证服务器端口
        is_valid, server_port_int = validate_port(server_port, 1, 65535)
        if not is_valid:
            messagebox.showerror("错误", "服务器端口必须在 1-65535 之间")
            return
        
        # 验证端口范围
        if not min_port_str or not max_port_str:
            messagebox.showerror("错误", "请输入端口范围（最小端口和最大端口）")
            return
        
        is_valid_min, min_port_int = validate_port(min_port_str, 1, 65535)
        if not is_valid_min:
            messagebox.showerror("错误", "最小端口必须在 1-65535 之间")
            return
        
        is_valid_max, max_port_int = validate_port(max_port_str, 1, 65535)
        if not is_valid_max:
            messagebox.showerror("错误", "最大端口必须在 1-65535 之间")
            return
        
        if min_port_int > max_port_int:
            messagebox.showerror("错误", "最小端口不能大于最大端口")
            return
        
        # 如果没有输入 web IP，使用默认值
        if not web_ip:
            web_ip = "127.0.0.1"
        
        # 校验 Web 服务 IP
        if not validate_ip_address(web_ip):
            messagebox.showerror("错误", "Web 服务 IP 格式不正确，请输入有效的 IPv4 地址")
            return
        
        # 如果没有输入 web 端口，使用默认值
        if not web_port:
            web_port = "7400"
        
        # 验证 Web 服务端口
        is_valid, web_port_int = validate_port(web_port, 1, 65535)
        if not is_valid:
            messagebox.showerror("错误", "Web 服务端口必须在 1-65535 之间")
            return
        
        # 验证 Web 服务用户名和密码（如果填了其中一个，另一个必填）
        if web_username and not web_password:
            messagebox.showerror("错误", "如果填写了 Web 服务用户名，则必须填写密码")
            return
        if web_password and not web_username:
            messagebox.showerror("错误", "如果填写了 Web 服务密码，则必须填写用户名")
            return
        
        # 获取 frpc.exe 路径
        frpc_exe_path = frpc_path_entry.get().strip()
        
        # 获取日志等级
        log_level = log_level_combo.get().strip()
        if not log_level:
            log_level = "info"
        
        # 生成配置文件
        try:
            generate_frpc_toml(
                server_ip,
                server_port_int,
                token if token else None,
                web_ip,
                web_port_int,
                log_level,
                web_username if web_username else None,
                web_password if web_password else None
            )
            
            # 保存所有配置到 frpc_config.json
            save_all_config_to_json(
                server_addr=server_ip,
                server_port=server_port_int,
                token=token if token else '',
                web_addr=web_ip,
                web_port=web_port_int,
                web_username=web_username if web_username else '',
                web_password=web_password if web_password else '',
                log_level=log_level,
                frpc_exe_path=frpc_exe_path if frpc_exe_path else '',
                port_range_min=min_port_int,
                port_range_max=max_port_int,
                enable_subdomain=enable_subdomain_var.get()
            )
            
            if existing_config:
                messagebox.showinfo("成功", "配置文件已更新：frpc.toml")
            else:
                messagebox.showinfo("成功", "配置文件已生成：frpc.toml")
            config_saved[0] = True  # 标记配置已保存
            root.destroy()
            if parent:
                parent.attributes('-disabled', False)
                parent.deiconify()  # 如果窗口被最小化，先恢复窗口
                parent.lift()  # 将父窗口提升到最前面
                parent.focus_set()  # 让父窗口获得焦点
        except Exception as e:
            messagebox.showerror("错误", f"生成配置文件失败：{str(e)}")
    
    def on_close():
        """窗口关闭时的处理"""
        if parent:
            # 如果有父窗口，先恢复父窗口状态
            root.destroy()
            parent.attributes('-disabled', False)
            parent.deiconify()  # 如果窗口被最小化，先恢复窗口
            parent.lift()  # 将父窗口提升到最前面
            parent.focus_set()  # 让父窗口获得焦点
        else:
            # 如果没有父窗口，先退出主循环，然后销毁窗口
            root.quit()
            root.destroy()
    
    # 按钮框架
    button_frame = ttk.Frame(frame)
    button_frame.grid(row=11, column=0, columnspan=2, pady=20)
    
    # 保存按钮
    save_button = ttk.Button(button_frame, text="保存", command=save_config)
    save_button.pack(side=tk.LEFT, padx=10)
    
    # 取消按钮
    cancel_button = ttk.Button(button_frame, text="取消", command=on_close)
    cancel_button.pack(side=tk.LEFT, padx=10)
    
    # 绑定关闭事件
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    if parent:
        # 如果是子窗口，禁用父窗口
        parent.attributes('-disabled', True)
        root.wait_window()
        return config_saved[0]
    else:
        # 如果是独立窗口，运行主循环
        root.mainloop()
        return config_saved[0]


def init_frpc_config():
    """
    初始化 FRPC 配置，如果不存在则提示设置
    
    返回:
        bool: 如果配置文件存在或已成功创建返回 True，如果用户取消了配置返回 False
    """
    if not check_frpc_config():
        # 显示设置窗口，如果用户保存了配置返回 True，否则返回 False
        saved = show_settings_window()
        # 如果用户保存了配置，再次检查配置文件是否存在
        if saved and check_frpc_config():
            return True
        # 如果用户取消了，返回 False
        return False
    return True


if __name__ == '__main__':
    # 测试代码
    if not check_frpc_config():
        print("未找到 frpc.toml 文件，显示设置窗口...")
        show_settings_window()
    else:
        print("已找到 frpc.toml 文件")
