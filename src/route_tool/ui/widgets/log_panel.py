"""操作日志面板。

给 IT 远程排查用：同事报"不好使"时让他截图发过来，能看到完整执行过程。
"""
from __future__ import annotations

import datetime

import customtkinter as ctk


# 不同级别的颜色（深色/浅色主题都用同一组，CustomTkinter 会自适应前景色）
_LEVEL_PREFIX = {
    "info": "",
    "success": "✓ ",
    "warning": "⚠ ",
    "error": "✗ ",
    "debug": "  ",
}


class LogPanel(ctk.CTkFrame):
    """操作日志区域。"""

    MAX_LINES = 200  # 防止无限增长导致卡顿

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._title = ctk.CTkLabel(self, text="📋 操作日志", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=20, pady=(15, 5))

        self._textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self._textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    def append(self, message: str, level: str = "info") -> None:
        """追加一条日志。level: info/success/warning/error/debug。"""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = _LEVEL_PREFIX.get(level, "")
        line = f"[{ts}] {prefix}{message}\n"

        self._textbox.configure(state="normal")
        self._textbox.insert("end", line)
        # 超过上限时删除最旧的
        line_count = int(self._textbox.index("end-1c").split(".")[0])
        if line_count > self.MAX_LINES:
            self._textbox.delete("1.0", f"{line_count - self.MAX_LINES}.0")
        self._textbox.see("end")
        self._textbox.configure(state="disabled")
