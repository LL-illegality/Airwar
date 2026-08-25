from __future__ import annotations

from pathlib import Path

import pygame

_FONTS_DIR = Path(__file__).parent / "fonts"

# 字体名称（去空格小写）→ fonts/ 目录下的文件名
_FONT_FILE_MAP: dict[str, str] = {
    "consola": "consola.ttf",
    "consolas": "consola.ttf",
    "simhei": "msyh.ttc",
    "simsun": "msyh.ttc",
    "microsoftyahei": "msyh.ttc",
    "yahei": "msyh.ttc",
    "microsoftyaheiui": "msyh.ttc",
}


def load_font(name: str, size: int) -> pygame.font.Font:
    """加载字体：优先使用 fonts/ 目录中的字体文件。

    避免依赖 ``pygame.font.SysFont`` —— 该函数在 Windows 上扫描系统字体
    注册表时，遇到非字符串类型的注册表值会抛 ``TypeError``（pygame 2.6.1
    已知问题）。回退顺序：
    1. ``fonts/`` 目录中的字体文件（按名称映射表）
    2. ``SysFont``（若系统字体扫描可用）
    3. pygame 默认字体（保证任何环境下都不崩溃）
    """
    key = name.replace(" ", "").lower()
    file_name = _FONT_FILE_MAP.get(key)
    font_path = _FONTS_DIR / file_name if file_name is not None else None
    if font_path is not None and font_path.is_file():
        return pygame.font.Font(str(font_path), size)
    try:
        return pygame.font.SysFont(name, size)
    except Exception:
        return pygame.font.Font(None, size)
