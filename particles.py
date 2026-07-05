import random
import math
import pygame
from typing import Any, Callable


def _resolve(val: Any, t: float) -> Any:
    if callable(val):
        return val(t)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        a, b = val
        if isinstance(a, (tuple, list)):
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))
        return a + (b - a) * t
    return val


def _rand(val: Any) -> Any:
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if isinstance(val[0], (int, float)):
            return random.uniform(val[0], val[1])
    return val


class Particle:
    def __init__(self, **kwargs: Any) -> None:
        self.age = 0
        self.alive = True
        self.lifetime = max(1, int(_rand(kwargs.get('lifetime', 60))))
        self.x = _rand(kwargs.get('x', 0))
        self.y = _rand(kwargs.get('y', 0))
        self.vx = _rand(kwargs.get('vx', 0))
        self.vy = _rand(kwargs.get('vy', 0))
        self.ax = _rand(kwargs.get('ax', 0))
        self.ay = _rand(kwargs.get('ay', 0))
        self._size = kwargs.get('size', 3)
        self._color = kwargs.get('color', (255, 255, 255))
        self._alpha = kwargs.get('alpha', 255)
        self._angle = 0.0
        self._angular_vel = kwargs.get('angular_vel', 0)
        self.shape = kwargs.get('shape', 'circle')
        self._surface = kwargs.get('surface', None)
        jitter = kwargs.get('brightness_jitter', 0)
        self._brightness = 1.0 + random.uniform(-jitter, jitter) if jitter > 0 else 1.0
        self.cached_size = 0.0
        self.cached_color = (255, 255, 255)
        self.cached_alpha = 255

    @property
    def t(self) -> float:
        return min(1.0, self.age / self.lifetime) if self.lifetime > 0 else 1.0

    def update(self) -> None:
        if not self.alive:
            return
        self.age += 1
        if self.age >= self.lifetime:
            self.alive = False
            return
        t = self.t
        self.vx += self.ax
        self.vy += self.ay
        self.x += self.vx
        self.y += self.vy
        self._angle += _resolve(self._angular_vel, t)
        self.cached_size = max(0.0, float(_resolve(self._size, t)))
        raw_color = _resolve(self._color, t)
        if self._brightness != 1.0:
            self.cached_color = tuple(max(0, min(255, int(c * self._brightness))) for c in raw_color)
        else:
            self.cached_color = raw_color
        self.cached_alpha = max(0, min(255, int(_resolve(self._alpha, t))))

    @property
    def expired(self) -> bool:
        return not self.alive

    def draw(self, surf: pygame.Surface, offset_x: float = 0, offset_y: float = 0) -> None:
        if not self.alive:
            return
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        size = self.cached_size
        color = self.cached_color
        alpha = self.cached_alpha
        angle = self._angle
        if alpha <= 0 or size <= 0:
            return
        if self.shape == 'circle':
            r = max(1, int(size))
            if alpha < 255 or angle != 0:
                d = r * 2
                tmp = pygame.Surface((d, d), pygame.SRCALPHA)
                pygame.draw.circle(tmp, (*color, alpha), (r, r), r)
                if angle != 0:
                    tmp = pygame.transform.rotate(tmp, angle)
                surf.blit(tmp, (px - tmp.get_width() // 2, py - tmp.get_height() // 2))
            else:
                pygame.draw.circle(surf, color, (px, py), r)
        elif self.shape == 'rect':
            w = max(1, int(size))
            h = max(1, int(size))
            if alpha < 255 or angle != 0:
                tmp = pygame.Surface((w, h), pygame.SRCALPHA)
                tmp.fill((*color, alpha))
                if angle != 0:
                    tmp = pygame.transform.rotate(tmp, angle)
                surf.blit(tmp, (px - tmp.get_width() // 2, py - tmp.get_height() // 2))
            else:
                r = pygame.Rect(px - w // 2, py - h // 2, w, h)
                pygame.draw.rect(surf, color, r)
        elif self.shape == 'surface' and self._surface is not None:
            s = self._surface
            if alpha < 255:
                s = s.copy()
                s.set_alpha(alpha)
            if angle != 0:
                s = pygame.transform.rotate(s, angle)
            surf.blit(s, (px - s.get_width() // 2, py - s.get_height() // 2))
        elif self.shape == 'triangle':
            h = max(1, int(size * 1.5))
            hw = max(1, int(size))
            pts = [(0, -h // 2), (-hw // 2, h // 2), (hw // 2, h // 2)]
            if angle != 0:
                rad = math.radians(angle)
                c, s = math.cos(rad), math.sin(rad)
                pts = [(int(p[0] * c - p[1] * s), int(p[0] * s + p[1] * c)) for p in pts]
            if alpha < 255:
                d = max(h, hw)
                tmp = pygame.Surface((d * 2, d * 2), pygame.SRCALPHA)
                shifted = [(p[0] + d, p[1] + d) for p in pts]
                pygame.draw.polygon(tmp, (*color, alpha), shifted)
                surf.blit(tmp, (px - d, py - d))
            else:
                shifted = [(p[0] + px, p[1] + py) for p in pts]
                pygame.draw.polygon(surf, color, shifted)
        elif self.shape == 'diamond':
            hw = max(1, int(size))
            hh = max(1, int(size))
            pts = [(0, -hh), (-hw, 0), (0, hh), (hw, 0)]
            if angle != 0:
                rad = math.radians(angle)
                c, s = math.cos(rad), math.sin(rad)
                pts = [(int(p[0] * c - p[1] * s), int(p[0] * s + p[1] * c)) for p in pts]
            if alpha < 255:
                d = max(hw, hh) * 2
                tmp = pygame.Surface((d, d), pygame.SRCALPHA)
                shifted = [(p[0] + d // 2, p[1] + d // 2) for p in pts]
                pygame.draw.polygon(tmp, (*color, alpha), shifted)
                surf.blit(tmp, (px - d // 2, py - d // 2))
            else:
                shifted = [(p[0] + px, p[1] + py) for p in pts]
                pygame.draw.polygon(surf, color, shifted)


class ParticleGroup:
    def __init__(self, **kwargs: Any) -> None:
        self.particles: list[Particle] = []
        self.subgroups: list[ParticleGroup] = []
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.spawn_width = kwargs.get('spawn_width', 0)
        self.spawn_height = kwargs.get('spawn_height', 0)
        self.emission_rate = kwargs.get('emission_rate', 0)
        self.max_particles = kwargs.get('max_particles', 0)
        self._emit_counter = 0.0
        self.particle_kwargs: dict[str, Any] = dict(kwargs.get('particle_kwargs', {}))
        if 'particle_kwargs' in kwargs:
            self.particle_kwargs.update(kwargs['particle_kwargs'])
        if 'brightness_jitter' in kwargs:
            self.particle_kwargs.setdefault('brightness_jitter', kwargs['brightness_jitter'])
        self.random_ranges: dict[str, tuple[float, float]] = {}
        for key in ('vx', 'vy', 'ax', 'ay', 'lifetime'):
            rng = kwargs.get(f'{key}_range')
            if rng is not None and isinstance(rng, (tuple, list)) and len(rng) == 2:
                self.random_ranges[key] = (rng[0], rng[1])
        self.gravity = kwargs.get('gravity', 0)
        self.wind = kwargs.get('wind', 0)
        self.damping = kwargs.get('damping', 1.0)
        self.active = kwargs.get('active', True)
        self.one_shot = kwargs.get('one_shot', False)
        self._has_emitted = False

    def emit(self, count: int = 1, **overrides: Any) -> None:
        for _ in range(count):
            kw = dict(self.particle_kwargs)
            for key, (lo, hi) in self.random_ranges.items():
                kw[key] = random.uniform(lo, hi)
            kw.update(overrides)
            if self.spawn_width > 0 or self.spawn_height > 0:
                ox = kw.get('x', 0) + random.uniform(-self.spawn_width / 2, self.spawn_width / 2)
                oy = kw.get('y', 0) + random.uniform(-self.spawn_height / 2, self.spawn_height / 2)
                kw['x'] = ox
                kw['y'] = oy
            p = Particle(**kw)
            p.ay += self.gravity
            p.ax += self.wind
            self.particles.append(p)
        if count > 0:
            self._has_emitted = True

    def update(self) -> None:
        if not self.active:
            return
        if self.emission_rate > 0:
            if not self.one_shot or not self._has_emitted:
                self._emit_counter += self.emission_rate
                emit_count = int(self._emit_counter)
                if emit_count > 0:
                    self._emit_counter -= emit_count
                    if self.max_particles > 0:
                        emit_count = min(emit_count, self.max_particles - len(self.particles))
                    if emit_count > 0:
                        self.emit(emit_count)
        for p in self.particles[:]:
            p.update()
            if not p.alive:
                self.particles.remove(p)

        if self.damping != 1.0:
            for p in self.particles:
                p.vx *= self.damping
                p.vy *= self.damping
        for sg in self.subgroups[:]:
            sg.update()

    def draw(self, surf: pygame.Surface, offset_x: float = 0, offset_y: float = 0) -> None:
        ox = self.x + offset_x
        oy = self.y + offset_y
        for p in self.particles:
            p.draw(surf, ox, oy)
        for sg in self.subgroups:
            sg.draw(surf, ox, oy)

    def clear(self) -> None:
        self.particles.clear()

    def kill(self) -> None:
        self.active = False
        self.clear()

    @property
    def is_dead(self) -> bool:
        return self.one_shot and self._has_emitted and len(self.particles) == 0

    @property
    def particle_count(self) -> int:
        return len(self.particles)


class EnemyExplosion(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=10, spawn_height=10,
            gravity=0.05, damping=0.97,
            particle_kwargs={
                'lifetime': (20, 40),
                'size': (4, 0),
                'color': ((255, 200, 50), (80, 20, 0)),
                'alpha': (255, 0),
                'shape': 'circle',
                'brightness_jitter': 0.3,
            },
            vx_range=(-3, 3),
            vy_range=(-3, 3),
        )
        self.emit(random.randint(15, 25))


class MissileTrail(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=False,
            emission_rate=0,
            max_particles=30,
            gravity=0.02,
            particle_kwargs={
                'lifetime': (15, 30),
                'size': (3, 0.5),
                'color': ((180, 180, 180), (80, 80, 80)),
                'alpha': (200, 0),
                'shape': 'circle',
                'brightness_jitter': 0.3,
            },
        )


class RocketTrail(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=False,
            emission_rate=0,
            max_particles=30,
            gravity=0.02,
            particle_kwargs={
                'lifetime': (15, 30),
                'size': (3, 0.5),
                'color': ((255, 200, 50), (100, 30, 0)),
                'alpha': (200, 0),
                'shape': 'circle',
                'brightness_jitter': 0.3,
            },
        )


class MissileHit(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=8, spawn_height=8,
            gravity=0.08, damping=0.96,
            particle_kwargs={
                'lifetime': (15, 25),
                'size': (3, 0),
                'color': ((255, 255, 255), (135, 216, 255)),
                'alpha': (255, 0),
                'shape': 'circle',
                'brightness_jitter': 0.3,
            },
            vx_range=(-4, 4),
            vy_range=(-4, 4),
        )
        self.emit(random.randint(10, 15))


class RocketHit(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=8, spawn_height=8,
            gravity=0.08, damping=0.96,
            particle_kwargs={
                'lifetime': (15, 25),
                'size': (3, 0),
                'color': ((255, 200, 80), (80, 20, 0)),
                'alpha': (255, 0),
                'shape': 'circle',
                'brightness_jitter': 0.3,
            },
            vx_range=(-4, 4),
            vy_range=(-4, 4),
        )
        self.emit(random.randint(20, 30))


class PlayerExplosion(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=30, spawn_height=30,
            gravity=0.05, damping=0.97,
            brightness_jitter=0.3,
        )
        self.emit(
            random.randint(30, 40),
            lifetime=(30, 60),
            size=(8, 0),
            color=((255, 255, 200), (255, 100, 0)),
            alpha=(255, 0),
            shape='circle',
            vx=(-6, 6), vy=(-6, 6),
        )
        self.emit(
            random.randint(15, 25),
            lifetime=(40, 80),
            size=(5, 1),
            color=((200, 200, 200), (50, 50, 50)),
            alpha=(150, 0),
            shape='circle',
            vx=(-4, 4), vy=(-4, 4),
        )
        self.emit(
            random.randint(10, 15),
            lifetime=(10, 25),
            size=(2, 0),
            color=((255, 255, 255), (255, 200, 0)),
            alpha=(255, 0),
            shape='rect',
            vx=(-10, 10), vy=(-10, 10),
        )


class NukeExplosion(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=30, spawn_height=30,
            brightness_jitter=0.3,
        )
        self.emit(
            1,
            lifetime=15,
            size=(350, 0),
            color=(255, 255, 255),
            alpha=(200, 0),
            shape='circle',
            vx=0, vy=0,
        )
        self.emit(
            120,
            lifetime=(30, 90),
            size=(10, 0),
            color=((255, 255, 200), (200, 50, 0)),
            alpha=(255, 0),
            shape='circle',
            vx=(-8, 8), vy=(-8, 8),
        )
        self.emit(
            80,
            lifetime=(30, 90),
            size=(5, 1),
            color=((255, 200, 100), (100, 30, 0)),
            alpha=(200, 0),
            shape='circle',
            vx=(-12, 12), vy=(-12, 12),
        )
        self.emit(
            100,
            lifetime=(60, 120),
            size=(15, 3),
            color=((150, 150, 150), (30, 30, 30)),
            alpha=(180, 0),
            shape='circle',
            vx=(-3, 3), vy=(-4, -2),
        )
        self.emit(
            60,
            lifetime=(50, 100),
            size=(4, 1),
            color=((200, 200, 150), (80, 80, 50)),
            alpha=(255, 0),
            shape='rect',
            vx=(-15, 15), vy=(-15, 15),
        )
        self.emit(
            40,
            lifetime=(80, 150),
            size=(2, 0),
            color=((180, 180, 180), (100, 100, 100)),
            alpha=(100, 0),
            shape='circle',
            vx=(-3, 3), vy=(0.5, 2),
        )


class BulletHit(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=4, spawn_height=4,
            brightness_jitter=0.3,
            particle_kwargs={
                'lifetime': (8, 15),
                'size': (3, 0),
                'color': ((255, 200, 50), (180, 120, 20)),
                'alpha': (255, 0),
                'shape': 'circle',
            },
            vx_range=(-2, 2),
            vy_range=(-2, 2),
        )
        self.emit(random.randint(4, 7))


class LazerHit(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=4, spawn_height=4,
            brightness_jitter=0.3,
            particle_kwargs={
                'lifetime': (8, 15),
                'size': (3, 0),
                'color': ((100, 200, 255), (30, 100, 200)),
                'alpha': (255, 0),
                'shape': 'circle',
            },
            vx_range=(-2, 2),
            vy_range=(-2, 2),
        )
        self.emit(random.randint(4, 7))


class AutocannonHit(ParticleGroup):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            one_shot=True,
            spawn_width=4, spawn_height=4,
            brightness_jitter=0.3,
            particle_kwargs={
                'lifetime': (8, 15),
                'size': (5, 0),
                'color': ((255, 150, 150), (200, 80, 80)),
                'alpha': (255, 0),
                'shape': 'circle',
            },
            vx_range=(-3, 3),
            vy_range=(-3, 3),
        )
        self.emit(random.randint(4, 7))
