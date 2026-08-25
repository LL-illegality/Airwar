from __future__ import annotations

import pygame


class DisplayManager:
    """管理逻辑表面与实际窗口之间的适配（等比缩放 + 黑边 + 全屏切换）。

    世界坐标与逻辑表面坐标严格一一对应：所有游戏内容绘制到
    ``logic_surface``（固定逻辑分辨率），``present`` 时整体等比缩放输出，
    任意屏幕分辨率下宽高比恒定，多余区域以黑色填充。
    """

    def __init__(self, logic_size: tuple[int, int], fullscreen: bool = True) -> None:
        self.logic_size = logic_size
        self.logic_surface = pygame.Surface(logic_size)
        self.fullscreen = fullscreen
        self.screen: pygame.Surface
        self.fit_rect_ = pygame.Rect(0, 0, logic_size[0], logic_size[1])
        self._apply_mode()

    def _apply_mode(self) -> None:
        """根据当前全屏状态创建窗口并重算等比缩放区域。"""
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            # RESIZABLE：窗口可自由拉伸，画面等比缩放（同时支持放大与缩小）
            self.screen = pygame.display.set_mode(self.logic_size, pygame.RESIZABLE)
        self.fit_rect_ = self.fit_rect()

    def handle_resize(self, size: tuple[int, int]) -> None:
        """窗口尺寸变化（RESIZABLE 模式拖拽）时重算缩放区域。

        需在收到 pygame.VIDEORESIZE 事件后调用（pygame 2.x 中必须先 set_mode）。
        """
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.fit_rect_ = self.fit_rect()

    def fit_rect(self) -> pygame.Rect:
        """计算逻辑表面在窗口中的等比缩放居中区域（黑边之外的区域）。"""
        lw, lh = self.logic_size
        sw, sh = self.screen.get_size()
        scale = min(sw / lw, sh / lh)
        nw = max(1, int(lw * scale))
        nh = max(1, int(lh * scale))
        x = (sw - nw) // 2
        y = (sh - nh) // 2
        return pygame.Rect(x, y, nw, nh)

    def toggle_fullscreen(self) -> None:
        """在独占全屏与固定尺寸窗口模式之间切换。"""
        self.fullscreen = not self.fullscreen
        self._apply_mode()

    def present(self) -> None:
        """将逻辑表面等比缩放后输出到屏幕（黑色黑边填充）。"""
        rect = self.fit_rect_
        scaled = pygame.transform.smoothscale(self.logic_surface, (rect.width, rect.height))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, (rect.x, rect.y))
        pygame.display.flip()

    def screen_to_logic(self, pos: tuple[int, int]) -> tuple[float, float]:
        """屏幕坐标 → 逻辑坐标（为触屏/鼠标交互预留）。"""
        rect = self.fit_rect_
        if rect.width <= 0 or rect.height <= 0:
            return (0.0, 0.0)
        lx = (pos[0] - rect.x) / rect.width * self.logic_size[0]
        ly = (pos[1] - rect.y) / rect.height * self.logic_size[1]
        return (lx, ly)
