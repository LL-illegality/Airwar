class Weapon:
    def __init__(self) -> None:
        pass
    
    @classmethod
    def weapon(cls, func):
        def wrapper(*args, **kwargs) -> None:
            print(f"Weapon {args[0].weaponType} shoot")
            func(*args, **kwargs)
        return wrapper

class Unit:
    def __init__(self, weaponType) -> None:
        self.weaponType = weaponType

    @Weapon.weapon
    def shoot(self) -> None:
        print("Unit shoot")

a = Unit("gun")
a.shoot()  # 输出: Weapon gun shoot

class Projectiles:...
class bullets(Projectiles):...

class Projectiles:
    projectilesType: dict = {'bullet': bullets}
    def __init__(self, type = None) -> None:
        self.data = {}
        if type != None:
            self = self.loadProjectileType(type)
    
    def loadProjectileType(self, type)-> bullets:
        r = self.projectilesType[type]()
        return r

class bullets(Projectiles):
    def __init__(self) -> None:
        super().__init__()
        self.data = {"bullet": 100}

pro = Projectiles(type='bullet')
print(pro.data)  # 输出: {'bullet': 100


