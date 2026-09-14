"""界面主题与通用控件样式"""
import tkinter as tk
from tkinter import ttk

COLORS = {
    "sidebar": "#12141a",
    "sidebar_hover": "#1e2330",
    "sidebar_active": "#2563eb",
    "sidebar_text": "#e8eaed",
    "sidebar_muted": "#8b93a7",
    "bg": "#eef1f6",
    "card": "#ffffff",
    "border": "#d8dee9",
    "text": "#1f2937",
    "muted": "#6b7280",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "success": "#059669",
    "success_bg": "#ecfdf5",
    "danger": "#dc2626",
    "danger_bg": "#fef2f2",
    "warning": "#d97706",
    "warning_bg": "#fffbeb",
    "input_bg": "#ffffff",
}

FONT_UI = ("Microsoft YaHei UI", 10)
FONT_TITLE = ("Microsoft YaHei UI", 16, "bold")
FONT_SUBTITLE = ("Microsoft YaHei UI", 12, "bold")
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_NAV = ("Microsoft YaHei UI", 11)


def apply_theme(root):
    """为窗口应用全局 ttk 主题"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLORS["bg"])
    style.configure(".", font=FONT_UI, background=COLORS["bg"], foreground=COLORS["text"])

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["card"])
    style.configure("Sidebar.TFrame", background=COLORS["sidebar"])

    style.configure(
        "TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=FONT_UI,
    )
    style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=FONT_UI)
    style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONT_TITLE)
    style.configure("CardTitle.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=FONT_SUBTITLE)
    style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=FONT_SMALL)
    style.configure("CardMuted.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=FONT_SMALL)
    style.configure("Success.TLabel", background=COLORS["card"], foreground=COLORS["success"], font=FONT_SUBTITLE)
    style.configure("Danger.TLabel", background=COLORS["card"], foreground=COLORS["danger"], font=FONT_SUBTITLE)
    style.configure("Warning.TLabel", background=COLORS["card"], foreground=COLORS["warning"], font=FONT_SUBTITLE)

    style.configure(
        "TLabelframe",
        background=COLORS["card"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=COLORS["card"],
        foreground=COLORS["muted"],
        font=FONT_SMALL,
    )

    style.configure(
        "TButton",
        font=FONT_UI,
        padding=(14, 8),
        background="#e5e7eb",
        foreground=COLORS["text"],
        borderwidth=0,
        focusthickness=0,
    )
    style.map(
        "TButton",
        background=[("active", "#d1d5db"), ("disabled", "#f3f4f6")],
        foreground=[("disabled", "#9ca3af")],
    )

    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground="#ffffff",
        padding=(16, 8),
        font=("Microsoft YaHei UI", 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS["accent_hover"]), ("disabled", "#93c5fd")],
        foreground=[("disabled", "#ffffff")],
    )

    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground="#ffffff",
        padding=(16, 8),
        font=("Microsoft YaHei UI", 10, "bold"),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#b91c1c"), ("disabled", "#fca5a5")],
        foreground=[("disabled", "#ffffff")],
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS["input_bg"],
        background=COLORS["input_bg"],
        foreground=COLORS["text"],
        padding=6,
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
    )
    style.map("TEntry", bordercolor=[("focus", COLORS["accent"])])

    style.configure(
        "TCombobox",
        fieldbackground=COLORS["input_bg"],
        background=COLORS["input_bg"],
        foreground=COLORS["text"],
        padding=5,
        arrowsize=14,
    )

    style.configure(
        "TCheckbutton",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=FONT_UI,
    )

    style.configure(
        "TNotebook",
        background=COLORS["bg"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        padding=(16, 8),
        font=FONT_UI,
        background="#dde3ee",
        foreground=COLORS["text"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["card"])],
        foreground=[("selected", COLORS["accent"])],
    )

    style.configure(
        "Treeview",
        background=COLORS["card"],
        fieldbackground=COLORS["card"],
        foreground=COLORS["text"],
        rowheight=32,
        font=FONT_UI,
        bordercolor=COLORS["border"],
    )
    style.configure(
        "Treeview.Heading",
        background="#f3f4f6",
        foreground=COLORS["muted"],
        font=("Microsoft YaHei UI", 9, "bold"),
        padding=8,
        relief="flat",
    )
    style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", COLORS["text"])])

    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#e5e7eb",
        background=COLORS["accent"],
        bordercolor="#e5e7eb",
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent"],
        thickness=8,
    )


class NavButton(tk.Frame):
    """侧栏导航按钮"""

    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, bg=COLORS["sidebar"], **kwargs)
        self.command = command
        self.active = False
        self.enabled = True

        self.indicator = tk.Frame(self, width=3, bg=COLORS["sidebar"])
        self.indicator.pack(side=tk.LEFT, fill=tk.Y)

        self.label = tk.Label(
            self,
            text=text,
            font=FONT_NAV,
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_text"],
            anchor="w",
            padx=18,
            pady=12,
            cursor="hand2",
        )
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        for widget in (self, self.label, self.indicator):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, _event=None):
        if not self.enabled or self.active:
            return
        self.configure(bg=COLORS["sidebar_hover"])
        self.label.configure(bg=COLORS["sidebar_hover"])
        self.indicator.configure(bg=COLORS["sidebar_hover"])

    def _on_leave(self, _event=None):
        if not self.enabled:
            return
        if self.active:
            self._paint_active()
        else:
            self._paint_idle()

    def _on_click(self, _event=None):
        if self.enabled:
            self.command()

    def set_active(self, active):
        self.active = active
        if not self.enabled:
            self._paint_disabled()
        elif active:
            self._paint_active()
        else:
            self._paint_idle()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.label.configure(cursor="hand2" if enabled else "arrow")
        if not enabled:
            self._paint_disabled()
        elif self.active:
            self._paint_active()
        else:
            self._paint_idle()

    def _paint_idle(self):
        self.configure(bg=COLORS["sidebar"])
        self.label.configure(bg=COLORS["sidebar"], fg=COLORS["sidebar_text"])
        self.indicator.configure(bg=COLORS["sidebar"])

    def _paint_active(self):
        self.configure(bg=COLORS["sidebar_hover"])
        self.label.configure(bg=COLORS["sidebar_hover"], fg="#ffffff")
        self.indicator.configure(bg=COLORS["sidebar_active"])

    def _paint_disabled(self):
        self.configure(bg=COLORS["sidebar"])
        self.label.configure(bg=COLORS["sidebar"], fg="#4b5563")
        self.indicator.configure(bg=COLORS["sidebar"])


def create_card(parent, padding=20):
    """创建白色卡片容器"""
    outer = tk.Frame(parent, bg=COLORS["bg"])
    card = tk.Frame(
        outer,
        bg=COLORS["card"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
        padx=padding,
        pady=padding,
    )
    card.pack(fill=tk.BOTH, expand=True)
    return outer, card
