import random
import bisect
import pygame
from const import *

class Background:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.scroll_speed = SCROLL_SPEED
        self.sky_surface = self._create_sky()
        self.river_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        self.clouds: list[list] = []
        self.rivers: list[dict] = []
        self.mountains: list[list] = []
        self._generate_rivers()
        for _ in range(CLOUD_INITIAL_COUNT):
            self._spawn_cloud()
            if self.clouds:
                self.clouds[-1][0] = random.uniform(-CLOUD_SPAWN_X_OFFSET, width + CLOUD_SPAWN_X_OFFSET)
                self.clouds[-1][1] = random.uniform(0, height)
        for _ in range(MOUNTAIN_INITIAL_COUNT):
            self._spawn_mountain()
            if self.mountains:
                self.mountains[-1][1] = random.uniform(0, height)

    def _create_sky(self) -> pygame.Surface:
        surf = pygame.Surface((self.width, self.height))
        tr, tg, tb = SKY_TOP_RGB
        br, bg_c, bb = SKY_BOTTOM_RGB
        for y in range(self.height):
            t = y / self.height
            r = int(tr + (br - tr) * t)
            g = int(tg + (bg_c - tg) * t)
            b = int(tb + (bb - tb) * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (self.width, y))
        return surf

    def _spawn_cloud(self) -> None:
        g = random.randint(CLOUD_GRAY_MIN, CLOUD_GRAY_MAX)
        alpha = random.randint(CLOUD_ALPHA_MIN, CLOUD_ALPHA_MAX)
        color = (g, g, g, alpha)
        blocks: list[tuple[int, int, int, int]] = []
        cx = random.randint(-CLOUD_SPAWN_X_OFFSET, self.width + CLOUD_SPAWN_X_OFFSET)
        cy = -random.randint(CLOUD_Y_ABOVE_MIN, CLOUD_Y_ABOVE_MAX)
        n = random.randint(CLOUD_BLOCK_COUNT_MIN, CLOUD_BLOCK_COUNT_MAX)
        min_bx = min_by = 99999
        max_bx = max_by = -99999
        for _ in range(n):
            bw = random.randint(CLOUD_BLOCK_W_MIN, CLOUD_BLOCK_W_MAX)
            bh = random.randint(CLOUD_BLOCK_H_MIN, CLOUD_BLOCK_H_MAX)
            bx = random.randint(CLOUD_BLOCK_X_MIN, CLOUD_BLOCK_X_MAX)
            by = random.randint(CLOUD_BLOCK_Y_MIN, CLOUD_BLOCK_Y_MAX)
            blocks.append((bx, by, bw, bh))
            min_bx = min(min_bx, bx)
            min_by = min(min_by, by)
            max_bx = max(max_bx, bx + bw)
            max_by = max(max_by, by + bh)
        w = max_bx - min_bx
        h = max_by - min_by
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for bx, by, bw, bh in blocks:
            pygame.draw.rect(surf, color, (bx - min_bx, by - min_by, bw, bh))
        speed = random.uniform(CLOUD_SPEED_MIN, CLOUD_SPEED_MAX)
        self.clouds.append([cx + min_bx, cy + min_by, speed, surf])

    def _generate_river(self, x_pos: float | None = None, start_offset: float = 0.0) -> dict:
        cx = x_pos if x_pos is not None else random.uniform(RIVER_X_CLAMP_MIN, self.width - RIVER_X_CLAMP_MIN)
        cy = RIVER_START_Y
        pts_x: list[float] = []
        pts_y: list[float] = []
        for _ in range(RIVER_NUM_POINTS):
            pts_x.append(cx)
            pts_y.append(cy)
            cx += random.uniform(RIVER_X_STEP_MIN, RIVER_X_STEP_MAX)
            cx = max(RIVER_X_CLAMP_MIN, min(self.width - RIVER_X_CLAMP_MIN, cx))
            cy += random.uniform(RIVER_Y_STEP_MIN, RIVER_Y_STEP_MAX)
        gray = random.randint(RIVER_GRAY_MIN, RIVER_GRAY_MAX)
        life = random.randint(RIVER_LIFE_MIN, RIVER_LIFE_MAX)
        return {
            'pts_x': pts_x,
            'pts_y': pts_y,
            'num_points': RIVER_NUM_POINTS,
            'offset': start_offset,
            'color': (gray, gray, gray),
            'width': random.uniform(RIVER_WIDTH_MIN, RIVER_WIDTH_MAX),
            'alpha': random.randint(RIVER_ALPHA_MIN, RIVER_ALPHA_MAX),
            'life': life,
            'max_life': life,
        }

    def _generate_rivers(self) -> None:
        count = random.randint(RIVER_COUNT_MIN, RIVER_COUNT_MAX)
        spacing = self.width / (count + 1)
        for i in range(count):
            x = spacing * (i + 1) + random.uniform(-RIVER_X_OFFSET, RIVER_X_OFFSET)
            self.rivers.append(self._generate_river(x_pos=x))

    def _spawn_new_river(self) -> None:
        x = random.uniform(RIVER_X_CLAMP_MIN, self.width - RIVER_X_CLAMP_MIN)
        offset = -RIVER_START_Y - RIVER_SPAWN_Y_ABOVE
        self.rivers.append(self._generate_river(x_pos=x))

    def _spawn_mountain(self) -> None:
        x = random.randint(MOUNTAIN_X_MARGIN, self.width - MOUNTAIN_X_MARGIN)
        my = -random.randint(MOUNTAIN_Y_ABOVE_MIN, MOUNTAIN_Y_ABOVE_MAX)
        for river in self.rivers:
            ry = my - river['offset']
            idx = max(0, bisect.bisect_left(river['pts_y'], ry) - 1)
            for i in range(max(0, idx - MOUNTAIN_COLLISION_IDX_RANGE), min(len(river['pts_x']), idx + MOUNTAIN_COLLISION_IDX_RANGE + 1)):
                if abs(river['pts_x'][i] - x) < MOUNTAIN_COLLISION_DIST:
                    return
        scale = random.uniform(MOUNTAIN_SCALE_MIN, MOUNTAIN_SCALE_MAX)
        w = int(random.randint(MOUNTAIN_SIZE_W_MIN, MOUNTAIN_SIZE_W_MAX) * scale)
        h = int(random.randint(MOUNTAIN_SIZE_H_MIN, MOUNTAIN_SIZE_H_MAX) * scale)
        if random.random() < MOUNTAIN_BIG_CHANCE:
            w = int(w * random.uniform(MOUNTAIN_BIG_SCALE_W_MIN, MOUNTAIN_BIG_SCALE_W_MAX))
            h = int(h * random.uniform(MOUNTAIN_BIG_SCALE_H_MIN, MOUNTAIN_BIG_SCALE_H_MAX))
        c = random.randint(MOUNTAIN_COLOR_MIN, MOUNTAIN_COLOR_MAX)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        half = w / 2
        aoff = random.uniform(MOUNTAIN_ALPHA_OFFSET_MIN, MOUNTAIN_ALPHA_OFFSET_MAX)
        for px in range(w):
            dist = abs(px - half) / half
            hh = int((1 - dist) * h)
            if hh > 0:
                a = int((px / w) * MOUNTAIN_MAX_ALPHA * aoff)
                for py in range(h - hh, h):
                    surf.set_at((px, py), (c, c, c, a))
        self.mountains.append([x, -random.randint(MOUNTAIN_Y_ABOVE_MIN, MOUNTAIN_Y_ABOVE_MAX), surf])

    def _river_pts(self, river: dict) -> list[tuple[int, int]]:
        pts_x = river['pts_x']
        pts_y = river['pts_y']
        offset = river['offset']
        screen_pts: list[tuple[int, int]] = []
        margin = BG_VISIBLE_MARGIN
        step = RIVER_DRAW_STEP
        for sy in range(-margin, self.height + margin + 1, step):
            ry = sy - offset
            idx = bisect.bisect_left(pts_y, ry)
            idx = max(1, min(idx, len(pts_x) - 1))
            y0 = pts_y[idx - 1]
            y1 = pts_y[idx]
            if y1 > y0:
                f = (ry - y0) / (y1 - y0)
                x = pts_x[idx - 1] + (pts_x[idx] - pts_x[idx - 1]) * f
            else:
                x = pts_x[idx - 1]
            screen_pts.append((int(x), int(sy)))
        return screen_pts

    def update(self) -> None:
        margin = BG_REMOVE_MARGIN
        for cloud in self.clouds[:]:
            cloud[1] += cloud[2]
            if cloud[1] > self.height + margin:
                self.clouds.remove(cloud)
        if random.random() < CLOUD_SPAWN_CHANCE:
            self._spawn_cloud()
        for river in self.rivers[:]:
            river['offset'] += self.scroll_speed
            river['life'] -= 1
            if river['life'] <= 0 and len(self.rivers) > RIVER_COUNT_MIN:
                self.rivers.remove(river)
        if len(self.rivers) < RIVER_COUNT_MAX and random.random() < RIVER_SPAWN_CHANCE:
            self._spawn_new_river()
        for m in self.mountains[:]:
            m[1] += self.scroll_speed
            if m[1] > self.height + margin:
                self.mountains.remove(m)
        if random.random() < MOUNTAIN_SPAWN_CHANCE:
            self._spawn_mountain()

    def draw(self, screen_surf: pygame.Surface) -> None:
        screen_surf.blit(self.sky_surface, (0, 0))
        for mx, my, surf in self.mountains:
            screen_surf.blit(surf, (mx - surf.get_width() // 2, int(my)))
        self.river_surf.fill((0, 0, 0, 0))
        for river in self.rivers:
            pts = self._river_pts(river)
            if len(pts) > 1:
                base_alpha = river['alpha']
                elapsed = river['max_life'] - river['life']
                if elapsed < RIVER_FADE_IN_DURATION:
                    base_alpha = int(base_alpha * elapsed / RIVER_FADE_IN_DURATION)
                if river['life'] < RIVER_FADE_DURATION:
                    base_alpha = int(base_alpha * river['life'] / RIVER_FADE_DURATION)
                base_alpha = max(0, min(255, base_alpha))
                pygame.draw.lines(
                    self.river_surf,
                    (river['color'][0], river['color'][1], river['color'][2], base_alpha),
                    False, pts, max(1, int(river['width']))
                )
        screen_surf.blit(self.river_surf, (0, 0))
        for cx, cy, _, surf in self.clouds:
            screen_surf.blit(surf, (int(cx), int(cy)))
