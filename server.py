import asyncio
import websockets
import os
from const import *
from data import Vector, Message, Queue
import random
import json 
import socket
import time
import math

def createInstanceFromClassname(classname: str, kwargs: dict) -> object:
    return globals()[classname](**kwargs)

class Point:
    def __init__(self, x = 0, y = 0) -> None:
        self.x = x
        self.y = y
    
    def getDirection(self, other: "Point") -> Vector:
        return Vector(other.x - self.x, other.y - self.y)

class BoundingBox:
    def __init__(self, width, height) -> None:
        self.width = width
        self.height = height
    
    def getRect(self, x, y) -> tuple[Point, Point]:
        luPoint = Point(x - (self.width/2), y - (self.height/2))
        rdPoint = Point(x + (self.width/2), y + (self.height/2))
        return (luPoint, rdPoint)

class Entity:
    def __init__(self, x = 0, y = 0, id = -1) -> None:
        self.x = x
        self.y = y
        self.id = id
        self.image: Images = None
        self.boundingBox: BoundingBox = None
        self.velocity = Vector(0, 0)
        self.acceleration = Vector(0, 0)
        self.rotation = 0
        self.maxVelocity = None
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
    
    def __eq__(self, other: "Entity") -> bool:
        if other is None:
            return False
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
    def __init__(self, item: ItemTypes):
        super().__init__()
        self.item = item
        self.image = itemMap[item]
        self.lifetime = 30 * gametick
        self.boundingBox = BoundingBox(24, 24)
        self.velocity = Vector(random.randint(-10, 10), random.randint(-10, 10))
        self.velocityMultiplier = 1
        self.redirectionDelay = 0
    
    def update(self) -> None:
        super().update()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.isAlive = False
        if self.redirectionDelay >= 0:
            if self.x <= 0 or self.x >= SCREENSIZE[0]:
                self.velocity.x *= -1
                self.redirectionDelay = 10
            if self.y <= 0 or self.y >= SCREENSIZE[1]:
                self.velocity.y *= -1
                self.redirectionDelay = 10
        else:
            self.redirectionDelay -= 1
    
    def onCollision(self, other: Entity) -> None:
        if other.race == Race.player:
            other.gottenItem.append(self.item)
            self.isAlive = False

class Projectile(Entity):
    def __init__(self, damage = 10, lifetime = 1000):
        super().__init__()
        self.damage = damage
        self.lifetime = lifetime
        self.shooterRace = Race.neutral
        self.boundingBox = BoundingBox(3, 8)
        self.chooseTarget = False
        self.velocityMultiplier = 1
    
    def update(self) -> None:
        super().update()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.isAlive = False
        self.rotation = ~self.velocity
    
    def onCollision(self, other):
        if other.race != self.shooterRace and other.race != Race.neutral:
            other.health -= self.damage
            self.isAlive = False

class Bullet(Projectile):
    def __init__(self, damage = 5, lifetime = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.bullet1
        self.boundingBox = BoundingBox(3, 8)
        self.velocity = Vector(0, -10)
    
    def onCollision(self, other):
        super().onCollision(other)

class Lazer(Projectile):
    def __init__(self, damage = 1.5, lifetime = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.lazer1
        self.boundingBox = BoundingBox(3, 8)
        self.velocity = Vector(0, -15)

class Missile(Projectile):
    def __init__(self, damage = 4, handedness = 1, lifetime = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.missile
        self.handedness = handedness
        self.boundingBox = BoundingBox(12, 16)
        self.velocity = Vector(1 * self.handedness, -4)
        self.target: Entity = None
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
    def __init__(self, damage = 10, handedness = 1, lifetime = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.rocket
        self.handedness = handedness
        self.boundingBox = BoundingBox(8, 16)
        self.velocity = Vector(1 * self.handedness, -4)
        self.acceleration = Vector(0, -0.7)

class EnergyBall(Projectile):
    def __init__(self, damage = 12, lifetime = 150) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.energyball
        self.chooseTarget = True
        self.boundingBox = BoundingBox(8, 8)
        self.velocity = Vector(0, 4)

class Magabomb(Projectile):
    def __init__(self, damage = 10, lifetime = 2147483647) -> None:
        super().__init__(damage, lifetime)
        self.image = Images.magabomb
        self.explodePos = (SCREENSIZE[0] / 2, SCREENSIZE[1] / 2)
        self.boundingBox = None
        self.velocity = Vector(0, 10)
    
    def onCollision(self, other):
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
    def __init__(self, bullet: Projectile, fireRate: int = 10, shooterRace: Race = Race.neutral) -> None:
        self.bullet = bullet
        self.fireRate = fireRate
        self.cooldown = 0
        self.level = 1
        self.maxLevel = 5
        self.shooterRace = shooterRace
        self.sound = Sounds.shotgun_shoot
        self.playSound = True
        self.isShooting = False
    
    def shoot(self, x, y, times: int = 1) -> list[Projectile] | None:
        if self.isShooting and self.cooldown <= 0:
            retList: list[Projectile] = []
            for _ in range(times):
                bullet = type(self.bullet)()
                bullet.shooterRace = self.shooterRace
                bullet.x = x
                bullet.y = y
                retList.append(bullet)
            self.cooldown = self.fireRate
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
    
    @property
    def isShooting(self) -> bool:
        return self.isShooting_

    @isShooting.setter
    def isShooting(self, value: bool) -> None:
        self.isShooting_ = value
        for weapon in self.weapons:
            weapon.isShooting = value
    
    def shoot(self, x, y) -> list[Projectile]:
        retList = []
        for weapon in self.weapons:
            proj = weapon.shoot(x, y)
            if type(proj) == list:
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

class Shotgun(Weapon):
    bulletSpreadMap = {
        1: [0],
        2: [-2, 2],
        3: [(-3, 0), 0, (3, 0)],
        4: [(-3, 0), -2, 2, (3, 0)],
        5: [(-5, 0), (-2, 0), 0, (2, 0), (5, 0)],
    }
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Bullet(), 5, shooterRace)
        self.sound = Sounds.shotgun_shoot
    
    def shoot(self, x, y) -> list[Projectile] | None:
        projs = super().shoot(x, y, self.level)
        if projs is not None:
            for i in range(len(projs)):
                proj = projs[i]
                spreadList = self.bulletSpreadMap[self.level]
                if type(spreadList[i]) == tuple:
                    proj.velocity += Vector(*spreadList[i])
                if type(spreadList[i]) == int:
                    proj.x += spreadList[i]
                if self.shooterRace == Race.enemy:
                    proj.chooseTarget = True
                    proj.image = Images.bullet_enemy
        return projs

class LazerGun(Weapon):
    bulletImageMap = {
        1: Images.lazer1,
        2: Images.lazer2,
        3: Images.lazer3,
        4: Images.lazer4,
        5: Images.lazer5
    }
    bulletDamageMap = {
        1: 1.5,
        2: 4.5,
        3: 7.5,
        4: 12,
        5: 13.5
    }
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Lazer(), 1.5, shooterRace)
        self.sound = Sounds.lazer_shoot
    
    def shoot(self, x, y) -> list[Projectile] | None:
        projs = super().shoot(x, y)
        if random.randint(0, 100) < 20:
            projs = None
            self.playSound = False
        if projs is not None:
            proj = projs[0]
            proj.image = self.bulletImageMap[self.level]
            proj.damage = self.bulletDamageMap[self.level]
            proj.boundingBox = BoundingBox(3 * (proj.damage / 1.5), 15)
            if self.shooterRace == Race.enemy:
                proj.velocity.y = -proj.velocity.y
        return projs
    
class MissileLauncher(Weapon):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(Missile(), 15, shooterRace)
        self.handedness = 1
        self.level = 0
        self.maxLevel = 0
        self.sound = Sounds.missile_shoot

    def shoot(self, x, y) -> list[Projectile] | None:
        if self.isShooting and self.cooldown <= 0:
            Board.msgQueue.push(Message('server', 'playsound', {"sound": self.sound.value}))
            missileL = type(self.bullet)()
            missileR = type(self.bullet)(handedness = -1)
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

class RocketLauncher(MissileLauncher):
    def __init__(self, shooterRace: Race) -> None:
        super().__init__(shooterRace)
        self.bullet = Rocket()
        self.sound = Sounds.rocket_shoot
    
    def shoot(self, x, y) -> list[Projectile] | None:
        return super().shoot(x, y)

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

class Unit(Entity):
    def __init__(self, x = 0, y = 0, health = 100, width = 100, height = 50) -> None:
        super().__init__(x, y)
        self.health = health
        self.weapon: WeaponGroup = None
        self.boundingBox = BoundingBox(width, height)
        self.inventory: list[ItemTypes] = []
    
    def update(self) -> None:
        super().update()
        if self.health <= 0:
            self.isAlive = False
        if self.weapon is not None:
            self.weapon.update()

class Enemy(Unit):
    def __inti__(self) -> None:
        super().__init__()
        self.race = Race.enemy
        self.weapon = None
        self.targetPos: list[int] = None
    
    def randomTargetPos(self) -> None:
        self.targetPos = [random.randint(0, SCREENSIZE[0]), random.randint(0, SCREENSIZE[1])]
        self.acceleration = Vector(0, random.randint(-10, 10) / 10)
    
    def update(self) -> None:
        super().update()
        self.rotation = ~self.velocity
        if self.weapon is not None:
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
    def __init__(self, player_id) -> None:
        super().__init__()
        self.player_id = player_id
        self.name = self.player_id
        self.race = Race.player
        self.pressedKeyList = []
        self.joystickAxisList = [0, 0]
        self.gottenItem: list[ItemTypes] = []
        self.magabombQuantity = 1
        self.isReady = False
        self.isThrowingMagabomb = False
        self.boundingBox = BoundingBox(16, 32)
        self.weapon = WeaponGroup(Shotgun(self.race))
        self.maxVelocity = 15
    
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
        for item in self.gottenItem:
            Board.msgQueue.push(Message("server", 'playsound', {"sound": "itemget"}))
            if item == ItemTypes.missile:
                self.weapon.addWeapon(MissileLauncher(self.race))
                self.weapon.removeAll(RocketLauncher)
            if item == ItemTypes.rocket:
                self.weapon.addWeapon(RocketLauncher(self.race))
                self.weapon.removeAll(MissileLauncher)
            if item == ItemTypes.shotgun:
                if self.weapon.has(Shotgun) == False:
                    self.weapon.removeAll(LazerGun)
                    self.weapon.addWeapon(Shotgun(self.race))
                else:
                    self.weapon.upgrade(Shotgun)
            if item == ItemTypes.lazer:
                if self.weapon.has(LazerGun) == False:
                    self.weapon.removeAll(Shotgun)
                    self.weapon.addWeapon(LazerGun(self.race))
                else:
                    self.weapon.upgrade(LazerGun)
            if item == ItemTypes.super:
                for _ in range(5):
                    self.weapon.upgrade(LazerGun)
                    self.weapon.upgrade(Shotgun)
            if item == ItemTypes.magabomb:
                self.magabombQuantity += 1
                self.gottenItem.remove(item)
            if item == ItemTypes.medic:
                self.health = 100
                self.gottenItem.remove(item)
            self.inventory.append(item)
        self.gottenItem.clear()
        if self.weapon is not None:
            if Keys.space in self.pressedKeyList:
                self.weapon.isShooting = True
            else:
                if self.weapon.isShooting == True:
                    self.weapon.isShooting = False

class EnemyBuilder:
    def __init__(self,
                 health = 100,
                 image = 'en',
                 weapon = None,
                 velocity = Vector(0, 0),
                 acceleration = Vector(0, 0),
                 boundingBox = None,
                 targetPos = None,
                 maxVelocity = None,
                 velocityMultiplier = 0.9,
                 inventory: list[int] = []
                 ) -> None:
        self.enemy = Enemy()
        self.enemy.maxVelocity = maxVelocity
        self.enemy.velocityMultiplier = velocityMultiplier
        self.enemy.health = health
        self.enemy.image = Images(image)
        self.enemy.velocity = velocity
        self.enemy.targetPos = targetPos
        self.enemy.acceleration = acceleration
        self.enemy.boundingBox = boundingBox
        self.enemy.inventory = [ItemTypes(item) for item in inventory]
        self.enemy.weapon = WeaponGroup(*[createInstanceFromClassname(weapon[i], {'shooterRace': Race.enemy}) for i in range(len(weapon))]) if weapon is not None else None
    
    def build(self) -> Enemy:
        return self.enemy

class Board:
    msgQueue: Queue = Queue()
    def __init__(self, msgQueue: Queue) -> None:
        self.players: list[Player] = []
        self.units: list[Unit] = []
        self.projectiles: list[Projectile] = []
        self.objects: list[list[Player] | list[Unit] | list[Projectile]] = [self.players, self.units, self.projectiles]
        Board.msgQueue = msgQueue
        self.currId = -1
    
    def increaseId(self) -> None:
        self.currId += 1
    
    def nearestPlayer(self, x, y) -> Player:
        if len(self.players) == 0:
            return None
        return min(self.players, key=lambda p: (p.x - x)**2 + (p.y - y)**2)
    
    def nearestUnit(self, x, y, race: Race) -> Unit:
        unitList = []
        for unit in self.units:
            if unit.race == race:
                unitList.append(unit)
        if len(unitList) == 0:
            return None
        return min(unitList, key=lambda u: (u.x - x)**2 + (u.y - y)**2)

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
            unit.x = random.randint(0, SCREENSIZE[0])
            self.units.append(unit)
            self.increaseId()
            unit.id = self.currId
        elif type == 'projectile':
            self.projectiles.append(unit)
            self.increaseId()
            unit.id = self.currId
    
    def getScreenObjects(self) -> list:
        retList = []
        for obj in self.objects:
            for item in obj:
                appDict = {
                    'id': item.id,
                    'x': item.x,
                    'y': item.y,
                    'rotation': item.rotation,
                    'image': item.image.value,
                    } 
                if type(item) == Player:
                    appDict['health'] = item.health
                    appDict['isReady'] = item.isReady
                    appDict['player_id'] = item.player_id
                    appDict['name'] = item.name
                    appDict['magabombQuantity'] = item.magabombQuantity
                retList.append(appDict)
        return retList
    
    def isAllPlayerPrepared(self) -> bool:
        return all(player.isReady for player in self.players)

    def checkCollision(self, item: Entity) -> None:
        for obj in self.objects:
            for other in obj:
                if item != other and item & other:
                    item.onCollision(other)
    
    def generateSoundMessage(self, sound: Sounds | str):
        if type(sound) == Sounds:
            sound = sound.value
        return Message('server', 'playsound', {"sound": sound})
    
    def update(self) -> None:
        for obj in self.objects:
            for item in obj:
                item.update()
                if item.x < disappearAera[0] or\
                   item.x > disappearAera[2] or\
                   item.y < disappearAera[1] or\
                   item.y > disappearAera[3]:
                    item.isAlive = False
                if hasattr(item, 'isExploding') and item.isExploding:
                    for i in self.units:
                        i.isAlive = False
                    for i in self.projectiles:
                        i.isAlive = False
                    self.projectiles.remove(item)
                    self.msgQueue.push(self.generateSoundMessage(Sounds.nuclear_missile_explode))
                    break
                if hasattr(item, 'weapon') and item.weapon is not None:
                    if item.weapon.isShooting:
                        bullets = item.weapon.shoot(item.x, item.y)
                        for bullet in bullets:
                            if bullet is not None:
                                if bullet.chooseTarget == True:
                                    if bullet.shooterRace == Race.enemy:
                                        target = self.nearestPlayer(bullet.x, bullet.y)
                                        if target is not None:
                                            bullet.faceToTarget(target, 'velocity')
                                            bullet.chooseTarget = False
                                    else:
                                        bullet.chooseTarget = False
                                if hasattr(bullet, 'target'):
                                    if bullet.shooterRace == Race.enemy:
                                        bullet.target = self.nearestPlayer(bullet.x, bullet.y)
                                    else:
                                        race = Race.enemy
                                        bullet.target = self.nearestUnit(bullet.x, bullet.y, race)
                                self.addUnit(bullet, 'projectile')
                if hasattr(item, 'isThrowingMagabomb') and item.isThrowingMagabomb == True:
                    item.isThrowingMagabomb = False
                    magabomb = Magabomb()
                    magabomb.x = item.x
                    magabomb.y = item.y
                    self.addUnit(magabomb, 'projectile')
                    self.msgQueue.push(self.generateSoundMessage(Sounds.nuclear_missile_shoot))
                self.checkCollision(item)
                if item.isAlive == False:
                    if hasattr(item, 'inventory'):
                        for itemType in item.inventory:
                            itemUnit = Item(itemType)
                            itemUnit.x = item.x
                            itemUnit.y = item.y
                            self.addUnit(itemUnit, 'unit')
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
        self.flags: list[Flag] = [None for _ in range(totalFlags)]
        for i in range(len(self.flags)):
            self.flags[i] = Flag(**flags[i])
        for item in drops:
            flag = random.choice(self.flags)
            flag.drops.append(item)
    
    def nextFlag(self) -> None:
        self.currFlagIndex += 1
        if self.currFlagIndex >= self.totalFlags:
            self.isFinished = True
            return
        self.flags[self.currFlagIndex].isFinished = False
    
    def getCurrFlag(self) -> Flag:
        if self.currFlagIndex == -1 or self.currFlagIndex >= self.totalFlags:
            return None
        else:
            return self.flags[self.currFlagIndex]
    
    def loadFlag(self) -> Flag | None:
        self.nextFlag()
        if self.isFinished == True:
            return None
        return self.flags[self.currFlagIndex]

class LevelLoader:
    def __init__(self, path = '.\\levels') -> None:
        self.currLevel = -1
        self.path = path
        self.levelList = os.listdir(path)
        self.totalLevel = len(self.levelList)
        self.isFinished = False
        self.levelData: list[Level] = []
        self.standardTypeList = configuration.enemyTypes.copy()
    
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
    
    def getCurrLevel(self) -> Level:
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
    
    def loadLevel(self) -> Level:
        self.nextLevel()
        if self.isFinished == True:
            return None
        if self.currLevel == 147:
            return 
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
            self.board.addUnit(unit, 'unit')
    
    def detectLevelState(self) -> None:
        if self.isWaitTimeOver() == False:
            pass
        else:
            self.setWaitTime(2 * gametick)
            enemyList = []
            for unit in self.board.units:
                if unit.race == Race.enemy:
                    enemyList.append(unit)
            if len(enemyList) == 0:
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
                    self.setWaitTime(random.randint(5, 15) * gametick)
                    self.currState = GameState.loadLevel
                    self.msgQueue.push(Message('server', 'load_level', {'level': level.name}))
                    self.msgQueue.push(Message('server', 'set_title', {'title': level.name, 'duration': 5 * gametick}))
                    level.waitLoaded = True
                else:
                    flag = level.loadFlag()
                    if flag == None:
                        return
                    else:
                        self.addFlagUnit(flag)
            else:
                level = self.levelLoader.getCurrLevel()
                flag = level.loadFlag()
                if flag == None:
                    return
                elif flag.finishCondition == FlagFinishCondition.waitForTime:
                    self.addFlagUnit(flag)
                else:
                    level.currFlagIndex -= 1

    def update(self) -> None:
        self.board.update()
        self.getObjects()

class WebSocketServer:
    messageQueue: Queue = Queue()
    def __init__(self, host="localhost", port=8765) -> None:
        self.host = host
        self.port = port
        self.clients: set[websockets.ClientConnection] = set()  # 存储所有连接的客户端
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

    async def handle_client(self, websocket: websockets.ClientConnection) -> None:
        # 新的客户端连接
        self.clients.add(websocket)
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
                self.game.detectLevelState()
                asyncio.gather(self.broadcast_game_state())
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                sleep_time = self.frame_duration - elapsed_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

    async def broadcast_game_state(self) -> None:
        """向所有连接的客户端广播游戏状态"""
        if not self.clients:
            print("没有客户端连接，无法发送消息")
            self.messageQueue.clear()
            return
        disconnected_clients = set()
        clients = self.clients.copy()
        while self.messageQueue.isEmpty() == False:
            msg = self.messageQueue.pop()
            for client in clients:
                try:
                    await client.send(str(msg))
                except websockets.ConnectionClosed:
                    disconnected_clients.add(client)
        #self.messageQueue.pop() if self.messageQueue.isEmpty() == False else None
        # 清理已断开的客户端
        self.clients -= disconnected_clients

    async def start(self) -> None:
        print(f"启动 WebSocket 服务器: ws://{self.host}:{self.port}")
        serve = await websockets.serve(self.handle_client, self.host, self.port)
        task = asyncio.create_task(self.Judge())
        await asyncio.gather(serve.wait_closed(), task)

async def main() -> None:
    # 创建 WebSocket 服务器实例
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    websocket_server = WebSocketServer(ip, 8000)
    await websocket_server.start()

if __name__ == "__main__":
    asyncio.run(main())