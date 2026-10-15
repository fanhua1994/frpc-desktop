import tkinter as tk
from tkinter import ttk, messagebox
from .setting import load_frpc_toml, get_port_range, get_web_auth_from_json, get_config_from_json
from .config_api import get_proxy_status, write_config_file, read_frpc_toml_content
from .theme import COLORS
from .util import (
    FRPC_TOML_FILE,
    LOG_FILE_TOML,
    ensure_config_dir,
    ensure_log_dir,
    validate_ip_address,
    validate_port,
    center_window,
)


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
log.to = "{LOG_FILE_TOML}"
log.level = "{log_level}"
'''
    
    # 添加代理配置
    if proxies:
        for proxy in proxies:
            config_content += '\n[[proxies]]\n'
            config_content += f'name = "{proxy.get("name", "")}"\n'
            config_content += f'type = "{proxy.get("type", "")}"\n'
            
            # enabled：关闭后不穿透，但配置仍保留在文件中
            enabled = proxy.get('enabled', True)
            config_content += f'enabled = {str(bool(enabled)).lower()}\n'
            
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
    
    ensure_config_dir()
    ensure_log_dir()
    with open(FRPC_TOML_FILE, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    return True


# frpc 重载后短暂中间态，需延迟刷新
_PENDING_PROXY_STATUSES = frozenset({'wait start', 'wait_start', 'new'})


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
        self._status_refresh_after_id = None
    
    def show_proxy_page(self):
        """显示代理页面"""
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 代理页面内容
        proxy_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        proxy_frame.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        header_frame = tk.Frame(proxy_frame, bg=COLORS["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 16))

        title_box = tk.Frame(header_frame, bg=COLORS["bg"])
        title_box.pack(side=tk.LEFT)
        ttk.Label(title_box, text="代理配置", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="管理当前隧道与端口映射", style="Muted.TLabel").pack(anchor=tk.W, pady=(4, 0))

        refresh_button = ttk.Button(
            header_frame,
            text="刷新",
            command=self.refresh_proxy_list,
        )
        refresh_button.pack(side=tk.RIGHT, padx=(8, 0))

        delete_button = ttk.Button(
            header_frame,
            text="删除",
            command=self.delete_proxy,
        )
        delete_button.pack(side=tk.RIGHT, padx=(8, 0))

        toggle_button = ttk.Button(
            header_frame,
            text="启用/禁用",
            command=self.toggle_proxy_enabled,
        )
        toggle_button.pack(side=tk.RIGHT, padx=(8, 0))

        edit_button = ttk.Button(
            header_frame,
            text="编辑",
            command=self.edit_proxy,
        )
        edit_button.pack(side=tk.RIGHT, padx=(8, 0))

        add_button = ttk.Button(
            header_frame,
            text="新增",
            command=self.add_proxy,
            style="Accent.TButton",
        )
        add_button.pack(side=tk.RIGHT, padx=(8, 0))

        list_wrap = tk.Frame(
            proxy_frame,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        list_wrap.pack(fill=tk.BOTH, expand=True)
        list_frame = tk.Frame(list_wrap, bg=COLORS["card"], padx=8, pady=8)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建 Treeview 显示代理列表
        columns = ('name', 'type', 'enabled', 'status', 'local_addr', 'remote_addr')
        self.proxy_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        # 隐藏树形列，避免占位导致表头与数据错位
        self.proxy_tree.column('#0', width=0, minwidth=0, stretch=False)

        column_specs = (
            ('name', '名称', 110, True),
            ('type', '类型', 70, False),
            ('enabled', '开关', 60, False),
            ('status', '状态', 100, False),
            ('local_addr', '本地地址', 150, True),
            ('remote_addr', '远程地址', 160, True),
        )
        for col_id, title, width, stretch in column_specs:
            # 表头与单元格统一左对齐，保证视觉列对齐
            self.proxy_tree.heading(col_id, text=title, anchor=tk.W)
            self.proxy_tree.column(
                col_id,
                width=width,
                minwidth=width,
                anchor=tk.W,
                stretch=stretch,
            )
        
        # 滚动条放在同一行布局，不挤压表头列宽计算
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.proxy_tree.yview)
        self.proxy_tree.configure(yscrollcommand=scrollbar.set)

        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.proxy_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # 绑定双击事件编辑代理
        self.proxy_tree.bind('<Double-1>', self.edit_proxy)
        
        # 绑定右键菜单
        self.proxy_tree.bind('<Button-3>', self.show_context_menu)
        
        # 初始加载代理列表
        self.refresh_proxy_list()
    
    def _format_local_addr(self, proxy):
        """根据配置拼本地地址"""
        local_ip = proxy.get('localIP', '')
        local_port = proxy.get('localPort', '')
        if local_ip and local_port != '':
            return f"{local_ip}:{local_port}"
        return local_ip or ''

    def _format_remote_addr(self, proxy):
        """根据配置拼远程地址展示"""
        if proxy.get('remotePort') not in (None, ''):
            return str(proxy['remotePort'])
        if proxy.get('subdomain'):
            return proxy['subdomain']
        custom_domains = proxy.get('customDomains')
        if custom_domains:
            if isinstance(custom_domains, list):
                return ','.join(str(d) for d in custom_domains)
            return str(custom_domains)
        return ''

    def refresh_proxy_list(self):
        """刷新代理列表（配置文件 + 运行状态，禁用代理也会显示）"""
        if not self.proxy_tree:
            return
        
        # 清空现有列表
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)

        config = load_frpc_toml() or {}
        config_proxies = config.get('proxies', []) or []

        # 运行状态按名称索引
        status_by_name = {}
        status = get_proxy_status() or {}
        status_error = status.get('error') if isinstance(status, dict) else None
        if isinstance(status, dict) and not status_error:
            for proxy_type, proxy_list in status.items():
                if isinstance(proxy_list, list):
                    for proxy in proxy_list:
                        name = str(proxy.get('name', ''))
                        if name:
                            status_by_name[name] = proxy

        # 以配置文件为准展示，确保关闭后数据仍可见
        proxy_count = 0
        for proxy in config_proxies:
            name = str(proxy.get('name', ''))
            if not name:
                continue
            ptype = proxy.get('type', '')
            enabled = bool(proxy.get('enabled', True))
            enabled_text = '开' if enabled else '关'
            runtime = status_by_name.get(name)

            if not enabled:
                status_text = '已禁用'
            elif runtime:
                status_text = self._display_status_text(runtime.get('status', 'unknown'))
            elif status_error:
                status_text = status_error
            else:
                status_text = '未知'

            if runtime:
                local_addr = runtime.get('local_addr') or self._format_local_addr(proxy)
                remote_addr = runtime.get('remote_addr') or self._format_remote_addr(proxy)
            else:
                local_addr = self._format_local_addr(proxy)
                remote_addr = self._format_remote_addr(proxy)

            self.proxy_tree.insert(
                '',
                tk.END,
                values=(name, ptype, enabled_text, status_text, local_addr, remote_addr),
                tags=(name,),
            )
            proxy_count += 1

        if proxy_count == 0:
            empty_status = status_error or '暂无代理'
            self.proxy_tree.insert('', tk.END, values=('', '', '', empty_status, '', ''))

    def _display_status_text(self, status_text):
        """将 frpc 中间态文案转为更友好的展示"""
        if status_text is None:
            return ''
        raw = str(status_text).strip()
        if raw.lower() in _PENDING_PROXY_STATUSES:
            return '启动中'
        return raw

    def _is_proxy_status_pending(self, proxy_name):
        """判断指定代理是否仍处于启动中间态"""
        status = get_proxy_status() or {}
        if not isinstance(status, dict) or status.get('error'):
            return False
        for proxy_list in status.values():
            if not isinstance(proxy_list, list):
                continue
            for proxy in proxy_list:
                if str(proxy.get('name', '')) != str(proxy_name):
                    continue
                return str(proxy.get('status', '')).strip().lower() in _PENDING_PROXY_STATUSES
        # 已启用但尚未出现在 status 接口中，视为仍在启动
        return True

    def _cancel_status_settle_refresh(self):
        """取消进行中的状态稳定轮询"""
        after_id = getattr(self, '_status_refresh_after_id', None)
        if not after_id:
            return
        try:
            self.parent_window.after_cancel(after_id)
        except Exception:
            pass
        self._status_refresh_after_id = None

    def _schedule_status_settle_refresh(self, proxy_name, attempts=8, interval_ms=500):
        """
        启用/重载后状态常短暂为 wait start，延迟轮询直到稳定。
        """
        self._cancel_status_settle_refresh()

        def poll(remaining):
            self._status_refresh_after_id = None
            if not self.proxy_tree:
                return
            try:
                if not self.proxy_tree.winfo_exists():
                    return
            except Exception:
                return

            self.refresh_proxy_list()
            if remaining <= 1:
                return
            if self._is_proxy_status_pending(proxy_name):
                self._status_refresh_after_id = self.parent_window.after(
                    interval_ms,
                    lambda: poll(remaining - 1),
                )

        # 先给 frpc 一点时间完成启动，再开始轮询
        self._status_refresh_after_id = self.parent_window.after(
            interval_ms,
            lambda: poll(attempts),
        )

    def _get_selected_proxy_name(self):
        """获取当前选中的代理名称"""
        if not self.proxy_tree:
            return None
        selection = self.proxy_tree.selection()
        if not selection:
            return None
        item = self.proxy_tree.item(selection[0])
        values = item.get('values') or []
        if not values:
            return None
        proxy_name = str(values[0]).strip()
        if not proxy_name or proxy_name in ('暂无代理',):
            return None
        return proxy_name

    def _write_config_with_proxies(self, config):
        """根据当前配置重写 frpc.toml 并通过 API 重载"""
        web_username, web_password = get_web_auth_from_json()
        if not web_username or not web_password:
            web_user_from_toml = config.get('web_user', '')
            web_password_from_toml = config.get('web_password', '')
            if web_user_from_toml and web_password_from_toml:
                web_username = web_user_from_toml
                web_password = web_password_from_toml

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

        new_content = read_frpc_toml_content()
        return write_config_file(new_content, auto_reload=True)

    def toggle_proxy_enabled(self):
        """切换代理启用状态：关闭后不穿透，配置数据保留"""
        proxy_name = self._get_selected_proxy_name()
        if not proxy_name:
            messagebox.showwarning("提示", "请先选择要切换开关的代理")
            return

        config = load_frpc_toml()
        if not config or not config.get('proxies'):
            messagebox.showerror("错误", "无法读取配置文件")
            return

        target = None
        for proxy in config['proxies']:
            if str(proxy.get('name', '')) == proxy_name:
                target = proxy
                break

        if not target:
            messagebox.showwarning("提示", f"未找到代理 '{proxy_name}'")
            return

        current_enabled = bool(target.get('enabled', True))
        target['enabled'] = not current_enabled
        action = '启用' if target['enabled'] else '禁用'

        try:
            result = self._write_config_with_proxies(config)
            # 本地文件已先写入，无论 API 成败都刷新列表以反映磁盘状态
            self.refresh_proxy_list()
            if 'error' in result:
                messagebox.showerror(
                    "错误",
                    f"本地配置已{action}，但同步到服务失败: {result['error']}\n请检查服务后点击刷新或再次切换。"
                )
            elif 'reload_error' in result:
                error_msg = f"代理已{action}，但重载失败:\n{result['reload_error']}"
                if result.get('reload_response'):
                    error_msg += f"\n\n详细信息: {result['reload_response']}"
                messagebox.showerror("重载失败", error_msg)
            else:
                # 启用后 status 常短暂返回 wait start，延迟轮询到稳定状态
                if target['enabled']:
                    self._schedule_status_settle_refresh(proxy_name)
                messagebox.showinfo("成功", f"代理 '{proxy_name}' 已{action}")
        except Exception as e:
            self.refresh_proxy_list()
            messagebox.showerror("错误", f"{action}失败: {str(e)}")
    
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
        if not item_values or len(item_values) < 6:
            return
        
        proxy_name = item_values[0]
        if not proxy_name or str(proxy_name).strip() in ('', '暂无代理'):
            return
        
        enabled_text = item_values[2]
        remote_addr = item_values[5]  # remote_addr 在第6列（索引5）
        
        # 创建右键菜单
        context_menu = tk.Menu(self.parent_window, tearoff=0)
        context_menu.add_command(
            label="编辑",
            command=self.edit_proxy
        )
        toggle_label = "禁用（保留配置）" if enabled_text == '开' else "启用"
        context_menu.add_command(
            label=toggle_label,
            command=self.toggle_proxy_enabled
        )
        if remote_addr and remote_addr.strip():
            context_menu.add_separator()
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
        
        # 双击时根据点击位置选中对应行
        if event:
            item_id = self.proxy_tree.identify_row(event.y)
            if not item_id:
                return
            self.proxy_tree.selection_set(item_id)
            self.proxy_tree.focus(item_id)
        
        selection = self.proxy_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的代理")
            return
        
        item = self.proxy_tree.item(selection[0])
        proxy_name = item['values'][0] if item['values'] else None
        
        if not proxy_name or str(proxy_name).strip() in ('', '暂无代理'):
            return
        
        proxy_name = str(proxy_name)
        
        # 从配置文件中读取代理信息
        config = load_frpc_toml()
        if not config:
            messagebox.showerror("错误", "无法读取配置文件")
            return
        
        proxy_data = None
        if 'proxies' in config:
            for proxy in config['proxies']:
                if str(proxy.get('name', '')) == proxy_name:
                    proxy_data = proxy
                    break
        
        if not proxy_data:
            messagebox.showwarning("提示", f"未在配置文件中找到代理 '{proxy_name}'")
            return
        
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
            result = self._write_config_with_proxies(config)

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
        dialog.configure(bg=COLORS["bg"])
        dialog.geometry("560x500")
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
        
        # 是否启用（关闭后不穿透，配置数据保留）
        ttk.Label(frame, text="启用穿透:").grid(row=2, column=0, sticky=tk.W, pady=5)
        enabled_var = tk.BooleanVar()
        enabled_var.set(proxy_data.get('enabled', True) if proxy_data else True)
        enabled_check = ttk.Checkbutton(frame, text="关闭后保留配置，仅停止穿透", variable=enabled_var)
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
            if proxy_data:
                name = str(proxy_data.get('name', '')).strip()
            else:
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
            
            # 编辑时保留原有 annotations
            if proxy_data and proxy_data.get('annotations'):
                new_proxy['annotations'] = proxy_data['annotations']
            
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
                old_name = str(proxy_data.get('name', ''))
                config['proxies'] = [p for p in config['proxies'] if str(p.get('name', '')) != old_name]
            
            # 检查名称是否已存在
            if any(str(p.get('name', '')) == name for p in config['proxies']):
                messagebox.showerror("错误", f"代理名称 '{name}' 已存在")
                return
            
            # 添加新代理
            config['proxies'].append(new_proxy)
            
            # 生成完整配置并写入
            try:
                result = self._write_config_with_proxies(config)

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
                    action = "更新" if proxy_data else "保存"
                    messagebox.showinfo("成功", result.get('message', f'代理配置已{action}并重载'))
                    dialog.destroy()
                    self.refresh_proxy_list()
                    if enabled:
                        self._schedule_status_settle_refresh(name)
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {str(e)}")
        
        # 按钮已在 update_fields_by_type 中创建和定位
        save_button = ttk.Button(button_frame, text="保存", command=save_proxy)
        save_button.pack(side=tk.LEFT, padx=10)
        
        cancel_button = ttk.Button(button_frame, text="取消", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)
        
        dialog.focus_set()
