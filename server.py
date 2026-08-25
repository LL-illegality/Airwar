from __future__ import annotations
import asyncio
import websockets
import os
from typing import Any
from const import *
from data import Vector, Message, Queue
import random
import json 
import socket
import time
import math
from collections import defaultdict

def createInstanceFromClassname(classname: str, kwargs: dict[str, Any] | None = None) -> Any:
    kwargs = kwargs or {}
    cls = globals().get(classname)
    if cls is None:
        raise ValueError(f"Unknown class name: {classname}")
    return cls(**kwargs)

class Point:
    def __init__(self, x: float = 0, y: float = 0) -> None:
        self.x = x
        self.y = y
    
    def getDirection(self, other: "Point") -> Vector:
        return Vector(other.x - self.x, other.y - self.y)

class BoundingBox:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
    
    def getRect(self, x: float, y: float) -> tuple[Point, Point]:
        luPoint = Point(x - (self.width/2), y - (self.height/2))
        rdPoint = Point(x + (self.width/2), y + (self.height/2))
        return (luPoint, rdPoint)

class SpatialGrid:
    cells: dict[tuple[int, int], set[Entity]]

    def __init__(self) -> None:
        self.cells = defaultdict(set)

    def add(self, entity: Entity) -> None:
        bb = entity.boundingBox
        if bb is None:
            return
        left = int((entity.x - bb.width / 2) // CELL_SIZE)
        right = int((entity.x + bb.width / 2) // CELL_SIZE)
        top = int((entity.y - bb.height / 2) // CELL_SIZE)
        bottom = int((entity.y + bb.height / 2) // CELL_SIZE)
        for cx in range(left, right + 1):
            for cy in range(top, bottom + 1):
                self.cells[(cx, cy)].add(entity)

    def get_nearby(self, entity: Entity) -> list[Entity]:
        bb = entity.boundingBox
        if bb is None:
            return []
        candidates: list[Entity] = []
        left = int((entity.x - bb.width / 2) // CELL_SIZE)
        right = int((entity.x + bb.width / 2) // CELL_SIZE)
        top = int((entity.y - bb.height / 2) // CELL_SIZE)
        bottom = int((entity.y + bb.height / 2) // CELL_SIZE)
        seen: set[Entity] = set()
        for cx in range(left, right + 1):
            for cy in range(top, bottom + 1):
                for e in self.cells.get((cx, cy), ()):
                    if e is not entity and e not in seen:
                        seen.add(e)
                        candidates.append(e)
        return candidates

class Entity:
    def __init__(self, x: float = 0, y: float = 0, id: int = -1) -> None:
        self.x = x
        self.y = y
        self.id = id
        self.image: Images | None = None
        self.boundingBox: BoundingBox | None = None
        self.velocity = Vector(0, 0)
        self.acceleration = Vector(0, 0)
        self.rotation = 0.0
        self.maxVelocity: float | None = None
        self.velocityMultiplier = 0.9
        self.race = Race.neutral
        self.isAlive = True
    
    def update(self) -> None:
        self.x += self.velocity.x
        self.y += self.velocity.y
        self.velocity *= self.velocityMultiplier
        self.velocity += self.acceleration
        if self.maxVelocity is not None:
            if self.velocity.x > self.maxVelocity:
                self.velocity.x = self.maxVelocity
            if self.velocity.x < -self.maxVelocity:
                self.velocity.x = -self.maxVelocity
            if self.velocity.y > self.maxVelocity:
                self.velocity.y = self.maxVelocity
            if self.velocity.y < -self.maxVelocity:
                self.velocity.y = -self.maxVelocity
        if (self.velocity.x**2 + self.velocity.y**2) ** 0.5 < 0.01:
            self.velocity = Vector(0, 0)
    
    def faceToTarget(self, target: "Entity", type: str = 'velocity') -> None:
        v0 = Vector(target.x - self.x, target.y - self.y)
        l0 = (v0.x**2 + v0.y**2)**0.5
        lb = (self.velocity.x**2 + self.velocity.y**2)**0.5
        if type == 'acceleration':
            lb = (self.acceleration.x**2 + self.acceleration.y**2)**0.5
        vn = Vector(v0.x * (lb / l0), v0.y * (lb / l0))
        if type == 'velocity':
            self.velocity = vn
        elif type == 'acceleration':
            self.acceleration = vn
    
    def onCollision(self, other: "Entity") -> None:
        ...
    
    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id
    
    def __and__(self, other: "Entity") -> bool:
        # check if two entities are colliding
        if self.boundingBox is None or other.boundingBox is None:
            return False
        rect1 = self.boundingBox.getRect(self.x, self.y)
        rect2 = other.boundingBox.getRect(other.x, other.y)
        lu1, rd1 = rect1
        lu2, rd2 = rect2
        return lu1.x < rd2.x and lu2.x < rd1.x and lu1.y < rd2.y and lu2.y < rd1.y

class Item(Entity):
    cycleMap = {
    ItemTypes.shotgun: ItemTypes.lazer,
    ItemTypes.lazer: ItemTypes.autocannon,
    ItemTypes.autocannon: ItemTypes.shotgun,
    ItemTypes.missile: ItemTypes.rocket,
    ItemTypes.rocket: ItemTypes.missile,
    }
    def __init__(self, item: ItemTypes):
        super().__init__()
        self.item = item
        self.image = itemMap[item]
        self.lifetime = 20 * gametick
        self.boundingBox = BoundingBox(24, 24)
        self.velocity = Vector(random.randint(-5, 5), random.randint(-5, 5))
        self.velocityMultiplier = 1
        self.redirectionDelay = 0
        self.alpha = 255
        self.typeCycleTimer = random.randint(3, 5) * gametick
    
    def update(self) -> None:
        super().update()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.isAlive = False
            return
        self.typeCycleTimer -= 1
        if self.typeCycleTimer <= 0:
            self.typeCycleTimer = random.randint(3, 5) * gametick
            if self.item in self.cycleMap:
                self.item = self.cycleMap[self.item]
                self.image = itemMap[self.item]
        if self.redirectionDelay >= 0:
            if self.x <= 0 or self.x >= SCREENSIZE[0]:
                self.velocity.x *= -1
                self.redirectionDelay = 15
            if self.y <= 0 or self.y >= SCREENSIZE[1]:
                self.velocity.y *= -1
                self.redirectionDelay = 15
        else:
            self.redirectionDelay -= 1
        if self.lifetime < 3 * gametick:
            progress = self.lifetime / (3 * gametick)
            blink_interval = max(2, int(progress * progress * 20))
            self.alpha = 255 if (self.lifetime // blink_interval) % 2 == 0 else 50
    
    def onCollision(self, other: Entity) -> None:
        if other.race == Race.player and isinstance(other, Player) and other.isAlive:
            other.gottenItem.append(self.item)
            self.isAlive = False

class Projectile(Entity):
    def __init__(self, damage: float = 10, lifetime: float = 1000):
        super().__init__()
        self.damage = damage
        self.lifetime = lifetime
        self.shooterRace = Race.neutral
        self.boundingBox = BoundingBox(3, 8)
        self.chooseTarget = False
        self.chooseTargetAngle = 360
        self.velocityMultiplier = 1
        self.target: "Entity | None" = None
    
    def update(self) -> None:
        super().update()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.isAlive = False
        self.rotation = ~self.velocity
    
    def onCollision(self, other: Entity) -> None:
        if other.race != self.shooterRace and other.race != Race.neutral and isinstance(other, Unit):
            if isinstance(other, Player) and other.isEntering:
                return  # 飞入动画期间无敌（加入/复活保护）
            other.health -= self.damage
            self.isAlive = False

class Bullet(Projectile):
    def __init__(self, damage: float = 5, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.bullet1
        self.boundingBox = BoundingBox(3, 8)
        self.velocity = Vector(0, -10)
    
    def onCollision(self, other: Entity) -> None:
        super().onCollision(other)

class Lazer(Projectile):
    def __init__(self, damage: float = 1.5, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.lazer1
        self.boundingBox = BoundingBox(3, 8)
        self.velocity = Vector(0, -15)

class AutocannonShells(Projectile):
    def __init__(self, damage: float = 10, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.autocannon12
        self.boundingBox = BoundingBox(3, 7)
        self.velocity = Vector(0, -20)

class Missile(Projectile):
    def __init__(self, damage: float = 4, handedness: int = 1, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.missile
        self.handedness = handedness
        self.boundingBox = BoundingBox(12, 16)
        self.velocity = Vector(1 * self.handedness, -4)
        self.target: Entity | None = None
        self.lockTargetDelay = 0.5 * gametick
        self.awaitedDelay = 1.5 * gametick
        self.acceleration = Vector(0, -0.5)
    
    def update(self) -> None:
        super().update()
        if self.target is not None:
            if self.target.isAlive == False:
                self.target = None
                return
            self.faceToTarget(self.target, 'acceleration')
            if self.awaitedDelay == 0:
                self.velocity *= 0.6
                self.faceToTarget(self.target, 'velocity')
                self.awaitedDelay = self.lockTargetDelay
            # self.acceleration.x *= (SCREENSIZE[0] - ((self.target.x ** 2 + self.x ** 2) ** 0.5)) / 500
            # self.acceleration.y *= (SCREENSIZE[1] - ((self.target.y ** 2 + self.y ** 2) ** 0.5)) / 500
            else:
                self.awaitedDelay -= 1

class Rocket(Projectile):
    def __init__(self, damage: float = 12, handedness: int = 1, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.rocket
        self.handedness = handedness
        self.boundingBox = BoundingBox(8, 16)
        self.velocity = Vector(1 * self.handedness, -4)
        self.acceleration = Vector(0, -0.7)

class EnergyBall(Projectile):
    def __init__(self, damage: float = 12, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.energyball
        self.chooseTarget = True
        self.boundingBox = BoundingBox(8, 8)
        self.velocity = Vector(0, 4)

class EnergyBallEnhanced(Projectile):
    def __init__(self, damage: float = 24, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.energyball_enhanced
        self.chooseTarget = True
        self.boundingBox = BoundingBox(8, 8)
        self.velocity = Vector(0, 6)

class RocketEnemy(Projectile):
    def __init__(self, damage: float = 12, lifetime: float = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.rocket_enemy
        self.boundingBox = BoundingBox(8, 16)
        self.velocity = Vector(0, 2)
        self.acceleration = Vector(0, 0.7)
        self.chooseTarget = True

class Magabomb(Projectile):
    def __init__(self, damage: float = 10, lifetime: float = 2147483647) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.magabomb
        self.explodePos: tuple[float, float] = (SCREENSIZE[0] / 2, SCREENSIZE[1] / 2)
        self.boundingBox: BoundingBox | None = None
        self.isExploding = False
        self.velocity = Vector(0, 10)
    
    def onCollision(self, other: Entity) -> None:
        pass
    
    def explode(self) -> None:
        self.isAlive = False
        self.isExploding = True
    
    def update(self) -> None:
        super().update()
        distance = ((self.explodePos[0] - self.x) ** 2 + (self.explodePos[1] - self.y) ** 2) ** 0.5
        if distance < 30:
            self.explode()
        else:
            self.faceToTarget(Entity(self.explodePos[0], self.explodePos[1]), 'velocity')

class Weapon:
    def __init__(self, bullet: Projectile, fireRate: float = 10, shooterRace: Race = Race.neutral) -> None:
        self.bullet = bullet
        self.fireRate = fireRate
        self.cooldown = random.randint(0, 100) / 100 * fireRate
        self.level = 1
        self.maxLevel = 10
        self.shooterRace = shooterRace
        self.sound = Sounds.shotgun_shoot
        self.playSound = True
        self.isShooting = False
        self.jamType = WeaponJamType.none
    
    def shoot(self, x: float, y: float, times: int = 1) -> list[Projectile] | None:
        if self.isShooting and self.cooldown <= 0:
            retList: list[Projectile] = []
            for _ in range(times):
                bullet = type(self.bullet)()
                bullet.shooterRace = self.shooterRace
                bullet.x = x
                bullet.y = y
                retList.append(bullet)
            self.cooldown = self.fireRate
            if self.jamType == WeaponJamType.shotgun:
                self.cooldown += random.randint(-10, 10) / 100 * self.fireRate
            if self.jamType == WeaponJamType.lazer:
                if random.randint(0, 100) < 20:
                    retList = []
                    self.playSound = False
            if self.playSound:
                Board.msgQueue.push(Message('server', 'playsound', {"sound": self.sound.value}))
            else:
                self.playSound = True
            return retList
        else:
            return None
    
    def upgrade(self) -> None:
        if self.level < self.maxLevel:
            self.level += 1
    
    def update(self) -> None:
        if self.cooldown > 0:
            self.cooldown -= 1

class WeaponGroup:
    def __init__(self, *weapnons) -> None:
        self.weapons: list[Weapon] = []
        self.isShooting_ = False
        for weapon in weapnons:
            self.weapons.append(weapon)
    
    def addWeapon(self, weapon: Weapon) -> None:
        self.weapons.append(weapon)
    
    def has(self, weaponType: type[Weapon]) -> bool:
        return weaponType in [type(weapon) for weapon in self.weapons]
    
    def removeAll(self, weaponType: type[Weapon]) -> None:
        self.weapons = [weapon for weapon in self.weapons if type(weapon) != weaponType]
    
    def upgrade(self, weaponType: type[Weapon]) -> None:
        for weapon in self.weapons:
            if type(weapon) == weaponType:
                weapon.upgrade()
    
    def getHighestLevel(self) -> int:
        highestLevel = 0
        for weapon in self.weapons:
            if weapon.level > highestLevel:
                highestLevel = weapon.level
        return highestLevel
    
    @property
    def isShooting(self) -> bool:
        return self.isShooting_

    @isShooting.setter
    def isShooting(self, value: bool) -> None:
        self.isShooting_ = value
        for weapon in self.weapons:
            weapon.isShooting = value
    
    def shoot(self, x: float, y: float) -> list[Projectile | None]:
        retList: list[Projectile | None] = []
        for weapon in self.weapons:
            proj = weapon.shoot(x, y)
            if isinstance(proj, list):
                retList.extend(proj)
            else:
                retList.append(proj)
        return retList

    def shoot_with_context(self, x: float, y: float, direction: Vector | None = None, game_context: dict | None = None) -> list[Projectile | None]:
        """带方向与游戏上下文射击（机制武器专用）。普通武器忽略 direction/context，保持原有行为。"""
        retList: list[Projectile | None] = []
        for weapon in self.weapons:
            if isinstance(weapon, EnemyWeapon):
                proj = weapon.shoot(x, y, direction, game_context)
            else:
                proj = weapon.shoot(x, y)
            if isinstance(proj, list):
                retList.extend(proj)
            else:
                retList.append(proj)
        return retList

    def update(self) -> None:
        """更新所有武器冷却（每帧由 Unit.update 驱动）。"""
        for weapon in self.weapons:
            weapon.update()

def _normalize(v: Vector) -> Vector:
    """向量归一化。零向量返回 (0,0)。"""
    length = (v.x**2 + v.y**2) ** 0.5
    if length < 0.0001:
        return Vector(0, 0)
    return Vector(v.x / length, v.y / length)

def _rotate_vector(v: Vector, angle_deg: float) -> Vector:
    """旋转向量（角度制）。与 ~Vector 约定一致：0°=向上、角度增大=视觉顺时针。"""
    rad = math.radians(angle_deg)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return Vector(v.x * cos - v.y * sin, v.x * sin + v.y * cos)

def _angle_from_vector(v: Vector) -> float:
    """向量 → 角度（度，0°=向上、顺时针增大，与 ~Vector 一致）。"""
    return ~v

def _vector_from_angle(angle_deg: float) -> Vector:
    """角度（0°=向上、顺时针增大）→ 单位向量。"""
    return _rotate_vector(Vector(0, -1), angle_deg)

class EnemyWeapon(Weapon):
    """敌人机制武器基类。

    扩展 Weapon.shoot() 接口：支持方向向量与游戏上下文（玩家列表、敌人自身引用）。
    子类继承本类后覆盖 _fire() 实现具体弹幕逻辑，并通过覆盖 __init__ 提供默认参数。
    """
    def __init__(self, bullet: Projectile, fireRate: float, shooterRace: Race = Race.enemy) -> None:
        super().__init__(bullet, fireRate, shooterRace)
        self.sound = Sounds.shotgun_shoot
        # 使用内置 cooldown 控制射击节奏；状态机类（ChargeBurst/RingBlast/PhaseSwitch）设为 False 自行控制
        self.use_cooldown = True

    def shoot(self, x: float, y: float, times: int | Vector | dict | None = 1,
              direction: Vector | dict | None = None,
              game_context: dict | None = None) -> list[Projectile] | None:
        """兼容基类 Weapon.shoot() 的 times 位置参数，并接受旧版 direction/game_context 调用。"""
        if isinstance(times, Vector):
            if isinstance(direction, dict) and game_context is None:
                game_context = direction
            direction = times
            times = 1
        elif isinstance(times, dict) and direction is None and game_context is None:
            game_context = times
            times = 1
        if not self.isShooting:
            return None
        if direction is None:
            return None
        if isinstance(direction, dict):
            if game_context is None:
                game_context = direction
            direction = Vector(0, -1)
        # 每帧更新瞄准角度（不受 cooldown 限制，扫射类武器持续跟踪目标）
        self._update_aim(direction, game_context)
        if self.use_cooldown and self.cooldown > 0:
            return None
        retList = self._fire(x, y, direction, game_context)
        if retList is not None and len(retList) > 0:
            if self.use_cooldown:
                self.cooldown = self.fireRate
            if self.playSound:
                Board.msgQueue.push(Message('server', 'playsound', {"sound": self.sound.value}))
            else:
                self.playSound = True
        return retList

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        """子类实现具体弹幕生成。返回子弹列表，或 None（本次未射击）。"""
        raise NotImplementedError

    def _update_aim(self, direction: Vector, game_context: dict | None) -> None:
        """每帧更新瞄准角度（扫射类武器覆盖实现）。"""
        pass

    def _spawn_bullet(self, x: float, y: float, direction: Vector, speed: float) -> Projectile:
        """创建一颗沿 direction 方向、speed 速度的子弹（无自动追踪）。"""
        bullet = type(self.bullet)()
        bullet.shooterRace = self.shooterRace
        bullet.image = self.bullet.image
        bullet.x = x
        bullet.y = y
        bullet.chooseTarget = False
        bullet.chooseTargetAngle = 360
        bullet.velocity = _normalize(direction) * speed
        if self.shooterRace == Race.enemy:
            if bullet.image == Images.bullet1:
                bullet.image = Images.bullet_enemy
        return bullet

    def _nearest_player(self, game_context: dict | None, x: float, y: float) -> Player | None:
        """从上下文取最近玩家（供预判/瞄准用）。"""
        if not game_context:
            return None
        players = game_context.get('players') or []
        if len(players) == 0:
            return None
        return min(players, key=lambda p: (p.x - x)**2 + (p.y - y)**2)

def _spread_offsets(count: int, fan_angle: float) -> list[float]:
    """扇形内均匀分布的角度偏移列表（相对中心）。"""
    if count <= 1:
        return [0.0]
    return [-fan_angle / 2 + fan_angle * i / (count - 1) for i in range(count)]

class FanSweep(EnemyWeapon):
    """扇形扫射：扇形中心角度持续向玩家方向旋转，每次射击在扇形内均匀撒弹。

    角度在 _update_aim 中每帧更新（不受 cooldown 限制）；首次调用直接对准目标方向，
    保证开局子弹立即朝玩家飞去，避免长时间空射。
    """
    def __init__(self, shooterRace: Race = Race.enemy, fan_angle: float = 60, sweep_speed: float = 2.0,
                 bullets_per_shot: int = 3, fire_rate: int = 8, bullet_speed: float = 8.0) -> None:
        super().__init__(Bullet(), fire_rate, shooterRace)
        self.fan_angle = fan_angle
        self.sweep_speed = sweep_speed
        self.bullets_per_shot = bullets_per_shot
        self.bullet_speed = bullet_speed
        self.current_angle: float = 0.0
        self._aim_initialized = False

    def _update_aim(self, direction: Vector, game_context: dict | None) -> None:
        target_angle = _angle_from_vector(direction)
        if not self._aim_initialized:
            # 首次直接对准目标方向，让扫射立刻有攻击效果
            self.current_angle = target_angle
            self._aim_initialized = True
            return
        diff = (target_angle - self.current_angle + 180) % 360 - 180
        if diff > self.sweep_speed:
            diff = self.sweep_speed
        elif diff < -self.sweep_speed:
            diff = -self.sweep_speed
        self.current_angle = (self.current_angle + diff) % 360

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        retList: list[Projectile] = []
        for offset in _spread_offsets(self.bullets_per_shot, self.fan_angle):
            bullet_dir = _vector_from_angle(self.current_angle + offset)
            retList.append(self._spawn_bullet(x, y, bullet_dir, self.bullet_speed))
        return retList

class FanVolley(EnemyWeapon):
    """扇形齐射：每隔 burst_interval 帧向玩家方向齐射一轮扇形弹。"""
    def __init__(self, shooterRace: Race = Race.enemy, volley_count: int = 5, fan_angle: float = 45,
                 burst_interval: int = 60, bullet_speed: float = 8.0) -> None:
        super().__init__(Bullet(), burst_interval, shooterRace)
        self.volley_count = volley_count
        self.fan_angle = fan_angle
        self.bullet_speed = bullet_speed

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        base_dir = _normalize(direction)
        retList: list[Projectile] = []
        for offset in _spread_offsets(self.volley_count, self.fan_angle):
            bullet_dir = _rotate_vector(base_dir, offset)
            retList.append(self._spawn_bullet(x, y, bullet_dir, self.bullet_speed))
        return retList

class LeadShot(EnemyWeapon):
    """预判射击（精确打击）：求解子弹命中方程，精确预测玩家未来位置后射击。

    玩家运动模型匹配服务器离散帧推进（Entity.update：x += v; v = clamp(v + a)），
    并考虑 maxVelocity 速度饱和（Player.maxVelocity=15，速度达到上限后匀速不再增长）——
    防止玩家持续加速时预判过头。用二分法求解命中时刻 t（f(t)=|P(t)-E|²-(v·t)²=0），
    f 恒正（追击切点/追不上场景）时牛顿法最小化 f'，朝最接近时刻位置射击。
    子弹类型为 AutocannonShells（高伤害），飞行速度远快于普通敌弹。
    prediction_factor 可缩放预判距离（1.0=完全精确，<1 保守、>1 过冲）。
    """
    def __init__(self, shooterRace: Race = Race.enemy, bullet_speed: float = 20.0,
                 prediction_factor: float = 1.0, fire_rate: int = 20) -> None:
        bullet: AutocannonShells = AutocannonShells()
        bullet.image = Images.autocannon56
        super().__init__(bullet, fire_rate, shooterRace)
        self.bullet_speed = bullet_speed
        self.prediction_factor = prediction_factor
        self.sound = Sounds.autocannon_shoot

    def _axis_state(self, v0: float, a: float, vmax: float | None, t: float) -> tuple[float, float, float]:
        """单轴带最大速度饱和的离散运动状态 (位移, 速度, 加速度)。

        帧推进：x += v; v = clamp(v + a)（速度钳制在 ±vmax，Player.maxVelocity=15）。
        - 加速段（|v| 未饱和）：位移 = v0·t + 0.5·a·t(t-1)，速度 = v0 + a·(t-0.5)，加速度 = a
        - 饱和段（速度已达 ±vmax）：匀速位移，速度 = ±vmax，加速度 = 0
        """
        if a == 0:
            return v0 * t, v0, 0.0
        if vmax is None or vmax <= 0:
            # 无速度上限：纯匀加速（Player.maxVelocity 恒 15，正常不会走到）
            return v0 * t + 0.5 * a * t * (t - 1), v0 + a * (t - 0.5), a
        vm = abs(vmax)
        if a > 0:
            if v0 >= vm:
                return vm * t, vm, 0.0
            k_sat = (vm - v0) / a
            if t <= k_sat:
                return v0 * t + 0.5 * a * t * (t - 1), v0 + a * (t - 0.5), a
            accel_disp = v0 * k_sat + 0.5 * a * k_sat * (k_sat - 1)
            return accel_disp + vm * (t - k_sat), vm, 0.0
        else:
            if v0 <= -vm:
                return -vm * t, -vm, 0.0
            k_sat = (v0 + vm) / (-a)
            if t <= k_sat:
                return v0 * t + 0.5 * a * t * (t - 1), v0 + a * (t - 0.5), a
            accel_disp = v0 * k_sat + 0.5 * a * k_sat * (k_sat - 1)
            return accel_disp + (-vm) * (t - k_sat), -vm, 0.0

    def _player_state(self, player: Player, t: float) -> tuple[float, float, float, float, float, float]:
        """玩家 t 帧后状态 (x, y, vx, vy, ax, ay)——含 maxVelocity 饱和。"""
        dx, vx, ax = self._axis_state(player.velocity.x, player.acceleration.x, player.maxVelocity, t)
        dy, vy, ay = self._axis_state(player.velocity.y, player.acceleration.y, player.maxVelocity, t)
        return player.x + dx, player.y + dy, vx, vy, ax, ay

    def _predict_player_pos(self, player: Player, travel_time: float) -> tuple[float, float]:
        """玩家带 maxVelocity 饱和的预测位置（prediction_factor 缩放预判距离）。"""
        t = travel_time * self.prediction_factor
        px, py, _, _, _, _ = self._player_state(player, t)
        return px, py

    def _solve_hit_time(self, x: float, y: float, player: Player) -> float | None:
        """求解命中时刻 t：f(t) = |P(t)-E|² - (bullet_speed·t)² = 0。

        玩家运动模型含 maxVelocity 速度饱和（Player.maxVelocity=15，速度达到上限后
        匀速不再增长）——防止玩家持续加速时预判过头。
        - 若存在 t 使 f(t)<0（子弹追得上）→ 二分法求最早命中根（f 从正转负的第一个零点）
        - 若 f 恒 ≥0（玩家加速逃离的追击切点场景）→ 牛顿法最小化 f（求 f'=0），
          朝"玩家与子弹最接近时刻"的位置射击（最佳努力命中）
        """
        v = self.bullet_speed

        def f(t: float) -> float:
            px, py, _, _, _, _ = self._player_state(player, t)
            dx = px - x
            dy = py - y
            return dx * dx + dy * dy - v * v * t * t

        def fp(t: float) -> float:
            px, py, vx, vy, _, _ = self._player_state(player, t)
            dx = px - x
            dy = py - y
            return 2 * (dx * vx + dy * vy) - 2 * v * v * t

        def fpp(t: float) -> float:
            px, py, vx, vy, ax, ay = self._player_state(player, t)
            dx = px - x
            dy = py - y
            return 2 * (vx * vx + vy * vy + dx * ax + dy * ay) - 2 * v * v

        dx0 = player.x - x
        dy0 = player.y - y
        t0 = ((dx0 * dx0 + dy0 * dy0) ** 0.5) / v
        if t0 < 1e-6:
            return None
        # 倍增找 f(t_hi) < 0 的区间上界（上限 300 帧 = 10 秒，超时放弃精确求解）
        t_hi = max(t0, 1.0)
        f_hi = f(t_hi)
        while f_hi > 0 and t_hi < 300:
            t_hi *= 2
            f_hi = f(t_hi)
        if f_hi <= 0:
            # 二分求根：f 从正转负（或切零）的第一个零点（最早命中时刻）
            lo, hi = 0.0, t_hi
            for _ in range(50):
                mid = (lo + hi) / 2
                if f(mid) > 0:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        # f 恒正（追击切点场景）：牛顿最小化 f（f'=0 → 玩家与子弹最接近时刻）
        t = t0
        for _ in range(12):
            df = fp(t)
            if abs(df) < 1e-6:
                break
            ddf = fpp(t)
            if abs(ddf) < 1e-9:
                break
            t_new = t - df / ddf
            if t_new <= 0:
                t_new = t * 0.5
            if abs(t_new - t) < 0.02:
                t = t_new
                break
            t = t_new
        return max(t, 1e-6)

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        player = self._nearest_player(game_context, x, y)
        if player is None:
            return None
        t = self._solve_hit_time(x, y, player)
        if t is None:
            return None
        predict_x, predict_y = self._predict_player_pos(player, t)
        aim = Vector(predict_x - x, predict_y - y)
        return [self._spawn_bullet(x, y, aim, self.bullet_speed)]

class FanSweepNormal(FanSweep):
    """扇形扫射（普通）：60° 扇形、慢速扫射、3 弹/次。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('fan_angle', 60)
        kwargs.setdefault('sweep_speed', 2.0)
        kwargs.setdefault('bullets_per_shot', 3)
        kwargs.setdefault('fire_rate', 8)
        super().__init__(shooterRace, **kwargs)

class FanSweepHard(FanSweep):
    """扇形扫射（困难）：90° 扇形、快速扫射、5 弹/次。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('fan_angle', 90)
        kwargs.setdefault('sweep_speed', 3.5)
        kwargs.setdefault('bullets_per_shot', 5)
        kwargs.setdefault('fire_rate', 6)
        super().__init__(shooterRace, **kwargs)

class FanVolleyNormal(FanVolley):
    """扇形齐射（普通）：5 弹/45°、1 秒一轮。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('volley_count', 5)
        kwargs.setdefault('fan_angle', 45)
        kwargs.setdefault('burst_interval', 60)
        super().__init__(shooterRace, **kwargs)

class FanVolleyHard(FanVolley):
    """扇形齐射（困难）：9 弹/60°、0.8 秒一轮。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('volley_count', 9)
        kwargs.setdefault('fan_angle', 60)
        kwargs.setdefault('burst_interval', 48)
        super().__init__(shooterRace, **kwargs)

class LeadShotNormal(LeadShot):
    """预判射击（普通）：Autocannon 弹、30 速、0.9 精确预判。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('bullet_speed', 30.0)
        kwargs.setdefault('prediction_factor', 0.9)
        kwargs.setdefault('fire_rate', 20)
        super().__init__(shooterRace, **kwargs)

class LeadShotHard(LeadShot):
    """预判射击（困难）：Autocannon 弹、40 速、0.9精确预判、更高频率。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('bullet_speed', 40.0)
        kwargs.setdefault('prediction_factor', 0.9)
        kwargs.setdefault('fire_rate', 15)
        super().__init__(shooterRace, **kwargs)

class ChargeBurst(EnemyWeapon):
    """蓄力连射：蓄力（停止移动）→ 快速连射 N 发 → 休息，循环。

    状态机由每次 shoot 调用推进（isShooting 时 Board 每帧调用）。
    """
    STATE_CHARGE = 0
    STATE_BURST = 1
    STATE_REST = 2

    def __init__(self, shooterRace: Race = Race.enemy, charge_duration: int = 90, burst_count: int = 8,
                 burst_interval: int = 3, rest_duration: int = 60, bullet_speed: float = 9.0) -> None:
        super().__init__(Bullet(), 1, shooterRace)
        self.use_cooldown = False
        self.charge_duration = charge_duration
        self.burst_count = burst_count
        self.burst_interval = burst_interval
        self.rest_duration = rest_duration
        self.bullet_speed = bullet_speed
        self.state = self.STATE_CHARGE
        self.state_timer = charge_duration
        self.burst_left = 0

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        enemy = game_context.get('enemy') if game_context else None
        if self.state == self.STATE_CHARGE:
            if enemy is not None:
                enemy.stop_movement = True
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = self.STATE_BURST
                self.burst_left = self.burst_count
                self.state_timer = self.burst_interval
            return None
        if self.state == self.STATE_BURST:
            if enemy is not None:
                enemy.stop_movement = False
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state_timer = self.burst_interval
                self.burst_left -= 1
                if self.burst_left < 0:
                    self.state = self.STATE_REST
                    self.state_timer = self.rest_duration
                    return None
                return [self._spawn_bullet(x, y, direction, self.bullet_speed)]
            return None
        # REST
        if enemy is not None:
            enemy.stop_movement = False
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.STATE_CHARGE
            self.state_timer = self.charge_duration
        return None

class PatternLibrary:
    """弹幕图案预设库：返回角度列表（度，0°=向上、顺时针增大）。"""
    @staticmethod
    def ring(count: int, rotation: float = 0.0) -> list[float]:
        return [(360 * i / count + rotation) % 360 for i in range(count)]

    @staticmethod
    def spiral(count: int, turns: float = 2.0, rotation: float = 0.0) -> list[float]:
        return [(360 * turns * i / count + rotation) % 360 for i in range(count)]

    @staticmethod
    def cross(count: int, rotation: float = 0.0) -> list[float]:
        base = max(1, count // 4)
        angles: list[float] = []
        for i in range(4):
            angles.extend([(90 * i + rotation) % 360] * base)
        return angles[:count]

    @staticmethod
    def diamond(count: int, rotation: float = 0.0) -> list[float]:
        base = max(1, count // 4)
        angles: list[float] = []
        for i in range(4):
            angles.extend([(45 + 90 * i + rotation) % 360] * base)
        return angles[:count]

    @staticmethod
    def get(pattern: str, count: int, rotation: float = 0.0, params: dict | None = None) -> list[float]:
        """按图案名生成角度列表，params 可覆盖图案参数（如 spiral 的 turns）。"""
        params = params or {}
        if pattern == 'ring':
            return PatternLibrary.ring(count, rotation)
        if pattern == 'spiral':
            return PatternLibrary.spiral(count, params.get('turns', 2.0), rotation)
        if pattern == 'cross':
            return PatternLibrary.cross(count, rotation)
        if pattern == 'diamond':
            return PatternLibrary.diamond(count, rotation)
        return PatternLibrary.ring(count, rotation)

class FixedPattern(EnemyWeapon):
    """固定弹幕：按预设图案（圆形/螺旋/十字/菱形）发射一圈弹幕。"""
    def __init__(self, shooterRace: Race = Race.enemy, pattern: str = 'ring', bullet_count: int = 12,
                 bullet_speed: float = 3.0, fire_rate: int = 60, pattern_rotation: float = 0.0,
                 pattern_params: dict | None = None) -> None:
        super().__init__(Bullet(), fire_rate, shooterRace)
        self.pattern = pattern
        self.bullet_count = bullet_count
        self.bullet_speed = bullet_speed
        self.pattern_rotation = pattern_rotation
        self.pattern_params = pattern_params or {}

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        angles = PatternLibrary.get(self.pattern, self.bullet_count, self.pattern_rotation, self.pattern_params)
        retList: list[Projectile] = []
        for angle in angles:
            retList.append(self._spawn_bullet(x, y, _vector_from_angle(angle), self.bullet_speed))
        return retList

class RingBlast(EnemyWeapon):
    """环形弹幕：连续发射多圈向外扩散的环形弹。"""
    def __init__(self, shooterRace: Race = Race.enemy, ring_count: int = 16, bullet_speed: float = 2.0,
                 rings: int = 3, ring_interval: int = 10, fire_rate: int = 90) -> None:
        super().__init__(Bullet(), fire_rate, shooterRace)
        self.use_cooldown = False
        self.ring_count = ring_count
        self.bullet_speed = bullet_speed
        self.rings = rings
        self.ring_interval = ring_interval
        self.cool_frames = fire_rate
        self.rings_left = 0
        self.ring_timer = 0
        self.cool_timer = 0

    def _fire(self, x: float, y: float, direction: Vector, game_context: dict | None) -> list[Projectile] | None:
        if self.rings_left > 0:
            self.ring_timer -= 1
            if self.ring_timer <= 0:
                self.ring_timer = self.ring_interval
                self.rings_left -= 1
                retList: list[Projectile] = []
                for i in range(self.ring_count):
                    angle = 360 * i / self.ring_count
                    retList.append(self._spawn_bullet(x, y, _vector_from_angle(angle), self.bullet_speed))
                if self.rings_left == 0:
                    self.cool_timer = self.cool_frames
                return retList
            return None
        self.cool_timer -= 1
        if self.cool_timer <= 0:
            self.rings_left = self.rings
            self.ring_timer = 0
        return None

class ChargeBurstNormal(ChargeBurst):
    """蓄力连射（普通）：1.5 秒蓄力、15 连发、2 秒休息。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('charge_duration', 45)
        kwargs.setdefault('burst_count', 15)
        kwargs.setdefault('burst_interval', 2)
        kwargs.setdefault('rest_duration', 60)
        super().__init__(shooterRace, **kwargs)

class ChargeBurstHard(ChargeBurst):
    """蓄力连射（困难）：1 秒蓄力、20 连发、1.5 秒休息。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('charge_duration', 30)
        kwargs.setdefault('burst_count', 25)
        kwargs.setdefault('burst_interval', 1)
        kwargs.setdefault('rest_duration', 45)
        super().__init__(shooterRace, **kwargs)

class FixedPatternSpiral(FixedPattern):
    """固定弹幕（螺旋）：16 发 2 圈螺旋。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('pattern', 'spiral')
        kwargs.setdefault('bullet_count', 16)
        kwargs.setdefault('bullet_speed', 3.0)
        kwargs.setdefault('fire_rate', 60)
        kwargs.setdefault('pattern_params', {'turns': 2.0})
        super().__init__(shooterRace, **kwargs)

class FixedPatternCross(FixedPattern):
    """固定弹幕（十字）：4 轴各 3 发。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('pattern', 'cross')
        kwargs.setdefault('bullet_count', 12)
        kwargs.setdefault('bullet_speed', 4.0)
        kwargs.setdefault('fire_rate', 60)
        super().__init__(shooterRace, **kwargs)

class FixedPatternDiamond(FixedPattern):
    """固定弹幕（菱形）：4 斜角各 3 发。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('pattern', 'diamond')
        kwargs.setdefault('bullet_count', 12)
        kwargs.setdefault('bullet_speed', 4.0)
        kwargs.setdefault('fire_rate', 60)
        super().__init__(shooterRace, **kwargs)

class RingBlastNormal(RingBlast):
    """环形弹幕（普通）：16 弹/圈、3 圈、3 秒冷却。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('ring_count', 16)
        kwargs.setdefault('bullet_speed', 2.0)
        kwargs.setdefault('rings', 3)
        kwargs.setdefault('ring_interval', 10)
        kwargs.setdefault('fire_rate', 90)
        super().__init__(shooterRace, **kwargs)

class RingBlastWide(RingBlast):
    """环形弹幕（宽）：24 弹/圈、4 圈、2 秒冷却。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('ring_count', 24)
        kwargs.setdefault('bullet_speed', 2.5)
        kwargs.setdefault('rings', 4)
        kwargs.setdefault('ring_interval', 8)
        kwargs.setdefault('fire_rate', 60)
        super().__init__(shooterRace, **kwargs)

class PhaseSwitch(EnemyWeapon):
    """阶段切换：按时间或血量阈值在多个子武器间切换。

    phases 示例: [{"weapon": "FanSweepNormal", "duration": 300, "params": {"fan_angle": 45}}, ...]
    trigger: 'time'（duration 后切档）| 'health'/'hp_ratio'（血量低于 max*threshold 后切档）
    """
    def __init__(self, shooterRace: Race = Race.enemy, phases: list[dict] | None = None,
                 trigger: str = 'time', health_threshold: float = 0.5) -> None:
        super().__init__(Bullet(), 1, shooterRace)
        self.use_cooldown = False
        self.phases: list[dict] = phases or []
        self.trigger = trigger
        self.health_threshold = health_threshold
        self.current_phase = 0
        self.phase_timer = 0
        self.max_health: float | None = None
        self.current_weapon: Weapon | None = None
        if len(self.phases) > 0:
            self._enter_phase(0)

    def _enter_phase(self, index: int) -> None:
        self.current_phase = index % len(self.phases)
        phase = self.phases[self.current_phase]
        params = {'shooterRace': self.shooterRace}
        params.update(phase.get('params', {}))
        weapon = createInstanceFromClassname(phase['weapon'], params)
        weapon.isShooting = True
        self.current_weapon = weapon
        self.phase_timer = phase.get('duration', 0)

    def _check_trigger(self, game_context: dict | None) -> bool:
        """返回 True 表示应切换到下一阶段。"""
        if self.trigger == 'time':
            self.phase_timer -= 1
            return self.phase_timer <= 0
        if self.trigger in ('health', 'hp_ratio'):
            enemy = game_context.get('enemy') if game_context else None
            if enemy is None:
                return False

            enemy_health = getattr(enemy, 'health', None)
            if enemy_health is None:
                return False

            # 某些配置可能传入 None，避免出现 "unsupported operand type(s) for *: 'NoneType' and 'float'"
            threshold = self.health_threshold if self.health_threshold is not None else 0.5
            max_health = self.max_health
            if max_health is None:
                max_health = enemy_health
                self.max_health = max_health
            if enemy_health <= max_health * threshold:
                self.max_health = enemy_health
                return True
        return False

    def shoot(self, x: float, y: float, times: int | Vector | dict | None = 1,
              direction: Vector | dict | None = None,
              game_context: dict | None = None) -> list[Projectile] | None:
        """兼容 EnemyWeapon.shoot() 的签名，并接受旧版 direction/game_context 调用。"""
        if isinstance(times, Vector):
            if isinstance(direction, dict) and game_context is None:
                game_context = direction
            direction = times
            times = 1
        elif isinstance(times, dict) and direction is None and game_context is None:
            game_context = times
            times = 1

        if not self.isShooting or direction is None:
            return None
        if self.current_weapon is None:
            return None
        if self._check_trigger(game_context):
            self._enter_phase(self.current_phase + 1)

        if isinstance(self.current_weapon, EnemyWeapon):
            return self.current_weapon.shoot(x, y, direction=direction, game_context=game_context)
        return self.current_weapon.shoot(x, y)

    def update(self) -> None:
        super().update()
        if self.current_weapon is not None:
            self.current_weapon.update()

class PhaseSwitchEarly(PhaseSwitch):
    """阶段切换（前期）：时间触发，2 阶段（扇形扫射 → 环形弹幕）。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('trigger', 'time')
        kwargs.setdefault('phases', [
            {'weapon': 'FanSweepNormal', 'duration': 300},
            {'weapon': 'RingBlastNormal', 'duration': 200},
        ])
        super().__init__(shooterRace, **kwargs)

class PhaseSwitchLate(PhaseSwitch):
    """阶段切换（后期）：血量触发，3 阶段（扇形齐射 → 蓄力连射 → 预判射击）。"""
    def __init__(self, shooterRace: Race = Race.enemy, **kwargs) -> None:
        kwargs.setdefault('trigger', 'hp_ratio')
        kwargs.setdefault('health_threshold', 0.66)
        kwargs.setdefault('phases', [
            {'weapon': 'FanVolleyHard', 'duration': 0},
            {'weapon': 'ChargeBurstHard', 'duration': 0},
            {'weapon': 'MissileLauncher', 'duration': 0},
            {'weapon': 'LeadShotHard', 'duration': 0},
        ])
        super().__init__(shooterRace, **kwargs)

class EnergyWeapon(Weapon):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(EnergyBall(), 2.5 * gametick, shooterRace)
        self.level= 0
        self.sound = Sounds.unprepare
        self.maxLevel = 0
        self.jamType = WeaponJamType.shotgun

class EnergyWeaponEnhanced(Weapon):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(EnergyBallEnhanced(), 3 * gametick, shooterRace)
        self.level= 0
        self.sound = Sounds.prepare
        self.maxLevel = 0
        self.jamType = WeaponJamType.shotgun

class RocketLauncherEnemy(Weapon):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(RocketEnemy(), 3 * gametick, shooterRace)
        self.level= 0
        self.sound = Sounds.rocket_shoot
        self.maxLevel = 0
        self.jamType = WeaponJamType.shotgun

class Shotgun(Weapon):
    bulletSpreadMap: dict[int, list[int | tuple[int, int]]] = {
        1: [0],
        2: [-2, 2],
        3: [-3, 0, 3],
        4: [(-1, 0), -2, 2, (1, 0)],
        5: [(-2, 0), (-1, 0), 0, (1, 0), (2, 0)],
        6: [(-2, 0), (-1, 0), -3, 0, 3, (1, 0), (2, 0)],
        7: [(-3, 0), (-2, 0), (-1, 2), (0, 2), (1, 2), (2, 0), (3, 0)],
        8: [(-3, 0), (-2, 0), (-1, 2), -2, (0, 2), 2, (1, 2), (2, 0), (3, 0)],
        9: [(-5, 0), (-3, 0), (-1, 2), -4, (0, 2), 4, (1, 2), (3, 0), (5, 0)],
        10: [(-5, 0), (-3, 0), (-1, 2), -4, -2, (0, 2), 2, 4, (1, 2), (3, 0), (5, 0)],
    }
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Bullet(), 5, shooterRace)
        self.sound = Sounds.shotgun_shoot
        self.jamType = WeaponJamType.shotgun
    
    def shoot(self, x: float, y: float, times: int = 1) -> list[Projectile] | None:
        projs = super().shoot(x, y, len(self.bulletSpreadMap[self.level]))
        if projs is not None:
            for i in range(len(projs)):
                proj = projs[i]
                spreadList = self.bulletSpreadMap[self.level]
                item = spreadList[i]
                if isinstance(item, tuple):
                    proj.velocity += Vector(item[0], item[1])
                else:
                    proj.x += item
                if self.shooterRace == Race.enemy:
                    proj.chooseTarget = True
                    proj.image = Images.bullet_enemy
        return projs

class LazerGun(Weapon):
    bulletImageMap: dict[int, Images] = {
        1: Images.lazer1,
        2: Images.lazer2,
        3: Images.lazer3,
        4: Images.lazer4,
        5: Images.lazer5,
        6: Images.lazer6,
        7: Images.lazer7,
        8: Images.lazer8,
        9: Images.lazer9,
        10: Images.lazer10
    }
    bulletDamageMap: dict[int, float] = {
        1: 2,
        2: 4,
        3: 6.5,
        4: 9,
        5: 11,
        6: 13,
        7: 15,
        8: 18,
        9: 20,
        10: 22
    }
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Lazer(), 1.5, shooterRace)
        self.sound = Sounds.lazer_shoot
        self.jamType = WeaponJamType.lazer
    
    def shoot(self, x: float, y: float, times: int = 1) -> list[Projectile] | None:
        projs = super().shoot(x, y)
        if projs:
            proj = projs[0]
            proj.image = self.bulletImageMap[self.level]
            proj.damage = self.bulletDamageMap[self.level]
            proj.boundingBox = BoundingBox(3 * (proj.damage / 1.5), 15)
            if self.shooterRace == Race.enemy:
                proj.velocity.y = -proj.velocity.y
        return projs

class Autocannon(Weapon):
    bulletImageMap: dict[int, Images] = {
        1: Images.autocannon12,
        2: Images.autocannon12,
        3: Images.autocannon34,
        4: Images.autocannon34,
        5: Images.autocannon56,
        6: Images.autocannon56,
        7: Images.autocannon7,
        8: Images.autocannon8,
        9: Images.autocannon9,
        10: Images.autocannon10
    }
    bulletDamageMap: dict[int, float] = {
        1: 10,
        2: 12,
        3: 15,
        4: 20,
        5: 24,
        6: 28,
        7: 31,
        8: 35,
        9: 37,
        10: 40
    }
    bulletVelocityMap: dict[int, float] = {
        1: -20,
        2: -24,
        3: -24,
        4: -30,
        5: -30,
        6: -40,
        7: -40,
        8: -40,
        9: -40,
        10: -40
    }
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(AutocannonShells(), 10, shooterRace)
        self.sound = Sounds.autocannon_shoot
        self.jamType = WeaponJamType.shotgun
    
    def shoot(self, x: float, y: float, times: int = 1) -> list[Projectile] | None:
        projs = super().shoot(x, y, 1)
        if projs is not None:
            proj = projs[0]
            proj.chooseTargetAngle = 120
            proj.velocity.y = self.bulletVelocityMap[self.level]
            proj.damage = self.bulletDamageMap[self.level]
            proj.image = self.bulletImageMap[self.level]
        return projs

class MissileLauncher(Weapon):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Missile(), 15, shooterRace)
        self.handedness = 1
        self.level = 0
        self.maxLevel = 0
        self.sound = Sounds.missile_shoot

    def shoot(self, x: float, y: float, times: int = 1) -> list[Projectile] | None:
        if self.isShooting and self.cooldown <= 0:
            Board.msgQueue.push(Message('server', 'playsound', {"sound": self.sound.value}))
            missileL = Missile()
            missileR = Missile(handedness=-1)
            missileL.shooterRace = self.shooterRace
            missileL.x = x
            missileL.y = y
            missileR.shooterRace = self.shooterRace
            missileR.x = x
            missileR.y = y
            self.cooldown = self.fireRate
            return [missileL, missileR]
        else:
            return None

class RocketLauncher(Weapon):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Rocket(), 20, shooterRace)
        self.sound = Sounds.rocket_shoot
    
    def shoot(self, x: float, y: float, times: int = 1) -> list[Projectile] | None:
        if self.isShooting and self.cooldown <= 0:
            Board.msgQueue.push(Message('server', 'playsound', {"sound": self.sound.value}))
            RocketL = Rocket()
            RocketR = Rocket(handedness=-1)
            RocketL.shooterRace = self.shooterRace
            RocketL.x = x
            RocketL.y = y
            RocketR.shooterRace = self.shooterRace
            RocketR.x = x
            RocketR.y = y
            self.cooldown = self.fireRate
            return [RocketL, RocketR]
        else:
            return None

class Shotgun_slow(Shotgun):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(shooterRace)
        self.fireRate = 1 * gametick

class Shotgun_normal(Shotgun):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(shooterRace)
        self.fireRate = 0.5 * gametick

class MissileLauncher_slow(MissileLauncher):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(shooterRace)
        self.fireRate = 1.5 * gametick
        self.jamType = WeaponJamType.shotgun

class Unit(Entity):
    def __init__(self, x: float = 0, y: float = 0, health: float = 100, width: float = 100, height: float = 50) -> None:
        super().__init__(x, y)
        self.health = health
        self.weapon = WeaponGroup()
        self.boundingBox = BoundingBox(width, height)
        self.inventory: list[ItemTypes] = []
    
    def update(self) -> None:
        super().update()
        if self.health <= 0:
            self.isAlive = False
        self.weapon.update()

class Enemy(Unit):
    def __init__(self) -> None:
        super().__init__()
        self.race = Race.enemy
        self.weapon = WeaponGroup()
        self.targetPos: list[int] | None = None
        # 移动模式：random（原有随机游走）| station（静止）| strafe（横向往返）| circle（圆周运动）
        self.move_pattern: str = 'random'
        # 射击模式：auto（持续射击，原有行为）| burst（间歇射击）
        self.shoot_pattern: str = 'auto'
        # 机制武器标记：weapon 列表包含 EnemyWeapon 子类时为 True，Board.update 走 context 射击
        self.uses_mechanic_weapons: bool = False
        # 外部强制停止移动（ChargeBurst 蓄力期由武器设置）
        self.stop_movement: bool = False
        # burst 间歇射击计时
        self._burstTimer = 0
        self._burstOn = 30
        self._burstOff = 30
        # strafe / circle 状态
        self._strafeDir = 1
        self._circleAngle = 0.0
        self._circleCenter: list[float] | None = None
        # 移动推力（strafe/circle/station 飞行共用，可在 enemyTypes.json 配置调慢）
        self.move_thrust: float = 1.5
        # station 驻留点（飞到后定住；None 时随机生成）
        self._stationTarget: list[int] | None = None

    def randomTargetPos(self) -> None:
        self.targetPos = [random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1])]
        self.acceleration = Vector(0, random.randint(-10, 10) / 10)

    def update(self) -> None:
        super().update()
        self.rotation = ~self.velocity
        self._update_shooting()
        self._update_movement()

    def _update_shooting(self) -> None:
        if self.shoot_pattern == 'auto':
            self.weapon.isShooting = True
        elif self.shoot_pattern == 'burst':
            self._burstTimer -= 1
            if self._burstTimer <= 0:
                self.weapon.isShooting = not self.weapon.isShooting
                self._burstTimer = self._burstOn if self.weapon.isShooting else self._burstOff

    def _update_movement(self) -> None:
        if self.stop_movement:
            self.velocity = Vector(0, 0)
            self.acceleration = Vector(0, 0)
            return
        if self.move_pattern == 'random':
            if self.targetPos is not None:
                self.faceToTargetPos()
            else:
                self.randomTargetPos()
            distance = self.distanceToTargetPos()
            if distance is not None:
                if distance < 30:
                    self.randomTargetPos()
            if self.velocity == Vector(0, 0):
                self.randomTargetPos()
        elif self.move_pattern == 'station':
            # 从屏幕外飞向驻留点，到达后定住不动
            if self._stationTarget is None:
                if self.targetPos is not None:
                    self._stationTarget = self.targetPos
                else:
                    self._stationTarget = [random.randint(0, SCREENSIZE[0]), random.randint(80, 400)]
            a0 = Vector(self._stationTarget[0] - self.x, self._stationTarget[1] - self.y)
            dist = (a0.x**2 + a0.y**2) ** 0.5
            if dist < 20:
                self.velocity = Vector(0, 0)
                self.acceleration = Vector(0, 0)
            else:
                self.acceleration = a0 * (self.move_thrust / dist)
        elif self.move_pattern == 'strafe':
            self.acceleration = Vector(self.move_thrust * self._strafeDir, 0)
            if self.x >= SCREENSIZE[0] - 30:
                self._strafeDir = -1
            elif self.x <= 30:
                self._strafeDir = 1
        elif self.move_pattern == 'circle':
            if self._circleCenter is None:
                self._circleCenter = [SCREENSIZE[0] / 2, SCREENSIZE[1] / 2]
            self._circleAngle = (self._circleAngle + 2.0) % 360
            radius = 150
            target_x = self._circleCenter[0] + radius * math.cos(math.radians(self._circleAngle))
            target_y = self._circleCenter[1] + radius * math.sin(math.radians(self._circleAngle))
            # 固定推力朝目标点（直接赋值加速度，避免 faceToTarget 对 0 长度加速度失效）
            a0 = Vector(target_x - self.x, target_y - self.y)
            l0 = (a0.x**2 + a0.y**2) ** 0.5
            if l0 > 0:
                self.acceleration = a0 * (self.move_thrust / l0)

    def faceToTargetPos(self) -> None:
        if self.targetPos is None:
            return
        a0 = Vector(self.targetPos[0] - self.x, self.targetPos[1] - self.y)
        l0 = (a0.x**2 + a0.y**2)**0.5
        ls = (self.acceleration.x**2 + self.acceleration.y**2)**0.5
        an = Vector(a0.x * (ls / l0), a0.y * (ls / l0))
        self.acceleration = an
    
    def distanceToTargetPos(self) -> float | None:
        if self.targetPos is not None:
            return ((self.targetPos[0] - self.x)**2 + (self.targetPos[1] - self.y)**2)**0.5
        else:
            return None

class Player(Unit):
    x: float
    y: float
    def __init__(self, player_id: int) -> None:
        super().__init__()
        self.player_id = player_id
        self.name: str = str(self.player_id)
        self.race = Race.player
        self.pressedKeyList: list[int] = []
        self.joystickAxisList: list[float] = [0.0, 0.0]
        self.gottenItem: list[ItemTypes] = []
        self.magabombQuantity = 1
        self.isReady = False
        self.isThrowingMagabomb = False
        self.boundingBox = BoundingBox(16, 32)
        self.weapon = WeaponGroup(Shotgun(self.race))
        self.maxVelocity = 15.0
        # 飞入战场状态：从屏幕最下方飞入并在加入位置停下（加入/复活/通关复活共用）
        self.isEntering: bool = False
        self._enterTargetX = 0.0
        self._enterTargetY = 2 / 3 * SCREENSIZE[1]
        self._enterSpeed = 20.0   # 初始向上速度（帧）
        self._enterDecel = 0.83   # 每帧减速（24 帧 ≈ 0.8 秒到达并恰好停下）
    
    def startEntering(self, target_x: float | None = None, target_y: float | None = None) -> None:
        """从屏幕最下方（y=SCREENSIZE[1]+50）飞入战场，1 秒内匀减速到目标位置停下。

        target_x 默认当前 x（加入/复活的随机停靠位）；target_y 默认 2/3 屏高（玩家加入位置）。
        """
        self.isEntering = True
        if target_x is None:
            target_x = self.x
        if target_y is None:
            target_y = 2 / 3 * SCREENSIZE[1]
        self._enterTargetX = float(target_x)
        self._enterTargetY = float(target_y)
        self.x = self._enterTargetX
        self.y = SCREENSIZE[1] + 50
        self.velocity = Vector(0, -self._enterSpeed)
        self.acceleration = Vector(0, self._enterDecel)
        self.rotation = ~self.velocity

    def _updateEntering(self) -> None:
        """飞入动画推进：匀减速向上，到达目标位置后停下。"""
        self.y += self.velocity.y
        self.velocity.y += self._enterDecel
        self.rotation = ~self.velocity
        if self.y <= self._enterTargetY or self.velocity.y >= 0:
            self.y = self._enterTargetY
            self.velocity = Vector(0, 0)
            self.acceleration = Vector(0, 0)
            self.isEntering = False

    def update(self) -> None:
        if Keys.c in self.pressedKeyList:
            self.isReady = True
        else:
            if self.isReady == True:
                self.isReady = False
        if self.isEntering:
            # 飞入动画期间：不受输入/重力/碰撞伤害影响（无敌），仅推进动画
            self._updateEntering()
            self.weapon.update()
            return
        super().update()
        if Keys.e in self.pressedKeyList and self.magabombQuantity > 0:
            self.magabombQuantity -= 1
            self.isThrowingMagabomb = True
            self.pressedKeyList.remove(Keys.e)
        if Keys.w in self.pressedKeyList:
            self.acceleration.y = -1.5
        elif Keys.s in self.pressedKeyList:
            self.acceleration.y = 1.5
        elif self.joystickAxisList[1] != 0:
            self.acceleration.y = 1.5 * self.joystickAxisList[1]
        else:
            self.acceleration.y = 0
        if Keys.a in self.pressedKeyList:
            self.acceleration.x = -1.5
        elif Keys.d in self.pressedKeyList:
            self.acceleration.x = 1.5
        elif self.joystickAxisList[0] != 0:
            self.acceleration.x = 1.5 * self.joystickAxisList[0]
        else:
            self.acceleration.x = 0
        if self.x < 0 : self.x = 0
        if self.y < 0 : self.y = 0
        if self.x > SCREENSIZE[0] : self.x = SCREENSIZE[0]
        if self.y > SCREENSIZE[1] : self.y = SCREENSIZE[1]
        for item in list(self.gottenItem):
            Board.msgQueue.push(Message("server", 'playsound', {"sound": "itemget"}))
            w = self.weapon
            if item == ItemTypes.missile:
                w.removeAll(MissileLauncher)
                w.addWeapon(MissileLauncher(self.race))
                w.removeAll(RocketLauncher)
            elif item == ItemTypes.rocket:
                w.removeAll(RocketLauncher)
                w.addWeapon(RocketLauncher(self.race))
                w.removeAll(MissileLauncher)
            elif item == ItemTypes.shotgun:
                if w.has(Shotgun) == False:
                    w.removeAll(LazerGun)
                    w.removeAll(Autocannon)
                    w.addWeapon(Shotgun(self.race))
                else:
                    w.upgrade(Shotgun)
            elif item == ItemTypes.lazer:
                if w.has(LazerGun) == False:
                    w.removeAll(Shotgun)
                    w.removeAll(Autocannon)
                    w.addWeapon(LazerGun(self.race))
                else:
                    w.upgrade(LazerGun)
            elif item == ItemTypes.autocannon:
                if w.has(Autocannon) == False:
                    w.removeAll(Shotgun)
                    w.removeAll(LazerGun)
                    w.addWeapon(Autocannon(self.race))
                else:
                    w.upgrade(Autocannon)
            elif item == ItemTypes.super:
                for _ in range(10):
                    w.upgrade(LazerGun)
                    w.upgrade(Shotgun)
                    w.upgrade(Autocannon)
            elif item == ItemTypes.magabomb:
                self.magabombQuantity += 1
                continue
            elif item == ItemTypes.medic:
                self.health = min(self.health + 50 * random.random() + 25, 100)
                continue
            self.inventory.append(item)
        self.gottenItem.clear()
        w = self.weapon
        if Keys.space in self.pressedKeyList:
            w.isShooting = True
        else:
            if w.isShooting == True:
                w.isShooting = False

class EnemyBuilder:
    def __init__(self,
                 health: float = 100,
                 image: str | Images = 'en',
                 weapon: list[str] | None = None,
                 velocity: Vector = Vector(0, 0),
                 acceleration: Vector = Vector(0, 0),
                 boundingBox: BoundingBox | None = None,
                 targetPos: list[int] | None = None,
                 maxVelocity: float | None = None,
                 velocityMultiplier: float = 0.9,
                 inventory: list[int] | None = None,
                 weapon_params: dict | None = None,
                 move_pattern: str = 'random',
                 shoot_pattern: str = 'auto',
                 move_thrust: float = 1.5
                 ) -> None:
        self.enemy = Enemy()
        self.enemy.maxVelocity = maxVelocity
        self.enemy.velocityMultiplier = velocityMultiplier
        self.enemy.health = health
        self.enemy.image = Images(image) if isinstance(image, str) else image
        self.enemy.velocity = velocity
        self.enemy.targetPos = targetPos
        self.enemy.acceleration = acceleration
        self.enemy.boundingBox = boundingBox
        self.enemy.inventory = [ItemTypes(item) for item in (inventory or [])]
        self.enemy.move_pattern = move_pattern
        self.enemy.shoot_pattern = shoot_pattern
        self.enemy.move_thrust = move_thrust
        self.weapon_params: dict = weapon_params or {}
        if weapon is not None:
            weapons = [self._create_weapon(w) for w in weapon]
            self.enemy.weapon = WeaponGroup(*weapons)
            self.enemy.uses_mechanic_weapons = any(isinstance(w, EnemyWeapon) for w in weapons)
        else:
            self.enemy.weapon = WeaponGroup()

    def _create_weapon(self, classname: str) -> Weapon:
        """创建武器实例：基础参数 + weapon_params[classname] 覆盖注入。"""
        params: dict = {'shooterRace': Race.enemy}
        if classname in self.weapon_params:
            params.update(self.weapon_params[classname])
        return createInstanceFromClassname(classname, params)

    def build(self) -> Enemy:
        return self.enemy

class Board:
    msgQueue: Queue = Queue()
    def __init__(self, msgQueue: Queue) -> None:
        self.players: list[Player] = []
        self.units: list[Unit] = []
        self.projectiles: list[Projectile] = []
        self.objects: list[list[Entity]] = [self.players, self.units, self.projectiles]  # type: ignore[arg-type]
        Board.msgQueue = msgQueue
        self.currId = -1
    
    def increaseId(self) -> None:
        self.currId += 1
    
    def nearestPlayer(self, x: float, y: float) -> Player | None:
        if len(self.players) == 0:
            return None
        return min(self.players, key=lambda p: (p.x - x)**2 + (p.y - y)**2)
    
    def nearestUnit(self, x: float, y: float, race: Race) -> Unit | None:
        unitList = []
        for unit in self.units:
            if unit.race == race:
                unitList.append(unit)
        if len(unitList) == 0:
            return None
        return min(unitList, key=lambda u: (u.x - x)**2 + (u.y - y)**2)

    def nearestEnemyInCone(self, x: float, y: float, coneAngle: float, forwardDir: Vector, targetRace: Race) -> Unit | None:
        candidates = [u for u in self.units if isinstance(u, Unit) and u.race == targetRace]
        if not candidates:
            return None
        forwardAngle = ~forwardDir
        halfAngle = coneAngle / 2.0
        valid = []
        for enemy in candidates:
            toEnemy = Vector(enemy.x - x, enemy.y - y)
            dist = (toEnemy.x**2 + toEnemy.y**2) ** 0.5
            if dist == 0:
                continue
            enemyAngle = ~toEnemy
            diff = abs(enemyAngle - forwardAngle) % 360
            diff = min(diff, 360 - diff)
            if diff <= halfAngle:
                valid.append(enemy)
        if not valid:
            return None
        return min(valid, key=lambda e: (e.x - x)**2 + (e.y - y)**2)

    def findPlayer(self, player_id: int) -> Player | None:
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None

    def addPlayer(self, player: Player) -> None:
        self.players.append(player)
        self.increaseId()
        player.id = self.currId
    
    def addUnit(self, unit: Entity, type: str) -> None:
        if type == 'unit':
            if not isinstance(unit, Item):
                if isinstance(unit, Enemy) and unit.move_pattern == 'strafe':
                    # strafe 只有水平移动：y 必定在屏幕内（>0），从左右两侧飞入，避免屏幕外游荡
                    unit.y = random.randint(1, 100)
                    unit.x = random.choice([-50, SCREENSIZE[0] + 50])
                else:
                    # 其他敌人（含 station 驻留型）从屏幕外飞入：y 在屏幕外上方~屏幕内上部随机
                    unit.y = random.randint(-80, 100)
                    if unit.y > 0:
                        # 屏幕内 → 从左右两侧飞入（x 放屏幕外）
                        unit.x = random.choice([-50, SCREENSIZE[0] + 50])
                    else:
                        # 屏幕外上方 → 从顶部飞入（x 屏幕内随机）
                        unit.x = random.randint(0, SCREENSIZE[0])
            self.units.append(unit)  # type: ignore[arg-type]
            self.increaseId()
            unit.id = self.currId
        elif type == 'projectile' and isinstance(unit, Projectile):
            self.projectiles.append(unit)
            self.increaseId()
            unit.id = self.currId
    
    def getScreenObjects(self) -> list[dict[str, Any]]:
        retList: list[dict[str, Any]] = []
        for obj in self.objects:
            for item in obj:
                if item.image is None:
                    continue
                appDict: dict[str, Any] = {
                    'id': item.id,
                    'x': item.x,
                    'y': item.y,
                    'rotation': item.rotation,
                    'image': item.image.value,
                    } 
                if isinstance(item, Player):
                    appDict['health'] = item.health
                    appDict['isReady'] = item.isReady
                    appDict['player_id'] = item.player_id
                    appDict['name'] = item.name
                    appDict['magabombQuantity'] = item.magabombQuantity
                if isinstance(item, Item):
                    appDict['alpha'] = item.alpha
                retList.append(appDict)
        return retList
    
    def isAllPlayerPrepared(self) -> bool:
        return len(self.players) > 0 and all(player.isReady for player in self.players)

    def checkCollision(self, item: Entity, grid: SpatialGrid | None = None) -> None:
        if grid is not None:
            for other in grid.get_nearby(item):
                if item != other and item & other:
                    item.onCollision(other)
        else:
            for obj in self.objects:
                for other in obj:
                    if item != other and item & other:
                        item.onCollision(other)
    
    def generateSoundMessage(self, sound: Sounds | str) -> Message:
        if type(sound) == Sounds:
            sound = sound.value
        return Message('server', 'playsound', {"sound": sound})

    def generateParticleMessage(self, effect: ParticleEffect | str, x: float, y: float) -> Message:
        if isinstance(effect, ParticleEffect):
            effect = effect.value
        return Message('server', 'particle_effect', {"effect": effect, "x": x, "y": y})
    
    def update(self) -> None:
        spatial = SpatialGrid()
        for obj in self.objects:
            for item in obj:
                spatial.add(item)
        for obj in self.objects:
            for item in obj[:]:
                item.update()
                if item.x < disappearAera[0] or\
                   item.x > disappearAera[2] or\
                   item.y < disappearAera[1] or\
                   item.y > disappearAera[3]:
                    item.isAlive = False
                if isinstance(item, Magabomb) and item.isExploding:
                    for i in self.units[:]:
                        if isinstance(i, Unit):
                            for itemType in i.inventory:
                                itemUnit = Item(itemType)
                                itemUnit.x = i.x
                                itemUnit.y = i.y
                                self.addUnit(itemUnit, 'unit')
                            self.msgQueue.push(self.generateSoundMessage(f"explode{random.randint(1, 5)}"))
                        self.units.remove(i)
                        del i
                    for i in self.projectiles[:]:
                        self.projectiles.remove(i)
                        del i
                    self.msgQueue.push(self.generateSoundMessage(Sounds.nuclear_missile_explode))
                    self.msgQueue.push(self.generateParticleMessage(ParticleEffect.nuke_explosion, item.x, item.y))
                    break
                if isinstance(item, Unit):
                    if item.weapon.isShooting:
                        if isinstance(item, Enemy) and item.uses_mechanic_weapons:
                            direction: Vector | None = None
                            target = self.nearestPlayer(item.x, item.y)
                            if target is not None:
                                direction = Vector(target.x - item.x, target.y - item.y)
                            bullets = item.weapon.shoot_with_context(
                                item.x, item.y, direction, {'players': self.players, 'enemy': item})
                        else:
                            bullets = item.weapon.shoot(item.x, item.y)
                        for bullet in bullets:
                            if bullet is not None:
                                if bullet.chooseTargetAngle < 360:
                                    if bullet.shooterRace == Race.player:
                                        target = self.nearestEnemyInCone(bullet.x, bullet.y, bullet.chooseTargetAngle, Vector(0, -1), Race.enemy)
                                    else:
                                        target = self.nearestEnemyInCone(bullet.x, bullet.y, bullet.chooseTargetAngle, Vector(0, 1), Race.player)
                                    if target is not None:
                                        bullet.faceToTarget(target, 'velocity')
                                        bullet.faceToTarget(target, 'acceleration')
                                if bullet.chooseTarget == True:
                                    if bullet.shooterRace == Race.enemy:
                                        target = self.nearestPlayer(bullet.x, bullet.y)
                                        if target is not None:
                                            bullet.faceToTarget(target, 'velocity')
                                            bullet.faceToTarget(target, 'acceleration')
                                            bullet.chooseTarget = False
                                    else:
                                        bullet.chooseTarget = False
                                if isinstance(bullet, (Missile, Rocket)):
                                    if bullet.shooterRace == Race.enemy:
                                        bullet.target = self.nearestPlayer(bullet.x, bullet.y)
                                    else:
                                        race = Race.enemy
                                        bullet.target = self.nearestUnit(bullet.x, bullet.y, race)
                                self.addUnit(bullet, 'projectile')
                if isinstance(item, Player) and item.isThrowingMagabomb == True:
                    item.isThrowingMagabomb = False
                    magabomb = Magabomb()
                    magabomb.x = item.x
                    magabomb.y = item.y
                    self.addUnit(magabomb, 'projectile')
                    self.msgQueue.push(self.generateSoundMessage(Sounds.nuclear_missile_shoot))
                for other in spatial.get_nearby(item):
                    if item != other and item & other:
                        was_alive = item.isAlive
                        item.onCollision(other)
                        if was_alive and not item.isAlive:
                            if isinstance(item, Missile):
                                self.msgQueue.push(self.generateParticleMessage(ParticleEffect.missile_hit, item.x, item.y))
                            elif isinstance(item, Rocket):
                                self.msgQueue.push(self.generateParticleMessage(ParticleEffect.rocket_hit, item.x, item.y))
                            elif isinstance(item, Bullet):
                                self.msgQueue.push(self.generateParticleMessage(ParticleEffect.bullet_hit, item.x, item.y))
                            elif isinstance(item, Lazer):
                                self.msgQueue.push(self.generateParticleMessage(ParticleEffect.lazer_hit, item.x, item.y))
                            elif isinstance(item, AutocannonShells):
                                self.msgQueue.push(self.generateParticleMessage(ParticleEffect.autocannon_hit, item.x, item.y))
                if isinstance(item, Unit) and item.health <= 0:
                    item.isAlive = False
                    if isinstance(item, Player):
                        self.msgQueue.push(self.generateParticleMessage(ParticleEffect.player_explosion, item.x, item.y))
                    else:
                        self.msgQueue.push(self.generateParticleMessage(ParticleEffect.enemy_explosion, item.x, item.y))
                if item.isAlive == False:
                    if isinstance(item, Unit):
                        for itemType in item.inventory:
                            itemUnit = Item(itemType)
                            itemUnit.x = item.x
                            itemUnit.y = item.y
                            self.addUnit(itemUnit, 'unit')
                    if isinstance(item, Player):
                        for itemType in item.gottenItem:
                            itemUnit = Item(itemType)
                            itemUnit.x = item.x
                            itemUnit.y = item.y
                            self.addUnit(itemUnit, 'unit')
                        item.gottenItem.clear()
                    obj.remove(item)
                    if isinstance(item, Unit):
                        self.msgQueue.push(self.generateSoundMessage(f"explode{str(random.randint(1, 5))}"))
                    del item

class Flag:
    def __init__(self, unitTypeList: list[str], timeBeforeNext: int, finishCondition: int) -> None:
        self.timeBeforeNext = timeBeforeNext
        self.isFinished = False
        self.finishCondition: FlagFinishCondition = FlagFinishCondition(finishCondition)
        self.drops: list[int] = []
        self.unitTypeList = unitTypeList
    
    def getUnits(self) -> list[str]:
        self.isFinished = True
        return self.unitTypeList

class Level:
    def __init__(self, name: str, totalFlags: int, flags: list[dict], drops: list[int]) -> None:
        self.name = name
        self.currFlagIndex: int = -1
        self.totalFlags = totalFlags
        self.waitLoaded = False
        self.isFinished = False
        self.flags: list[Flag] = []
        for i in range(totalFlags):
            self.flags.append(Flag(**flags[i]))
        self._initialDrops: list[int] = list(drops)
        for item in drops:
            flag = random.choice(self.flags)
            flag.drops.append(item)
    
    def nextFlag(self) -> None:
        self.currFlagIndex += 1
        if self.currFlagIndex >= self.totalFlags:
            self.isFinished = True
            return
        self.flags[self.currFlagIndex].isFinished = False

    def reset(self) -> None:
        """重置本关卡进度（供服务器自动重置后重新开局使用）。"""
        self.currFlagIndex = -1
        self.waitLoaded = False
        self.isFinished = False
        for flag in self.flags:
            flag.isFinished = False
            flag.drops = []
        # 恢复初始掉落物品（重新随机分配到各 flag）
        for item in self._initialDrops:
            flag = random.choice(self.flags)
            flag.drops.append(item)
    
    def getCurrFlag(self) -> Flag | None:
        if self.currFlagIndex == -1 or self.currFlagIndex >= self.totalFlags:
            return None
        else:
            return self.flags[self.currFlagIndex]
    
    def loadFlag(self) -> Flag | None:
        self.nextFlag()
        if self.isFinished == True:
            return None
        return self.flags[self.currFlagIndex]

    def splitFlag(self, flag: Flag, avgLevel: int, nukeBonus: int = 0) -> Flag:
        total = len(flag.unitTypeList)
        if total <= 1:
            return flag
        ratio = avgLevel / MIN_WEAPON_LEVEL_THRESHOLD
        frontCount = max(1, int(total * ratio + MIN_ENEMY_COUNT_THRESHOLD + avgLevel - MIN_WEAPON_LEVEL_THRESHOLD / 2) + nukeBonus)
        if frontCount >= total:
            return flag
        indices = list(range(total))
        random.shuffle(indices)
        pick = set(indices[:frontCount])
        frontUnits = [flag.unitTypeList[i] for i in range(total) if i in pick]
        backUnits = [flag.unitTypeList[i] for i in range(total) if i not in pick]
        frontFlag = Flag(frontUnits, flag.timeBeforeNext, flag.finishCondition.value)
        frontFlag.drops = []
        backFlag = Flag(backUnits, 20, 1)
        backFlag.drops = []
        for item in flag.drops:
            if random.random() < 0.5:
                frontFlag.drops.append(item)
            else:
                backFlag.drops.append(item)
        self.flags.insert(self.currFlagIndex + 1, backFlag)
        self.totalFlags += 1
        return frontFlag

class LevelLoader:
    def __init__(self, path: str = '.\\levels') -> None:
        self.currLevel = -1
        self.path = path
        self.levelList = os.listdir(path)
        self.totalLevel = len(self.levelList)
        self.isFinished = False
        self.levelData: list[Level] = []
        if hasattr(configuration, 'enemyTypes'):
            self.standardTypeList = configuration.enemyTypes.copy()
        else:
            self.standardTypeList = {}
    
    def createAttr(self) -> None:
        unitTypes = list(self.standardTypeList.keys())
        for type in unitTypes:
            kwargs = self.standardTypeList[type]
            #kwargs['weapon'] = WeaponGroup(*[createInstanceFromClassname(kwargs['weapon'][i], {'shooterRace': Race.enemy}) for i in range(len(kwargs['weapon']))]) if 'weapon' in kwargs else None
            kwargs['velocity'] = Vector(**kwargs['velocity']) if 'velocity' in kwargs else Vector(0, 0)
            kwargs['acceleration'] = Vector(**kwargs['acceleration']) if 'acceleration' in kwargs else Vector(0, 0)
            kwargs['boundingBox'] = BoundingBox(**kwargs['boundingBox']) if 'boundingBox' in kwargs else None
            #self.objectsList.append(EnemyBuilder(**kwargs).build())
    
    def createUnits(self, unitTypeList: list[str]) -> list[Enemy]:
        unitList = []
        for type in unitTypeList:
            kwargs = self.standardTypeList[type]
            unit = EnemyBuilder(**kwargs).build()
            unit.race = Race.enemy
            unitList.append(unit)
        return unitList
    
    def loadLevels(self) -> None:
        for level in self.levelList:
            with open(f'{self.path}\\{level}', 'r') as f:
                data = json.load(f)
                self.levelData.append(Level(**data))
    
    def nextLevel(self) -> None:
        self.currLevel += 1
        if self.currLevel >= self.totalLevel:
            self.isFinished = True
            self.currLevel = 147
    
    def getCurrLevel(self) -> Level | None:
        if self.currLevel == -1:
            return None
        if self.currLevel >= self.totalLevel:
            return None
        if self.isFinished == True:
            return None
        else:
            return self.levelData[self.currLevel]
    
    def getCurrLevelFinishState(self) -> bool | None:
        if self.isFinished == True:
            return None
        if self.currLevel == -1:
            return None
        if self.currLevel >= self.totalLevel:
            return None
        else:
            return self.levelData[self.currLevel].isFinished
    
    def loadLevel(self) -> Level | None:
        self.nextLevel()
        if self.isFinished == True:
            return None
        if self.currLevel == 147:
            return None
        return self.levelData[self.currLevel]

    def reset(self) -> None:
        """重置关卡进度（回到第一关），供服务器自动重置后重新开局使用。"""
        self.currLevel = -1
        self.isFinished = False
        for level in self.levelData:
            level.reset()

class Game:
    # 自动重置倒计时（帧，gametick=30）：全灭 5 秒、通关 10 秒后回主菜单
    AUTO_RESET_GAME_OVER_DELAY: int = 5 * gametick
    AUTO_RESET_GAME_WIN_DELAY: int = 10 * gametick

    def __init__(self, queue: Queue) -> None:
        self._currState = GameState.mainMenu
        self.levelLoader = LevelLoader()
        self.levelLoader.loadLevels()
        self.levelLoader.createAttr()
        self.waitTime = 0
        self.msgQueue: Queue = queue
        self.board = Board(self.msgQueue)
        self.isPaused = False
        self.pausePlayerId = -1
        self.pausePlayerName = ''
        self.pendingEnemies: list[tuple[Enemy, int]] = []
        # 在线玩家注册表：player_id -> playerName（供自动重置后重生；单人/多人共用）
        self.online_players: dict[int, str] = {}
        self._resetTimer = 0
        self._resetReason = ''
        self._hasStartedGame = False
    
    def setWaitTime(self, time: int) -> None:
        self.waitTime = time
    
    def isWaitTimeOver(self) -> bool:
        if self.waitTime <= 0:
            return True
        else:
            self.waitTime -= 1
            return False
    
    @property
    def currState(self) -> GameState:
        return self._currState
    @currState.setter
    def currState(self, state: GameState) -> None:
        self._currState = state
        self.msgQueue.push(Message('server', 'game_state_changed', {'state': state.value}))
    
    def getObjects(self) -> None:
        objList = self.board.getScreenObjects()
        retDict =  {
            'objects': objList,
            'isPaused': self.isPaused,
            'pausePlayerName': self.pausePlayerName if self.isPaused else '',
        }
        retMsg = Message('server', 'screen_info', retDict)
        self.msgQueue.push(retMsg)
    
    def addFlagUnit(self, flag: Flag) -> None:
        self.currState = GameState.inGame
        self.setWaitTime(flag.timeBeforeNext)
        units = self.levelLoader.createUnits(flag.getUnits())
        while len(flag.drops) > 0:
            unitWithDrop = random.choice(units)
            unitWithDrop.inventory.append(ItemTypes(flag.drops[0]))
            flag.drops.pop(0)
        for unit in units:
            delay = random.randint(0, int(1.5 * gametick))
            self.pendingEnemies.append((unit, delay))

    def _maybeSplitFlag(self, level: Level, flag: Flag) -> Flag:
        if not self.board.players:
            return flag
        avg = sum(p.weapon.getHighestLevel() for p in self.board.players) // len(self.board.players)
        if avg < MIN_WEAPON_LEVEL_THRESHOLD and len(flag.unitTypeList) > MIN_ENEMY_COUNT_THRESHOLD:
            total_nukes = sum(p.magabombQuantity for p in self.board.players)
            nuke_bonus = total_nukes if total_nukes <= 2 else 2 * (total_nukes - 2) + 2
            flag = level.splitFlag(flag, avg, nuke_bonus)
        return flag

    def _processPendingEnemies(self) -> None:
        remaining: list[tuple[Enemy, int]] = []
        for unit, delay in self.pendingEnemies:
            if delay <= 0:
                self.board.addUnit(unit, 'unit')
            else:
                remaining.append((unit, delay - 1))
        self.pendingEnemies = remaining
    
    def detectLevelState(self) -> None:
        if self.isPaused:
            return
        if self.currState == GameState.gameWin:
            # 已通关：等待服务器自动重置（10 秒后回主菜单），不再重复触发关卡加载
            return
        if self.isWaitTimeOver() == False:
            pass
        else:
            self.setWaitTime(random.randint(2, 5) * gametick)
            enemyList = []
            for unit in self.board.units:
                if unit.race == Race.enemy:
                    enemyList.append(unit)
            if len(enemyList) == 0 and len(self.pendingEnemies) == 0:
                if self.currState == GameState.mainMenu:
                    if not self.board.isAllPlayerPrepared() or len(self.board.players) == 0:
                        return
                lState = self.levelLoader.getCurrLevelFinishState()
                if lState == False:
                    level = self.levelLoader.getCurrLevel()
                else:
                    level = self.levelLoader.loadLevel()
                if level == None:
                    self.currState = GameState.gameWin
                    self.msgQueue.push(Message('server', 'set_title', {'title': "You Win!", 'duration': 10 * gametick}))
                elif level.waitLoaded == False:
                    self.setWaitTime(random.randint(10, 20) * gametick)
                    self.currState = GameState.loadLevel
                    self.msgQueue.push(Message('server', 'load_level', {'level': level.name}))
                    self.msgQueue.push(Message('server', 'set_title', {'title': level.name, 'duration': 5 * gametick}))
                    level.waitLoaded = True
                    # 通关复活：死去的玩家在新关卡开始前飞入战场
                    self._revive_dead_players()
                else:
                    flag = level.loadFlag()
                    if flag == None:
                        return
                    else:
                        flag = self._maybeSplitFlag(level, flag)
                        self.addFlagUnit(flag)
            else:
                if len(self.pendingEnemies) > 0:
                    return
                level = self.levelLoader.getCurrLevel()
                if level is None:
                    return
                flag = level.loadFlag()
                if flag is None:
                    return
                elif flag.finishCondition == FlagFinishCondition.waitForTime:
                    flag = self._maybeSplitFlag(level, flag)
                    self.addFlagUnit(flag)
                else:
                    level.currFlagIndex -= 1

    def update(self) -> None:
        self.board.update()
        self._processPendingEnemies()
        self._check_auto_reset()
        self.getObjects()

    def _spawn_player(self, pid: int, playerName: str) -> None:
        """按指定 player_id 重建玩家（重生/加入用），初始化逻辑与 WebSocketServer.new_player 一致。"""
        player = Player(pid)
        player.x = random.randint(0, SCREENSIZE[0])
        player.y = 2/3 * SCREENSIZE[1]
        imageid = pid % 2
        if imageid == 1:
            player.image = Images.player2
        else:
            player.image = Images.player1
        if playerName != "{default}":
            player.name = playerName
        else:
            player.name = str(pid)
        self.board.addPlayer(player)
        # 从屏幕最下方飞入战场（加入/自动重置复活的统一入场动画）
        player.startEntering()

    def _revive_dead_players(self) -> None:
        """通关时复活死去的玩家（在线注册表中不在场上的玩家），飞入战场。"""
        alive_ids = {p.player_id for p in self.board.players}
        for pid, name in self.online_players.items():
            if pid not in alive_ids:
                self._spawn_player(pid, name)

    def _check_auto_reset(self) -> None:
        """自动重置检测（每帧 update 调用，单人/多人共用）：
        - 所有玩家死亡（inGame/loadLevel 中 players 清空）→ 5 秒后回主菜单并重生在线玩家
        - 通关（gameWin）→ 10 秒后执行同样操作
        """
        state = self.currState
        if state == GameState.inGame:
            self._hasStartedGame = True
        elif state == GameState.mainMenu:
            self._hasStartedGame = False
        if self._resetTimer > 0:
            self._resetTimer -= 1
            if self._resetTimer <= 0:
                self._perform_auto_reset()
            return
        if state == GameState.gameWin:
            self._resetTimer = self.AUTO_RESET_GAME_WIN_DELAY
            self._resetReason = 'game_win'
        elif state in (GameState.inGame, GameState.loadLevel) and \
                self._hasStartedGame and len(self.board.players) == 0:
            self._resetTimer = self.AUTO_RESET_GAME_OVER_DELAY
            self._resetReason = 'game_over'

    def _perform_auto_reset(self) -> None:
        """执行自动重置：清场 → 关卡复位 → 重生在线玩家 → 切回主菜单。"""
        print(f"自动重置（{self._resetReason}）：回主菜单并重生 {len(self.online_players)} 名在线玩家")
        # 清场：敌方单位、子弹、待生成敌人
        self.board.units.clear()
        self.board.projectiles.clear()
        self.pendingEnemies.clear()
        # 移除现有玩家（gameWin 时玩家仍存活，需重建为全新状态）
        for p in list(self.board.players):
            self.board.players.remove(p)
        # 关卡复位（回到第一关）
        self.levelLoader.reset()
        # 重生所有在线玩家
        for pid, name in self.online_players.items():
            self._spawn_player(pid, name)
        # 切回主菜单并复位暂停
        self.currState = GameState.mainMenu
        self.isPaused = False
        self.pausePlayerId = -1
        self.pausePlayerName = ''
        self._resetTimer = 0
        self._resetReason = ''
        self._hasStartedGame = False

class WebSocketServer:
    messageQueue: Queue = Queue()

    def __init__(self, host="localhost", port=8765) -> None:
        self.host = host
        self.port = port
        self.clients: set[websockets.ServerConnection] = set()
        self.game = Game(self.messageQueue)
        self.frame_duration = 1.0 / gametick

    async def new_player(self, playerName: str) -> int:
        playerNum = 0
        while self.game.board.findPlayer(playerNum) != None:
            playerNum += 1
        self.game._spawn_player(playerNum, playerName)
        return playerNum

    async def handle_client(self, websocket: websockets.ServerConnection) -> None:
        # 新的客户端连接
        self.clients.add(websocket)
        pid: int = -1
        try:
            async for message in websocket:
                #print(f"收到消息: {message}")
                # 解析消息
                data = eval(message)
                msg = Message(data['sender'], data['type'], data['content'])
                if msg.type == 'connect':
                    if self.game.currState == GameState.mainMenu:
                        pid = await self.new_player(msg.content['playerName'])
                        self.game.online_players[pid] = msg.content['playerName']
                        await websocket.send(str(Message('server', 'connect', {'player_id': pid})))
                    else:
                        await websocket.send(str(Message('server', 'connect', {'player_id': -1})))
                    #await self.broadcast_game_state()
                if msg.type == 'disconnect':
                    raise websockets.ConnectionClosed(None, None)
                if msg.type == 'get':
                    await self.broadcast_game_state()
                if msg.type == 'keyDown':
                    player = self.game.board.findPlayer(int(msg.sender))
                    if player != None:
                        if msg.content['key'] == Keys.p:
                            if not self.game.isPaused:
                                self.game.isPaused = True
                                self.game.pausePlayerId = player.player_id
                                self.game.pausePlayerName = player.name
                            elif self.game.pausePlayerId == player.player_id:
                                self.game.isPaused = False
                                self.game.pausePlayerId = -1
                                self.game.pausePlayerName = ''
                            self.game.getObjects()
                        else:
                            player.pressedKeyList.append(msg.content['key'])
                if msg.type == 'keyUp':
                    player = self.game.board.findPlayer(int(msg.sender))
                    if player != None:
                        key = msg.content['key']
                        if key in player.pressedKeyList:
                            player.pressedKeyList.remove(msg.content['key'])
                if msg.type == 'joyAxis':
                    player = self.game.board.findPlayer(int(msg.sender))
                    if player != None:
                        player.joystickAxisList[msg.content['axis']] = msg.content['value']
                        if abs(msg.content['value']) < 0.2:
                            player.joystickAxisList[msg.content['axis']] = 0
                if msg.type == 'joyHat':
                    player = self.game.board.findPlayer(int(msg.sender))
                    if player != None:
                        if msg.content['value'] == [0, 0]:
                            player.pressedKeyList.remove(Keys.w) if Keys.w in player.pressedKeyList else None
                            player.pressedKeyList.remove(Keys.s) if Keys.s in player.pressedKeyList else None
                            player.pressedKeyList.remove(Keys.a) if Keys.a in player.pressedKeyList else None
                            player.pressedKeyList.remove(Keys.d) if Keys.d in player.pressedKeyList else None
                        else:
                            if msg.content['value'][0] == 1:
                                player.pressedKeyList.append(Keys.d)
                            if msg.content['value'][0] == -1:
                                player.pressedKeyList.append(Keys.a)
                            if msg.content['value'][1] == 1:
                                player.pressedKeyList.append(Keys.w)
                            if msg.content['value'][1] == -1:
                                player.pressedKeyList.append(Keys.s)
                    # if msg.content['key'] == Keys.esc:
                    #     self.game.isPaused = self.game.isPaused ^ True
            else:
                # 对端正常关闭（如浏览器关闭页面，发送 close frame）：websockets 的
                # async for 迭代器会吞掉 ConnectionClosedOK 并正常退出（不抛异常），
                # 因此必须在 else 中移除玩家，否则断连的飞机残留在游戏里
                print(f"客户端连接正常关闭: pid={pid}")
                self._remove_player(pid)
        except websockets.ConnectionClosed as e:
            print(f"客户端断开连接: {e}")
            self._remove_player(pid)
        finally:
            # 移除断开的客户端
            self.clients.remove(websocket)

    def _remove_player(self, pid: int) -> None:
        """按 player_id 从游戏板移除玩家（断连清理）并注销在线注册。"""
        self.game.online_players.pop(pid, None)
        for player in self.game.board.players:
            if player.player_id == pid:
                self.game.board.players.remove(player)
                return
    
    async def Judge(self) -> None:
        while True:
                start_time = time.perf_counter()
                if self.game.isPaused == False:
                    self.game.update()
                else:
                    self.game.getObjects()
                self.game.detectLevelState()
                await self.broadcast_game_state()
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                sleep_time = self.frame_duration - elapsed_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

    async def broadcast_game_state(self) -> None:
        if not self.clients:
            self.messageQueue.clear()
            return
        disconnected_clients: set[websockets.ServerConnection] = set()
        clients = self.clients.copy()
        while self.messageQueue.isEmpty() == False:
            msg = self.messageQueue.pop()
            for client in clients:
                try:
                    await client.send(str(msg))
                except websockets.ConnectionClosed:
                    disconnected_clients.add(client)
        self.clients -= disconnected_clients

    async def start(self) -> None:
        print(f"启动 WebSocket 服务器: ws://{self.host}:{self.port}")
        try:
            hostname = socket.gethostname()
            ipv6_info = socket.getaddrinfo(hostname, None, socket.AF_INET6, socket.SOCK_STREAM)
            if ipv6_info:
                ipv6 = ipv6_info[0][4][0]
                print(f"IPv6 地址: ws://[{ipv6}]:{self.port}")
        except Exception:
            pass
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except (AttributeError, OSError):
                pass
            sock.bind(('::', self.port))
            sock.setblocking(False)
            serve = await websockets.serve(self.handle_client, sock=sock)
            print("已启用 IPv4/IPv6 双栈监听")
        except Exception:
            serve = await websockets.serve(self.handle_client, self.host, self.port)
            print("仅监听 IPv4")
        task = asyncio.create_task(self.Judge())
        await asyncio.gather(serve.wait_closed(), task)

async def main() -> None:
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    try:
        ipv6_info = socket.getaddrinfo(hostname, None, socket.AF_INET6, socket.SOCK_STREAM)
        if ipv6_info:
            ipv6 = ipv6_info[0][4][0]
            print(f"本机 IPv4: {ip}")
            print(f"本机 IPv6: [{ipv6}]")
    except Exception:
        pass
    websocket_server = WebSocketServer(ip, 8000)
    await websocket_server.start()

if __name__ == "__main__":
    asyncio.run(main())