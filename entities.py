import random
import math
from const import *
from abc import ABC, abstractmethod
from sympy import *

class Entity:...
class Projectiles(Entity):...
class Bullet(Projectiles):...
class Unit(Entity):...
class Player(Entity):...

class Entity:
    def __init__(self, **kwargs) -> None:
        self.x: int = kwargs.get('x', 0)
        self.y: int = kwargs.get('y', 0)
        self.id: int = kwargs.get('id', -1)
        self.isDisappeared: bool = False
        self.data: dict = kwargs.get('data', {})
    
    def get(self, key: str):# -> Any:
        return self.data.get(key, None)
    
    def checkDisappear(self) -> None:
        if self.x < disappearAera[0] or self.y < disappearAera[1] or self.x > disappearAera[2] or self.y > disappearAera[3]: self.isDisappeared = True

class Unit(Entity):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if 'data' in kwargs:
            kwargs = kwargs['data']
        self.race = self.get('race')
        self.data['shootCooldown'] = kwargs.get('shootCooldown', 100)
        self.data['shootDuration'] = kwargs.get('shootDuration', 30)
        self.data['lifeTime'] = kwargs.get('lifeTime', 0)
        self.data['moveFunction'] = kwargs.get('moveFunction', 'x=t;y=t')
        self.data['direction'] = kwargs.get('direction', 0)
        self.data['speed'] = kwargs.get('speed', 0)
        self.data['type'] = kwargs.get('type', 0)
        self.data['health'] = kwargs.get('health', 100)
    
    def parseMovementFunction(self) -> None:
        funcLst: list = self.get('moveFunction').split(';')
        tValue = self.get('lifeTime')
        funcx = funcLst[0].replace('x=', '')
        exprx = sympify(funcx).subs('t', tValue).subs('x', self.x).subs('y', self.y)
        self.x = float(exprx.evalf())
        funcy = funcLst[1].replace('y=', '')
        expry = sympify(funcy).subs('t', tValue).subs('x', self.x).subs('y', self.y)
        self.y = float(expry.evalf())
    
    def update(self) -> None:
        self.data['lifeTime'] += self.get('speed')
        self.move()
    
    def move(self) -> None:
        self.parseMovementFunction()
        self.checkDisappear()

class Projectiles(Entity):
    projectilesTypes: dict = {}
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if 'data' in kwargs:
            kwargs = kwargs['data']
        self.data['direction'] = kwargs.get('direction', 0)
        self.data['speed'] = kwargs.get('speed', 0)
        self.data['owner'] = kwargs.get('owner', -1)
        self.data['race'] = kwargs.get('race', raceList[0])
        self.data['type'] = kwargs.get('type', 'bullet')
        self.data['damage'] = kwargs.get('damage', 0)
        self.data['acceleration'] = kwargs.get('acceleration', [0, 0]) #[ value, direction ]
    
    @abstractmethod
    def update(self, *args) -> None:
        ...
    
    def on_hit(self, *args) -> None:
        for i in args:
            if i.id == self.get('owner'):
                pass
            else:
                i.data['health'] -= self.get('damage')
                self.isDisappeared = True
    
    @classmethod
    def create(cls, projectileObject: Projectiles) -> Projectiles:
        projectile = cls.projectilesTypes[projectileObject.get('type')]()
        projectile.x = projectileObject.x
        projectile.y = projectileObject.y
        projectile.id = projectileObject.id
        projectile.data = projectileObject.data
        return projectile

class Bullet(Projectiles):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        #data: {speed, direction, owner, race, type, damage}
        self.data['type'] = 'bullet'
    
    def update(self, *args) -> None:
        self.checkDisappear()
        self.move()
    
    def move(self) -> None:
        self.x += self.get('speed') * math.cos(self.get('direction'))
        self.y += self.get('speed') * math.sin(self.get('direction'))

class Missile(Projectiles):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        #data: {speed, direction, acceleration, owner, race, type, damage}
        self.data['type'] = 'missile'
        self.data['target'] = kwargs.get('target', -1)
    
    def move(self) -> None:
        self.x += self.get('speed') * math.cos(self.get('direction'))
        self.y += self.get('speed') * math.sin(self.get('direction'))
    
    def accelerate(self) -> None:
        v0 = Vector(self.get('speed'), self.get('direction'))
        a0 = Vector(self.get('acceleration')[0], self.get('acceleration')[1])
        vt = v0 + a0
        self.data['speed'] = vt.magnitude
        self.data['direction'] = vt.angle
    
    def faceto(self, target: Entity) -> None:
        if target == None:
            return
        self.data['acceleration'][1] = math.atan2(target.y - self.y, target.x - self.x)
    
    def update(self, *args) -> None:
        self.checkDisappear()
        self.faceto(args[0])
        self.accelerate()
        self.move()

class Player(Entity):
    def __init__(self, ID: int = -1, **kwargs) -> None:
        super().__init__(**kwargs)
        if 'data' in kwargs:
            kwargs = kwargs['data']
        if ID != -1:
            self.id = ID
        self.data['shootDuration'] = kwargs.get('shootDuration', 20)
        self.data['shootCooldown'] = kwargs.get('shootCooldown', 20)
        if self.id == -1:
            self.id = kwargs.get('id', -1)
            self.x = kwargs.get('x', 0)
            self.y = kwargs.get('y', 0)
            self.data = kwargs.get('data', {"shootDuration": 20, "shootCooldown": 20})
    
    def move(self, direction: int, distance: int) -> tuple:
        # TODO direction: angle
        self.x += distance * math.cos(direction)
        self.y += distance * math.sin(direction)
        if self.x < 0:
            self.x = 0
        if self.y < 0:
            self.y = 0
        if self.x > SCREENSIZE[0]:
            self.x = SCREENSIZE[0]
        if self.y > SCREENSIZE[1]:
            self.y = SCREENSIZE[1]
        return (self.x, self.y)

Projectiles.projectilesTypes = {'bullet': Bullet, 'missile': Missile}
