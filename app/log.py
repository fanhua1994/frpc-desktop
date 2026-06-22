import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext


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
        log_frame = ttk.Frame(self.content_frame, padding="20")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题和按钮区域
        header_frame = ttk.Frame(log_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="运行日志",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # 按钮区域（右侧）
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # 清空按钮
        clear_button = ttk.Button(
            button_frame,
            text="清空",
            command=self.clear_log,
            width=10
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 刷新按钮
        refresh_button = ttk.Button(
            button_frame,
            text="刷新",
            command=self.refresh_log,
            width=10
        )
        refresh_button.pack(side=tk.LEFT)
        
        # 日志显示区域
        log_text_frame = ttk.LabelFrame(log_frame, text="日志内容", padding="10")
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 使用 ScrolledText 显示日志
        self.log_text = scrolledtext.ScrolledText(
            log_text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4",
            state=tk.DISABLED  # 只读模式
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
