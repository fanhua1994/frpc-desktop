import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from .theme import COLORS, create_card


class LogManager:
    """日志管理器"""
    
    def __init__(self, root, content_frame):
        self.root = root
        self.content_frame = content_frame
        self.log_text = None
        self.auto_refresh_id = None
        self.log_file = 'frpc.log'
    
    def show_log_page(self):
        """显示日志页面"""
        # 清空内容区域
        self.clear_log_page()
        
        # 日志页面内容
        log_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        header_frame = tk.Frame(log_frame, bg=COLORS["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 16))

        title_box = tk.Frame(header_frame, bg=COLORS["bg"])
        title_box.pack(side=tk.LEFT)
        ttk.Label(title_box, text="运行日志", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="实时查看 frpc.log", style="Muted.TLabel").pack(anchor=tk.W, pady=(4, 0))

        button_frame = tk.Frame(header_frame, bg=COLORS["bg"])
        button_frame.pack(side=tk.RIGHT)

        clear_button = ttk.Button(
            button_frame,
            text="清空",
            command=self.clear_log,
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 8))

        refresh_button = ttk.Button(
            button_frame,
            text="刷新",
            command=self.refresh_log,
            style="Accent.TButton",
        )
        refresh_button.pack(side=tk.LEFT)

        card_wrap, log_text_frame = create_card(log_frame, padding=12)
        card_wrap.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief=tk.FLAT,
            borderwidth=0,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 初始加载日志
        self.refresh_log()
        
        # 设置定时刷新（每2秒自动刷新一次）
        self.start_auto_refresh()
    
    def clear_log_page(self):
        """清空日志页面"""
        # 停止自动刷新
        self.stop_auto_refresh()
        
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.log_text = None
    
    def refresh_log(self):
        """刷新日志内容"""
        # 检查日志文本区域是否存在
        if self.log_text is None:
            return
        
        try:
            # 启用文本区域进行编辑
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            
            if os.path.exists(self.log_file):
                try:
                    with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        self.log_text.insert(tk.END, content)
                except Exception as e:
                    self.log_text.insert(tk.END, f"读取日志文件失败: {str(e)}\n")
            else:
                self.log_text.insert(tk.END, "日志文件不存在: frpc.log\n")
                self.log_text.insert(tk.END, "请确保 FRPC 服务已启动并配置了日志输出。\n")
            
            # 禁用文本区域（只读模式）
            self.log_text.config(state=tk.DISABLED)
            
            # 自动滚动到底部
            self.log_text.see(tk.END)
        except Exception as e:
            # 如果出错，尝试恢复只读状态
            try:
                if self.log_text:
                    self.log_text.config(state=tk.DISABLED)
            except:
                pass
    
    def clear_log(self):
        """清空日志文件"""
        # 确认对话框
        if not messagebox.askyesno("确认", "确定要清空日志文件吗？"):
            return
        
        try:
            # 清空日志文件
            if os.path.exists(self.log_file):
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write('')  # 写入空内容
            
            # 刷新显示
            self.refresh_log()
            
            messagebox.showinfo("成功", "日志文件已清空")
        except Exception as e:
            messagebox.showerror("错误", f"清空日志文件失败：{str(e)}")
    
    def start_auto_refresh(self):
        """启动自动刷新"""
        # 检查日志文本区域是否存在
        if self.log_text is None:
            return
        
        self.refresh_log()
        # 每2秒刷新一次
        self.auto_refresh_id = self.root.after(2000, self.start_auto_refresh)
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        if self.auto_refresh_id:
            self.root.after_cancel(self.auto_refresh_id)
            self.auto_refresh_id = None
