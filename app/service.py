import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from .setting import check_frpc_config, show_settings_window, get_frpc_exe_path, load_frpc_toml
from .proxy import ProxyManager
from .log import LogManager
from .theme import COLORS, FONT_SMALL, FONT_UI, NavButton, apply_theme, create_card
from .util import center_window
from .config_api import check_frpc_service_status
from .version import APP_NAME, get_version_display
import threading


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {get_version_display()}")
        self.root.geometry("980x640")
        self.root.minsize(880, 560)
        apply_theme(self.root)
        self.root.configure(bg=COLORS["bg"])

        main_container = tk.Frame(root, bg=COLORS["bg"])
        main_container.pack(fill=tk.BOTH, expand=True)

        self.menu_frame = tk.Frame(main_container, width=220, bg=COLORS["sidebar"])
        self.menu_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.menu_frame.pack_propagate(False)

        self.content_frame = tk.Frame(main_container, bg=COLORS["bg"])
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 初始化内容区域和进程对象（需要在 init_menu 之前初始化）
        self.current_page = None
        self.frpc_process = None  # FRPC 进程对象
        
        # 初始化菜单
        self.init_menu()
        
        # 初始化代理管理器
        self.proxy_manager = ProxyManager(self.root, self.content_frame, self.refresh_proxy_callback)
        
        # 初始化日志管理器
        self.log_manager = LogManager(self.root, self.content_frame)
        
        self.show_status_page()
        
        # 延迟检测已运行的进程（等待 UI 创建完成，在后台线程中执行避免阻塞）
        self.root.after(100, lambda: self.detect_existing_frpc_process_async())
        
        # 绑定窗口关闭事件，确保进程被清理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def refresh_proxy_callback(self):
        """代理刷新回调"""
        if hasattr(self, 'proxy_manager'):
            self.proxy_manager.refresh_proxy_list()
    
    def init_menu(self):
        """初始化左侧菜单"""
        brand = tk.Frame(self.menu_frame, bg=COLORS["sidebar"])
        brand.pack(fill=tk.X, padx=20, pady=(28, 18))
        tk.Label(
            brand,
            text=APP_NAME,
            font=("Microsoft YaHei UI", 14, "bold"),
            bg=COLORS["sidebar"],
            fg="#ffffff",
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            brand,
            text="内网穿透桌面客户端",
            font=FONT_SMALL,
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_muted"],
            anchor="w",
        ).pack(fill=tk.X, pady=(4, 0))

        tk.Frame(self.menu_frame, bg="#2a3040", height=1).pack(fill=tk.X, padx=16, pady=(0, 12))

        menu_items = [
            ("服务", self.show_status_page),
            ("代理", self.show_proxy_page),
            ("日志", self.show_log_page),
            ("设置", self.show_settings_page),
        ]

        self.menu_buttons = []
        for text, command in menu_items:
            btn = NavButton(self.menu_frame, text, command)
            btn.pack(fill=tk.X, padx=8, pady=2)
            self.menu_buttons.append(btn)

        version_label = tk.Label(
            self.menu_frame,
            text=get_version_display(),
            font=FONT_SMALL,
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_muted"],
        )
        version_label.pack(side=tk.BOTTOM, pady=18)

        self.update_proxy_menu_state()
        self.update_settings_menu_state()
    
    def clear_content(self):
        """清空右侧内容区域"""
        # 停止日志自动刷新
        if hasattr(self, 'log_manager'):
            self.log_manager.stop_auto_refresh()
        
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_status_page(self):
        """显示状态页面"""
        self.clear_content()
        self.current_page = "status"
        
        # 更新菜单按钮状态
        self.update_menu_highlight(0)
        
        status_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        status_frame.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        ttk.Label(status_frame, text="服务状态", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            status_frame,
            text="启动或停止 FRPC，并查看当前运行情况",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(4, 18))

        card_wrap, info_frame = create_card(status_frame, padding=28)
        card_wrap.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(info_frame, bg=COLORS["card"])
        header.pack(fill=tk.X)

        self.status_dot = tk.Canvas(
            header, width=14, height=14, bg=COLORS["card"], highlightthickness=0
        )
        self.status_dot.pack(side=tk.LEFT)
        self._draw_status_dot(COLORS["muted"])

        self.status_label = tk.Label(
            header,
            text="未启动",
            font=("Microsoft YaHei UI", 18, "bold"),
            bg=COLORS["card"],
            fg=COLORS["text"],
        )
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))

        self.status_hint = tk.Label(
            info_frame,
            text="服务尚未运行，配置完成后即可启动。",
            font=FONT_UI,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            anchor="w",
            justify=tk.LEFT,
        )
        self.status_hint.pack(fill=tk.X, pady=(12, 0))

        self.progress_frame = tk.Frame(info_frame, bg=COLORS["card"])
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode="indeterminate",
            length=280,
        )
        self.progress_label = tk.Label(
            self.progress_frame,
            text="处理中...",
            font=FONT_UI,
            bg=COLORS["card"],
            fg=COLORS["muted"],
        )

        button_frame = tk.Frame(info_frame, bg=COLORS["card"])
        button_frame.pack(pady=(28, 0), anchor=tk.W)

        self.start_button = ttk.Button(
            button_frame,
            text="启动服务",
            command=self.start_frpc,
            style="Accent.TButton",
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(
            button_frame,
            text="停止服务",
            command=self.stop_frpc,
            style="Danger.TButton",
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT)
        
        # 根据实际服务状态更新 UI
        self.update_status_ui()
    
    def show_proxy_page(self):
        """显示代理页面"""
        # 检查服务是否已启动
        if not self.is_service_running():
            messagebox.showwarning("提示", "请先启动 FRPC 服务")
            # 切换到服务页面
            self.show_status_page()
            return
        
        self.clear_content()
        self.current_page = "proxy"
        
        # 更新菜单按钮状态
        self.update_menu_highlight(1)
        
        # 使用代理管理器显示代理页面
        self.proxy_manager.show_proxy_page()
    
    def show_log_page(self):
        """显示日志页面"""
        self.clear_content()
        self.current_page = "log"
        
        # 更新菜单按钮状态
        self.update_menu_highlight(2)
        
        # 使用日志管理器显示日志页面
        self.log_manager.show_log_page()
    
    def show_settings_page(self):
        """显示设置页面 - 打开设置窗口"""
        # 检查服务是否正在运行
        if self.is_service_running():
            messagebox.showwarning("提示", "请先停止 FRPC 服务才能打开设置")
            return
        
        show_settings_window(self.root)
        page_index = {"status": 0, "proxy": 1, "log": 2}
        if self.current_page in page_index:
            self.update_menu_highlight(page_index[self.current_page])
    
    def update_menu_highlight(self, active_index):
        """更新菜单按钮高亮状态"""
        for i, btn in enumerate(self.menu_buttons):
            btn.set_active(i == active_index)

    def _draw_status_dot(self, color):
        if not hasattr(self, "status_dot") or self.status_dot is None:
            return
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline=color)

    def _set_status_text(self, title, hint, color):
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.config(text=title, fg=color)
        if hasattr(self, "status_hint") and self.status_hint:
            self.status_hint.config(text=hint)
        self._draw_status_dot(color)
    
    def is_service_running(self):
        """检查服务是否正在运行"""
        # 如果进程对象存在且正在运行
        if self.frpc_process is not None:
            if self.frpc_process.poll() is None:
                return True
            else:
                # 进程已结束，清理引用
                self.frpc_process = None
        
        # 检查是否有其他 frpc 进程在运行（通过 API 检测）
        status_code = check_frpc_service_status()
        return status_code == 200
    
    
    def detect_existing_frpc_process_async(self):
        """异步检测是否已有 frpc 进程在运行（在后台线程中执行）"""
        def check_thread():
            status_code = check_frpc_service_status()
            if status_code == 200:
                # 检测到服务在运行，更新 UI 状态（在主线程中执行）
                self.root.after(0, self._update_ui_for_external_process)
        
        # 在后台线程中执行检测，避免阻塞UI
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def _update_ui_for_external_process(self):
        """更新UI以显示外部启动的进程"""
        # 检测到服务在运行，更新 UI 状态
        # 注意：不设置 self.frpc_process，因为不是我们启动的进程
        if hasattr(self, 'status_label') and self.status_label:
            self._set_status_text(
                "运行中（外部启动）",
                "检测到已有 FRPC 进程在运行，当前窗口不会接管该进程。",
                COLORS["warning"],
            )
            if hasattr(self, 'start_button') and self.start_button:
                self.start_button.config(state=tk.DISABLED)
            if hasattr(self, 'stop_button') and self.stop_button:
                # 外部启动的进程无法通过我们的 stop 按钮停止
                self.stop_button.config(state=tk.DISABLED)
        # 启用代理菜单
        self.update_proxy_menu_state()
        # 禁用设置菜单（服务运行时）
        self.update_settings_menu_state()
    
    def update_proxy_menu_state(self):
        """更新代理菜单按钮的启用/禁用状态"""
        if len(self.menu_buttons) > 1:
            proxy_button = self.menu_buttons[1]  # 代理按钮是第二个（索引为1）
            proxy_button.set_enabled(self.is_service_running())
    
    def update_settings_menu_state(self):
        """更新设置菜单按钮的启用/禁用状态"""
        if len(self.menu_buttons) > 3:
            settings_button = self.menu_buttons[3]  # 设置按钮是第四个（索引为3）
            settings_button.set_enabled(not self.is_service_running())
    
    def update_status_ui(self):
        """根据实际服务状态更新状态页面的 UI"""
        if not hasattr(self, 'status_label') or self.status_label is None:
            return
        
        if self.frpc_process is not None and self.frpc_process.poll() is None:
            self._set_status_text("运行中", "FRPC 服务已启动，可以管理代理。", COLORS["success"])
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        elif self.is_service_running():
            self._set_status_text(
                "运行中（外部启动）",
                "检测到已有 FRPC 进程在运行，当前窗口不会接管该进程。",
                COLORS["warning"],
            )
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
        else:
            self._set_status_text("未启动", "服务尚未运行，配置完成后即可启动。", COLORS["muted"])
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def show_loading(self, message="处理中..."):
        """显示加载状态"""
        if not hasattr(self, 'progress_frame') or self.progress_frame is None:
            return
        
        self.progress_label.config(text=message)
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))
        self.progress_bar.pack(side=tk.LEFT)
        self.progress_frame.pack(pady=(16, 0), anchor=tk.W)
        self.progress_bar.start(10)  # 开始动画
        
        # 禁用按钮
        if hasattr(self, 'start_button'):
            self.start_button.config(state=tk.DISABLED)
        if hasattr(self, 'stop_button'):
            self.stop_button.config(state=tk.DISABLED)
    
    def hide_loading(self):
        """隐藏加载状态"""
        if not hasattr(self, 'progress_frame') or self.progress_frame is None:
            return
        
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
    
    def start_frpc(self):
        """启动 FRPC 服务"""
        # 检查配置文件是否存在
        if not os.path.exists('frpc.toml'):
            messagebox.showerror("错误", "未找到 frpc.toml 配置文件")
            return
        
        # 获取 frpc.exe 路径
        frpc_exe_path = get_frpc_exe_path()
        if not frpc_exe_path or not os.path.exists(frpc_exe_path):
            if messagebox.askyesno(
                "未找到客户端",
                "未找到 frpc.exe。\n是否打开设置，从 GitHub Releases 选择版本下载？",
            ):
                show_settings_window(self.root)
            return
        
        # 检查进程是否已经在运行
        if self.frpc_process is not None:
            # 检查进程是否还在运行
            if self.frpc_process.poll() is None:
                messagebox.showwarning("提示", "FRPC 服务已在运行中")
                return
            else:
                # 进程已结束，清理引用
                self.frpc_process = None
        
        # 检查是否有其他 frpc 进程在运行（通过 API 检测）
        status_code = check_frpc_service_status()
        if status_code == 200:
            messagebox.showwarning("提示", "FRPC 服务已在运行中（可能是外部启动的）")
            # 更新 UI 状态
            self.update_status_ui()
            self.update_proxy_menu_state()
            self.update_settings_menu_state()
            return
        
        # 显示加载状态
        self.show_loading("正在启动服务...")
        
        # 在后台线程中启动服务
        def start_thread():
            try:
                # 启动 FRPC 进程
                # 使用 subprocess.Popen 启动，不显示控制台窗口
                self.frpc_process = subprocess.Popen(
                    [frpc_exe_path, '-c', 'frpc.toml'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 等待一小段时间，确保进程启动
                import time
                time.sleep(0.5)
                
                # 检查进程是否成功启动
                if self.frpc_process.poll() is not None:
                    # 进程已退出，启动失败
                    error_msg = "服务启动失败"
                    try:
                        _, stderr = self.frpc_process.communicate(timeout=1)
                        if stderr:
                            error_msg = stderr.decode('utf-8', errors='ignore')[:200]
                    except:
                        pass
                    
                    self.root.after(0, lambda: self._start_failed(error_msg))
                    return
                
                # 更新 UI（在主线程中执行）
                self.root.after(0, lambda: self._start_success())
                
            except Exception as e:
                self.root.after(0, lambda: self._start_failed(str(e)))
        
        # 启动后台线程
        thread = threading.Thread(target=start_thread, daemon=True)
        thread.start()
    
    def _start_success(self):
        """启动成功的回调"""
        self.hide_loading()
        
        # 更新 UI
        self._set_status_text("运行中", "FRPC 服务已启动，可以管理代理。", COLORS["success"])
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 启用代理菜单按钮
        self.update_proxy_menu_state()
        # 禁用设置菜单按钮（服务运行时）
        self.update_settings_menu_state()
        
        messagebox.showinfo("成功", "FRPC 服务已启动")
    
    def _start_failed(self, error_msg):
        """启动失败的回调"""
        self.hide_loading()
        
        if self.frpc_process:
            self.frpc_process = None
        
        self._set_status_text("启动失败", "请检查配置、客户端路径和服务器连通性。", COLORS["danger"])
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 禁用代理菜单按钮
        self.update_proxy_menu_state()
        # 启用设置菜单按钮（服务未运行时）
        self.update_settings_menu_state()
        
        messagebox.showerror("错误", f"启动 FRPC 服务失败：{error_msg}")
    
    def stop_frpc(self):
        """停止 FRPC 服务"""
        # 检查是否是我们启动的进程
        if self.frpc_process is None:
            # 检查是否有外部启动的进程
            status_code = check_frpc_service_status()
            if status_code == 200:
                messagebox.showwarning("提示", "FRPC 服务正在运行，但该进程不是由此程序启动的，无法通过此程序停止。\n请手动停止该进程。")
            else:
                messagebox.showwarning("提示", "FRPC 服务未运行")
            return
        
        # 检查进程是否还在运行
        if self.frpc_process.poll() is not None:
            # 进程已经结束
            self.frpc_process = None
            self.update_status_ui()
            self.update_proxy_menu_state()
            self.update_settings_menu_state()
            return
        
        # 显示加载状态
        self.show_loading("正在停止服务...")
        
        # 在后台线程中停止服务
        def stop_thread():
            try:
                # 进程还在运行，终止它
                self.frpc_process.terminate()
                
                # 等待进程结束，最多等待 5 秒
                try:
                    self.frpc_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果进程没有响应，强制杀死
                    self.frpc_process.kill()
                    self.frpc_process.wait()
                
                # 清理进程引用
                self.frpc_process = None
                
                # 更新 UI（在主线程中执行）
                self.root.after(0, lambda: self._stop_success())
                
            except Exception as e:
                # 即使出错也清理引用
                self.frpc_process = None
                self.root.after(0, lambda: self._stop_failed(str(e)))
        
        # 启动后台线程
        thread = threading.Thread(target=stop_thread, daemon=True)
        thread.start()
    
    def _stop_success(self):
        """停止成功的回调"""
        self.hide_loading()
        
        # 更新 UI
        self._set_status_text("已停止", "服务已停止，可以修改设置或重新启动。", COLORS["muted"])
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 禁用代理菜单按钮
        self.update_proxy_menu_state()
        # 启用设置菜单按钮（服务停止后）
        self.update_settings_menu_state()
        
        # 如果当前在代理页面，切换回服务页面
        if self.current_page == "proxy":
            self.show_status_page()
        
        messagebox.showinfo("成功", "FRPC 服务已停止")
    
    def _stop_failed(self, error_msg):
        """停止失败的回调"""
        self.hide_loading()
        
        self._set_status_text("已停止", "停止过程出现异常，请确认进程是否仍在运行。", COLORS["warning"])
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # 禁用代理菜单按钮
        self.update_proxy_menu_state()
        # 启用设置菜单按钮（服务停止后）
        self.update_settings_menu_state()
        
        # 如果当前在代理页面，切换回服务页面
        if self.current_page == "proxy":
            self.show_status_page()
        
        messagebox.showerror("错误", f"停止 FRPC 服务失败：{error_msg}")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        # 停止日志自动刷新
        if hasattr(self, 'log_manager'):
            self.log_manager.stop_auto_refresh()
        
        # 如果进程还在运行，先停止它
        if self.frpc_process is not None and self.frpc_process.poll() is None:
            try:
                self.frpc_process.terminate()
                try:
                    self.frpc_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.frpc_process.kill()
                    self.frpc_process.wait()
            except:
                pass
            self.frpc_process = None
        
        # 关闭窗口
        self.root.destroy()


def show_main_window():
    """显示主窗口"""
    if not check_frpc_config():
        return False
    
    root = tk.Tk()
    root.withdraw()
    apply_theme(root)
    MainWindow(root)
    center_window(root, 980, 640)
    root.deiconify()
    root.mainloop()
    return True


if __name__ == '__main__':
    show_main_window()
