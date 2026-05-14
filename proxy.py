import tkinter as tk
from tkinter import ttk, messagebox
from setting import load_frpc_toml, get_port_range, get_web_auth_from_json, get_config_from_json
from config_api import get_proxy_status, write_config_file, read_frpc_toml_content
from util import validate_ip_address, validate_port, center_window


def generate_frpc_toml_with_proxies(server_addr, server_port, token=None, web_addr="127.0.0.1", web_port=7400, log_level="info", web_user=None, web_password=None, proxies=None):
    """
    生成包含代理配置的完整 frpc.toml 文件
    
    参数:
        server_addr: 服务器地址
        server_port: 服务器端口
        token: 认证 token（可选）
        web_addr: Web 服务地址
        web_port: Web 服务端口
        log_level: 日志级别
        web_user: Web 服务用户名（可选）
        web_password: Web 服务密码（可选）
        proxies: 代理配置列表
    """
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
    
    # 添加代理配置
    if proxies:
        for proxy in proxies:
            config_content += '\n[[proxies]]\n'
            config_content += f'name = "{proxy.get("name", "")}"\n'
            config_content += f'type = "{proxy.get("type", "")}"\n'
            
            # enabled (默认 true)
            if 'enabled' in proxy:
                config_content += f'enabled = {str(proxy["enabled"]).lower()}\n'
            
            # localIP
            if 'localIP' in proxy:
                config_content += f'localIP = "{proxy["localIP"]}"\n'
            
            # localPort
            if 'localPort' in proxy:
                config_content += f'localPort = {proxy["localPort"]}\n'
            
            # remotePort
            if 'remotePort' in proxy:
                config_content += f'remotePort = {proxy["remotePort"]}\n'
            
            # subdomain
            if 'subdomain' in proxy:
                config_content += f'subdomain = "{proxy["subdomain"]}"\n'
            
            # customDomains
            if 'customDomains' in proxy and proxy['customDomains']:
                domains = proxy['customDomains']
                if isinstance(domains, list):
                    domains_str = ', '.join([f'"{d}"' for d in domains])
                    config_content += f'customDomains = [{domains_str}]\n'
                else:
                    config_content += f'customDomains = ["{domains}"]\n'
            
            # annotations (map[string]string)
            if 'annotations' in proxy and proxy['annotations']:
                for key, value in proxy['annotations'].items():
                    config_content += f'annotations.{key} = "{value}"\n'
    
    with open('frpc.toml', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    return True


class ProxyManager:
    """代理管理类"""
    
    def __init__(self, parent_window, content_frame, refresh_callback=None):
        """
        初始化代理管理器
        
        参数:
            parent_window: 父窗口
            content_frame: 内容框架
            refresh_callback: 刷新回调函数
        """
        self.parent_window = parent_window
        self.content_frame = content_frame
        self.refresh_callback = refresh_callback
        self.proxy_tree = None
    
    def show_proxy_page(self):
        """显示代理页面"""
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 代理页面内容
        proxy_frame = ttk.Frame(self.content_frame, padding="20")
        proxy_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题和按钮区域
        header_frame = ttk.Frame(proxy_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="代理配置",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # 刷新按钮
        refresh_button = ttk.Button(
            header_frame,
            text="刷新",
            command=self.refresh_proxy_list,
            width=10
        )
        refresh_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 新增按钮
        add_button = ttk.Button(
            header_frame,
            text="新增",
            command=self.add_proxy,
            width=10
        )
        add_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 删除按钮
        delete_button = ttk.Button(
            header_frame,
            text="删除",
            command=self.delete_proxy,
            width=10
        )
        delete_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 代理列表区域
        list_frame = ttk.LabelFrame(proxy_frame, text="代理列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建 Treeview 显示代理列表
        columns = ('name', 'type', 'status', 'local_addr', 'remote_addr')
        self.proxy_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题和宽度
        self.proxy_tree.heading('name', text='名称')
        self.proxy_tree.heading('type', text='类型')
        self.proxy_tree.heading('status', text='状态')
        self.proxy_tree.heading('local_addr', text='本地地址')
        self.proxy_tree.heading('remote_addr', text='远程地址')
        
        self.proxy_tree.column('name', width=120)
        self.proxy_tree.column('type', width=80)
        self.proxy_tree.column('status', width=100)
        self.proxy_tree.column('local_addr', width=150)
        self.proxy_tree.column('remote_addr', width=150)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.proxy_tree.yview)
        self.proxy_tree.configure(yscrollcommand=scrollbar.set)
        
        self.proxy_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件编辑代理
        self.proxy_tree.bind('<Double-1>', self.edit_proxy)
        
        # 绑定右键菜单
        self.proxy_tree.bind('<Button-3>', self.show_context_menu)
        
        # 初始加载代理列表
        self.refresh_proxy_list()
    
    def refresh_proxy_list(self):
        """刷新代理列表"""
        if not self.proxy_tree:
            return
        
        # 清空现有列表
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)
        
        # 从 status 接口加载代理列表
        status = get_proxy_status()
        
        if 'error' in status:
            self.proxy_tree.insert('', tk.END, values=('', '', status['error'], '', ''))
            return
        
        # 遍历所有类型的代理
        proxy_count = 0
        for proxy_type, proxy_list in status.items():
            if isinstance(proxy_list, list):
                for proxy in proxy_list:
                    name = proxy.get('name', '')
                    ptype = proxy.get('type', proxy_type)
                    status_text = proxy.get('status', 'unknown')
                    local_addr = proxy.get('local_addr', '')
                    remote_addr = proxy.get('remote_addr', '')
                    
                    self.proxy_tree.insert('', tk.END, values=(name, ptype, status_text, local_addr, remote_addr), tags=(name,))
                    proxy_count += 1
        
        if proxy_count == 0:
            self.proxy_tree.insert('', tk.END, values=('', '', '暂无代理', '', ''))
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击位置对应的项
        item = self.proxy_tree.identify_row(event.y)
        if not item:
            return
        
        # 选中该项
        self.proxy_tree.selection_set(item)
        
        # 获取该项的值
        item_values = self.proxy_tree.item(item, 'values')
        if not item_values or len(item_values) < 5:
            return
        
        remote_addr = item_values[4]  # remote_addr 在第5列（索引4）
        if not remote_addr or remote_addr.strip() == '':
            return
        
        # 创建右键菜单
        context_menu = tk.Menu(self.parent_window, tearoff=0)
        # 使用 functools.partial 或直接定义函数来避免 lambda 闭包问题
        def copy_remote_addr():
            self.copy_to_clipboard(remote_addr)
        
        context_menu.add_command(
            label=f"复制远程地址: {remote_addr}",
            command=copy_remote_addr
        )
        
        # 显示菜单
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # 延迟销毁菜单，确保命令能够执行
            self.parent_window.after(100, context_menu.destroy)
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        import subprocess
        import sys
        
        # 优先使用 Windows 的 clip 命令（最可靠）
        if sys.platform == 'win32':
            try:
                # 使用 subprocess.run 更简单可靠
                result = subprocess.run(
                    ['clip'],
                    input=text.encode('utf-8'),
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                messagebox.showinfo("成功", f"已复制到剪贴板: {text}")
                return
            except subprocess.CalledProcessError:
                pass  # 如果失败，尝试其他方法
            except Exception:
                pass  # 如果失败，尝试其他方法
        
        # 备用方法: 使用 Tkinter 剪贴板
        try:
            self.parent_window.clipboard_clear()
            self.parent_window.clipboard_append(text)
            # 在 Windows 上需要调用 update() 确保剪贴板操作完成
            self.parent_window.update()
            messagebox.showinfo("成功", f"已复制到剪贴板: {text}")
        except Exception as e:
            # 如果都失败了，显示错误信息并提示手动复制
            messagebox.showerror("错误", f"复制失败: {str(e)}\n\n请手动复制: {text}")
    
    def add_proxy(self):
        """新增代理"""
        self.show_proxy_edit_dialog()
    
    def edit_proxy(self, event=None):
        """编辑代理"""
        if not self.proxy_tree:
            return
        
        selection = self.proxy_tree.selection()
        if not selection:
            return
        
        item = self.proxy_tree.item(selection[0])
        proxy_name = item['values'][0] if item['values'] else None
        
        if not proxy_name:
            return
        
        # 从配置文件中读取代理信息
        config = load_frpc_toml()
        proxy_data = None
        
        if config and 'proxies' in config:
            for proxy in config['proxies']:
                if proxy.get('name') == proxy_name:
                    proxy_data = proxy
                    break
        
        self.show_proxy_edit_dialog(proxy_data)
    
    def delete_proxy(self):
        """删除代理"""
        if not self.proxy_tree:
            return
        
        # 获取选中的项
        selection = self.proxy_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的代理")
            return
        
        # 获取代理名称
        item = self.proxy_tree.item(selection[0])
        proxy_name = item['values'][0] if item['values'] else None
        
        if not proxy_name:
            messagebox.showwarning("提示", "无法获取代理名称")
            return
        
        # 将代理名称转换为字符串（处理数字类型的 name）
        proxy_name = str(proxy_name)
        
        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除代理 '{proxy_name}' 吗？"):
            return
        
        # 读取现有配置
        config = load_frpc_toml()
        if not config:
            messagebox.showerror("错误", "无法读取配置文件")
            return
        
        # 检查代理是否存在
        if 'proxies' not in config or not config['proxies']:
            messagebox.showwarning("提示", "没有可删除的代理")
            return
        
        # 查找并删除代理（将配置中的 name 也转换为字符串进行比较）
        original_count = len(config['proxies'])
        config['proxies'] = [p for p in config['proxies'] if str(p.get('name', '')) != proxy_name]
        
        if len(config['proxies']) == original_count:
            messagebox.showwarning("提示", f"未找到代理 '{proxy_name}'")
            return
        
        # 生成完整配置并写入
        try:
            # 优先从 frpc_config.json 读取 web 认证信息，如果没有则从 frpc.toml 读取
            web_username, web_password = get_web_auth_from_json()
            if not web_username or not web_password:
                # 如果 JSON 中没有，尝试从 toml 配置中读取
                web_user_from_toml = config.get('web_user', '')
                web_password_from_toml = config.get('web_password', '')
                if web_user_from_toml and web_password_from_toml:
                    web_username = web_user_from_toml
                    web_password = web_password_from_toml
            
            # 使用 generate_frpc_toml_with_proxies 生成包含代理的完整配置
            generate_frpc_toml_with_proxies(
                config['server_addr'],
                int(config['server_port']),
                config.get('token'),
                config.get('web_addr', '127.0.0.1'),
                int(config.get('web_port', 7400)),
                config.get('log_level', 'info'),
                web_username if web_username else None,
                web_password if web_password else None,
                config.get('proxies', [])
            )
            
            # 通过 API 写入配置
            new_content = read_frpc_toml_content()
            result = write_config_file(new_content, auto_reload=True)
            
            if 'error' in result:
                messagebox.showerror("错误", f"删除代理失败: {result['error']}")
            elif 'reload_error' in result:
                # 配置写入成功，但重载失败
                error_msg = f"代理已删除，但重载失败:\n{result['reload_error']}"
                if result.get('reload_response'):
                    error_msg += f"\n\n详细信息: {result['reload_response']}"
                messagebox.showerror("重载失败", error_msg)
                self.refresh_proxy_list()
            else:
                messagebox.showinfo("成功", f"代理 '{proxy_name}' 已删除")
                self.refresh_proxy_list()
        except Exception as e:
            messagebox.showerror("错误", f"删除代理失败: {str(e)}")
    
    def show_proxy_edit_dialog(self, proxy_data=None):
        """显示代理编辑对话框"""
        dialog = tk.Toplevel(self.parent_window)
        dialog.title("编辑代理" if proxy_data else "新增代理")
        dialog.geometry("500x450")
        dialog.resizable(False, False)
        dialog.transient(self.parent_window)
        dialog.grab_set()
        
        # 居中显示
        center_window(dialog)
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 全局开关：控制代理弹窗中是否显示“子域名”选项
        enable_subdomain = get_config_from_json('enable_subdomain', False)
        
        # 代理名称
        ttk.Label(frame, text="名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(frame, width=30)
        if proxy_data:
            name_entry.insert(0, proxy_data.get('name', ''))
            name_entry.config(state=tk.DISABLED)  # 编辑时名称不可修改
        name_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # 代理类型
        ttk.Label(frame, text="类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        type_combo = ttk.Combobox(frame, width=27, state="readonly")
        type_combo['values'] = ('tcp', 'udp', 'http', 'https', 'tcpmux', 'stcp', 'sudp', 'xtcp')
        if proxy_data:
            type_combo.set(proxy_data.get('type', 'tcp'))
        else:
            type_combo.set('tcp')
        type_combo.grid(row=1, column=1, pady=5, padx=10, sticky=tk.W)
        
        # 是否启用
        ttk.Label(frame, text="启用:").grid(row=2, column=0, sticky=tk.W, pady=5)
        enabled_var = tk.BooleanVar()
        enabled_var.set(proxy_data.get('enabled', True) if proxy_data else True)
        enabled_check = ttk.Checkbutton(frame, variable=enabled_var)
        enabled_check.grid(row=2, column=1, pady=5, padx=10, sticky=tk.W)
        
        # 本地IP
        ttk.Label(frame, text="本地IP:").grid(row=3, column=0, sticky=tk.W, pady=5)
        local_ip_entry = ttk.Entry(frame, width=30)
        if proxy_data and 'localIP' in proxy_data:
            local_ip_entry.insert(0, proxy_data['localIP'])
        local_ip_entry.grid(row=3, column=1, pady=5, padx=10)
        
        # 本地端口
        ttk.Label(frame, text="本地端口:").grid(row=4, column=0, sticky=tk.W, pady=5)
        local_port_entry = ttk.Entry(frame, width=30)
        if proxy_data and 'localPort' in proxy_data:
            local_port_entry.insert(0, str(proxy_data['localPort']))
        local_port_entry.grid(row=4, column=1, pady=5, padx=10)
        
        # 远程端口（用于 tcp/udp）
        remote_port_label = ttk.Label(frame, text="远程端口:")
        remote_port_entry = ttk.Entry(frame, width=30)
        if proxy_data and 'remotePort' in proxy_data:
            remote_port_entry.insert(0, str(proxy_data['remotePort']))
        
        # 子域名（用于 http/https/tcpmux）
        subdomain_label = ttk.Label(frame, text="子域名:")
        subdomain_entry = ttk.Entry(frame, width=30)
        if proxy_data and 'subdomain' in proxy_data:
            subdomain_entry.insert(0, proxy_data['subdomain'])
        
        # 自定义域名（用于 http/https/tcpmux）
        custom_domains_label = ttk.Label(frame, text="自定义域名(逗号分隔):")
        custom_domains_entry = ttk.Entry(frame, width=30)
        if proxy_data and 'customDomains' in proxy_data:
            if isinstance(proxy_data['customDomains'], list):
                custom_domains_entry.insert(0, ','.join(proxy_data['customDomains']))
            else:
                custom_domains_entry.insert(0, str(proxy_data['customDomains']))
        
        # 按钮框架（先创建，位置会动态调整）
        button_frame = ttk.Frame(frame)
        
        def update_fields_by_type(*args):
            """根据类型更新字段显示"""
            ptype = type_combo.get()
            
            # 隐藏所有可选字段
            remote_port_label.grid_remove()
            remote_port_entry.grid_remove()
            subdomain_label.grid_remove()
            subdomain_entry.grid_remove()
            custom_domains_label.grid_remove()
            custom_domains_entry.grid_remove()
            
            # 根据类型显示相应字段
            if ptype in ['tcp', 'udp']:
                # tcp/udp 需要远程端口
                remote_port_label.grid(row=5, column=0, sticky=tk.W, pady=5)
                remote_port_entry.grid(row=5, column=1, pady=5, padx=10)
                button_frame.grid(row=6, column=0, columnspan=2, pady=20)
            elif ptype in ['http', 'https', 'tcpmux']:
                # http/https/tcpmux 需要子域名或自定义域名
                if enable_subdomain:
                    subdomain_label.grid(row=5, column=0, sticky=tk.W, pady=5)
                    subdomain_entry.grid(row=5, column=1, pady=5, padx=10)
                    custom_domains_label.grid(row=6, column=0, sticky=tk.W, pady=5)
                    custom_domains_entry.grid(row=6, column=1, pady=5, padx=10)
                    button_frame.grid(row=7, column=0, columnspan=2, pady=20)
                else:
                    # 不显示“子域名”，改为只显示自定义域名
                    custom_domains_label.grid(row=5, column=0, sticky=tk.W, pady=5)
                    custom_domains_entry.grid(row=5, column=1, pady=5, padx=10)
                    button_frame.grid(row=6, column=0, columnspan=2, pady=20)
            else:
                # stcp, sudp, xtcp 不需要额外字段
                button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        # 绑定类型变化事件
        type_combo.bind('<<ComboboxSelected>>', update_fields_by_type)
        
        # 初始显示字段
        if proxy_data:
            update_fields_by_type()
        else:
            # 默认显示 tcp 的字段
            remote_port_label.grid(row=5, column=0, sticky=tk.W, pady=5)
            remote_port_entry.grid(row=5, column=1, pady=5, padx=10)
            button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def save_proxy():
            """保存代理配置"""
            name = name_entry.get().strip()
            ptype = type_combo.get().strip()
            enabled = enabled_var.get()
            local_ip = local_ip_entry.get().strip()
            local_port = local_port_entry.get().strip()
            
            # 验证必填项
            if not name:
                messagebox.showerror("错误", "请输入代理名称")
                return
            
            if not ptype:
                messagebox.showerror("错误", "请选择代理类型")
                return
            
            if not local_ip:
                messagebox.showerror("错误", "请输入本地IP")
                return
            
            # 校验本地 IP
            if not validate_ip_address(local_ip):
                messagebox.showerror("错误", "本地 IP 格式不正确，请输入有效的 IPv4 地址")
                return
            
            if not local_port:
                messagebox.showerror("错误", "请输入本地端口")
                return
            
            # 校验本地端口（1-65535）
            is_valid, local_port_int = validate_port(local_port, 1, 65535)
            if not is_valid:
                messagebox.showerror("错误", "本地端口必须在 1-65535 之间")
                return
            
            # 构建代理配置
            new_proxy = {
                'name': name,
                'type': ptype,
                'enabled': enabled,
                'localIP': local_ip,
                'localPort': local_port_int
            }
            
            # 根据类型验证和添加特定字段
            if ptype in ['tcp', 'udp']:
                # tcp/udp 需要远程端口
                remote_port = remote_port_entry.get().strip()
                if not remote_port:
                    messagebox.showerror("错误", "请输入远程端口")
                    return
                
                # 获取端口范围配置
                min_port, max_port = get_port_range()
                
                # 校验远程端口是否在配置的范围内
                is_valid, remote_port_int = validate_port(remote_port, min_port, max_port)
                if not is_valid:
                    messagebox.showerror("错误", f"远程端口必须在 {min_port}-{max_port} 之间（服务器端口范围）")
                    return
                
                new_proxy['remotePort'] = remote_port_int
            elif ptype in ['http', 'https', 'tcpmux']:
                # http/https/tcpmux 需要子域名或自定义域名
                custom_domains = custom_domains_entry.get().strip()
                existing_subdomain = proxy_data.get('subdomain', '').strip() if proxy_data else ''

                if enable_subdomain:
                    subdomain = subdomain_entry.get().strip()
                else:
                    # 未开启时不展示子域名输入框：
                    # 1) 若用户未填写 customDomains，则沿用已有子域名（避免编辑时无法保存）
                    # 2) 若用户填写了 customDomains，则不再写入子域名
                    subdomain = existing_subdomain if not custom_domains else ''
                
                if not subdomain and not custom_domains:
                    if enable_subdomain:
                        messagebox.showerror("错误", "请输入子域名或自定义域名（至少填写一个）")
                    else:
                        messagebox.showerror("错误", "请输入自定义域名（至少填写一个）")
                    return
                
                if subdomain:
                    new_proxy['subdomain'] = subdomain
                
                if custom_domains:
                    # 将逗号分隔的字符串转换为列表
                    domains_list = [d.strip() for d in custom_domains.split(',') if d.strip()]
                    if domains_list:
                        new_proxy['customDomains'] = domains_list
            # stcp, sudp, xtcp 不需要额外字段
            
            # 读取现有配置
            config = load_frpc_toml()
            if not config:
                messagebox.showerror("错误", "无法读取配置文件")
                dialog.destroy()
                return
            
            # 更新或添加代理
            if 'proxies' not in config:
                config['proxies'] = []
            
            # 如果是编辑，先删除旧配置
            if proxy_data:
                config['proxies'] = [p for p in config['proxies'] if p.get('name') != name]
            
            # 检查名称是否已存在
            if any(p.get('name') == name for p in config['proxies']):
                messagebox.showerror("错误", f"代理名称 '{name}' 已存在")
                return
            
            # 添加新代理
            config['proxies'].append(new_proxy)
            
            # 生成完整配置并写入
            try:
                # 优先从 frpc_config.json 读取 web 认证信息，如果没有则从 frpc.toml 读取
                web_username, web_password = get_web_auth_from_json()
                if not web_username or not web_password:
                    # 如果 JSON 中没有，尝试从 toml 配置中读取
                    web_user_from_toml = config.get('web_user', '')
                    web_password_from_toml = config.get('web_password', '')
                    if web_user_from_toml and web_password_from_toml:
                        web_username = web_user_from_toml
                        web_password = web_password_from_toml
                
                # 使用 generate_frpc_toml_with_proxies 生成包含代理的完整配置
                generate_frpc_toml_with_proxies(
                    config['server_addr'],
                    int(config['server_port']),
                    config.get('token'),
                    config.get('web_addr', '127.0.0.1'),
                    int(config.get('web_port', 7400)),
                    config.get('log_level', 'info'),
                    web_username if web_username else None,
                    web_password if web_password else None,
                    config.get('proxies', [])
                )
                
                # 通过 API 写入配置
                new_content = read_frpc_toml_content()
                result = write_config_file(new_content, auto_reload=True)
                
                if 'error' in result:
                    messagebox.showerror("错误", f"写入配置失败: {result['error']}")
                elif 'reload_error' in result:
                    # 配置写入成功，但重载失败
                    error_msg = f"配置已保存，但重载失败:\n{result['reload_error']}"
                    if result.get('reload_response'):
                        error_msg += f"\n\n详细信息: {result['reload_response']}"
                    messagebox.showerror("重载失败", error_msg)
                    dialog.destroy()
                    self.refresh_proxy_list()
                else:
                    messagebox.showinfo("成功", result.get('message', '代理配置已保存并重载'))
                    dialog.destroy()
                    self.refresh_proxy_list()
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {str(e)}")
        
        # 按钮已在 update_fields_by_type 中创建和定位
        save_button = ttk.Button(button_frame, text="保存", command=save_proxy)
        save_button.pack(side=tk.LEFT, padx=10)
        
        cancel_button = ttk.Button(button_frame, text="取消", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)
        
        dialog.focus_set()
