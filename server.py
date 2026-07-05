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

def createInstanceFromClassname(classname: str, kwargs: dict) -> object:
    return globals()[classname](**kwargs)

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
    
    def update(self) -> None:
        for weapon in self.weapons:
            weapon.update()

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
    
    def randomTargetPos(self) -> None:
        self.targetPos = [random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1])]
        self.acceleration = Vector(0, random.randint(-10, 10) / 10)
    
    def update(self) -> None:
        super().update()
        self.rotation = ~self.velocity
        self.weapon.isShooting = True
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
    
    def update(self) -> None:
        super().update()
        if Keys.c in self.pressedKeyList:
            self.isReady = True
        else:
            if self.isReady == True:
                self.isReady = False
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
                 inventory: list[int] | None = None
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
        self.enemy.weapon = WeaponGroup(*[createInstanceFromClassname(weapon[i], {'shooterRace': Race.enemy}) for i in range(len(weapon))]) if weapon is not None else WeaponGroup()
    
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
        for item in drops:
            flag = random.choice(self.flags)
            flag.drops.append(item)
    
    def nextFlag(self) -> None:
        self.currFlagIndex += 1
        if self.currFlagIndex >= self.totalFlags:
            self.isFinished = True
            return
        self.flags[self.currFlagIndex].isFinished = False
    
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

class Game:
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
        self.getObjects()

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
        player = Player(playerNum)
        player.x = random.randint(0, SCREENSIZE[0])
        player.y = 2/3 * SCREENSIZE[1]
        imageid = player.player_id % 2
        if imageid == 1:
            player.image = Images.player2
        else:
            player.image = Images.player1
        if playerName != "{default}":
            player.name = playerName
        else:
            player.name = str(player.player_id)
        self.game.board.addPlayer(player)
        return player.player_id

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
        except websockets.ConnectionClosed as e:
            print(f"客户端断开连接: {e}")
            for player in self.game.board.players:
                    if player.player_id == pid:
                        self.game.board.players.remove(player)
        finally:
            # 移除断开的客户端
            self.clients.remove(websocket)
    
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