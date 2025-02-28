# **Airwar**
Airwar是一款基于python开发的多人联机闯关游戏，在游戏中玩家可以操纵自己的飞机通过击败敌人升级自身并通过关卡

## 新手教程

Airwar有新手教程系统，可以帮助第一次游玩的玩家快速适应该游戏的操作方式，教程中提及移动，发射，击杀敌人等等基础操作，也有升级武器，使用特殊攻击的高级操作

启动`Airwar.exe`即打开客户端，并在弹出的窗口中选择`single player`即可进入新手教程

## 多人游戏

Airwar采用python的`websockets`和`asyncio`库实现客户端和服务端的连接，游戏中所有的计算都是在服务端中进行，而客户端则负责绘图播放声音和监听按键事件等等

要开始多人游戏，须先启动`server.exe`并在其终端中查找输出的服务端启动时的ip地址和端口号，然后在启动客户端（`Airwar.exe`），在客户端弹出的窗口中输入服务端的ip地址和端口号，再点击`multi player`按钮即可加入指定的服务器开启多人游玩

## 游戏内按键操作

**在游戏中切换到英文输入法才能流畅使用按键*

- w: 使玩家向前移动
- s: 使玩家向后移动
- a: 使玩家向左移动
- d: 使玩家向右移动
- c: 长按进入准备状态
- z: 在自身下方绘制标记
- e: 使用核弹
- space: 发射子弹

## 游戏详情简介

### 玩家

- 玩家的飞机拥有红蓝两种颜色，这不仅丰富了玩家游玩时的色彩丰富度，也能够在实际中最常见的双人游玩场景中区分其他玩家和自身。飞机颜色取决于玩家加入游戏的顺序
- 屏幕下方是玩家的状态栏，里面描述了当前操作者所操作的玩家的玩家id，血量状态以及持有的核弹数量等等
- 当玩家血量降低至0时，玩家将死亡且其状态栏将隐藏，并且无法复活；玩家持有的物品道具也将掉落并可被其他玩家捡起，但依然可观战场地内的其他玩家

### 敌人

- 敌人会出现在关卡中随机游走并向玩家发动攻击
- 当敌人死亡时可能会掉落道具，这些道具能被玩家捡起并给予一定的增益

### 物品道具

- 击杀敌人时可能掉落，会在场地中弹跳并且无视敌人或弹射物，只能被玩家拾取或者消失
- 道具在一定时间后如果未被拾取则会消失
- 玩家在捡起不同类型的道具后会获得不同类型的增益：
  - 升级武器：捡起与武器类型相同的道具；武器有五个等级，等级越高对应的武器强度也会越大
  - 更换武器：捡起与武器类型不同的道具；会清空当前武器并装备新武器
  - 增加副武器：捡起导弹和火箭可以将其添加到副武器，不会清空原有的武器
  - 回复血量：捡起血包时会将玩家血量恢复至最大值
  - 增加核弹持有数量：捡起核弹时会增加玩家持有的核弹数量，核弹会在按下e键释放时消耗

### 关卡系统

游戏中利用数据驱动的方式构建了轻量高效的关卡系统，在游戏文件夹的`levels`文件夹中存放着`json`格式的关卡文件，玩家可以自己编写关卡并加载到游戏中，关卡加载的顺序是通过`os.listdir(".\\levels\\")`的顺序决定的，通常为名称顺序

关卡中的敌人是由`configs`中的`enemyTypes.json`定义的，该文件定义了每种敌人的属性

编写关卡Demo：

```json
{
    "name": "level0",//关卡名
    "totalFlags": 5,//关卡总波数
    "drops": [//关卡内的敌人的掉落物
        0,
        1,
        6,
        2,
        4
    ],
    "flags": [//定义 波，列表内长度要与totalFlags相同
        {
            "unitTypeList": [//敌人列表
                "enemy2"//敌人
            ],
            "timeBeforeNext": 300,
            "finishCondition": 0
        },
        {
            "unitTypeList": [
                "enemy2",
                "en"
            ],
            "timeBeforeNext": 300,
            "finishCondition": 0
        },
        {
            "unitTypeList": [
                "Laser shooter",
                "test",
                "test"
            ],
            "timeBeforeNext": 300,
            "finishCondition": 0
        },
        {
            "unitTypeList": [
                "Laser shooter",
                "en",
                "test"
            ],
            "timeBeforeNext": 300,
            "finishCondition": 0
        },
        {
            "unitTypeList": [
                "Laser shooter",
                "enemy2",
                "enemy2",
                "enemy2",
                "en"
            ],
            "timeBeforeNext": 300,
            "finishCondition": 0
        }
    ]
}
```

编写敌人种类Demo:

```json
{
    "en": {//敌人类名，被用于填到关卡中
        "health": 100,//血量
        "image": "en",//图片
        "weapon": ["Shotgun_normal"],//武器列表，填写武器类名，可以多个
        "velocity": {//敌人的初始速度，单位像素/游戏刻
            "x": 0,
            "y": 15
        },
        "acceleration": {//敌人的初始加速度，单位像素/游戏刻²
            "x": 0,
            "y": 1
        },
        "maxVelocity": 15,//敌人的最大速度大小
        "velocityMultiplier": 0.9,//空气阻力系数，小于1则敌人会逐渐减速至静止，等于1则会匀速飞行，大于1则会逐渐加速
        "boundingBox": {//敌人的碰撞想，单位像素
            "width": 56,
            "height": 56
        },
        "targetPos": [400, 300]//敌人的目标点坐标，敌人会飞行至目标点,
        "inventory": [0, 1]//敌人的物品栏，其中物品在死亡时会掉落，列表中每一项的值对应物品道具的类型
    }
}
```

## 开发者相关

### 配置文件的数据驱动

配置文件是通过`Configuration`类实现读取的，`Configuration`类会读取`.\\configs`目录下的所有文件并将其文件名（不包括后缀）作为该类的属性添加到内存中

假设有配置文件`setting.json`并需要从其中读取出`key`的值，则在代码中需要写`configuration.setting["key"]`

```python
class Configuration:
    def __init__(self) -> None:
        cfgFiles = os.listdir(".\\configs")
        for cfg in cfgFiles:
            if cfg.endswith(".json"):
                with open(f".\\configs\\{cfg}", "r") as f:
                    self.__dict__[cfg[:-5]] = json.load(f)
configuration = Configuration() #全局的configuration
```

### 关卡属性（`Level`）

编写关卡文件时需要在其文件中填入关卡属性，程序将会根据填入的属性构建对应的关卡以加载到游戏中游玩，若属性不正确或未填入属性则可能导致关卡加载失败或程序崩溃

- `name: str`：关卡名称，加载关卡时会显示在屏幕中间
- `totalFlags: int`：关卡的波数，规定了有多少波敌人会出现在该关卡中，应与`flags`的长度保持一致
- `flags: list[dict]`：定义每一波的敌人，其长度应与`totalFlags`的值保持一致
- `drops: list[int]`：定义关卡中将会掉落的道具，每一项对应一个道具，该项的值为道具类型的枚举

### 波属性（`Flag`）

波中存储了该波的敌人信息，下一波到来的时间等，应被写入`Level`的`flags`中

- `unitTypeList: list[str]`：存储该波中出现的敌人，每一项对应一个敌人种类
- `timeBeforeNext: int`：下一波到来的时间，与`finishCondition`有关，若`finishCondition = 0`则当`timeBeforeNext = 0`时加载下一波；若`finishCondition = 1`则当`timeBeforeNext = 0`且屏幕上无敌人时才加载下一波
- `finishCondition: int`：波完成条件，是枚举值

### 敌人种类构建（`EnemyBuilder`）

该类可实现将`json`文本实例化成类以便加载到关卡中，所有参数都是可选参数，可以不填以保持其默认值

- `health: int = 100`：定义敌人血量
- `image: str = 'en'`：定义敌人图片，是枚举(图片的无后缀文件名)
- `weapon: list[str] = None`：定义敌人拥有的武器，每一项为一个武器，该项的值为武器的类名
- `velocity: dict[str, int] = {0, 0}`：敌人的初始速度，是二维向量，有`x`和`y`两个属性
- `acceleration: dict[str, int] = {0, 0}`：敌人的初始加速度，是二维向量，有`x`和`y`两个属性
- `boundingBox: dict[str, int] = None`：定义碰撞箱子，有`width`和`height`两个属性
- `targetPos: list[int] = None`：敌人的目标点，会使敌人飞到该点的坐标，应输入两个整形数值表示坐标`x`和`y`
- `maxVelocity: int = None`：定义敌人的最大速度
- `velocityMultiplier: float = 0.9`：定义敌人的阻力系数，每一个游戏刻敌人的移动速度都会乘上这个系数
- `inventory: list[int] = []`定义敌人的物品栏，每一项为一个道具，每一项的值为道具类型的枚举

### 波完成条件枚举（`FlagFinishCondition`）

```python
class FlagFinishCondition(Enum):
    waitForTime = 0 #等待时间结束就加载下一波
    killAll = 1 #当杀死所有敌人且等待时间结束才加载下一波
```

### 道具种类枚举（`ItemTypes`）

```python
class ItemTypes(Enum):
    shotgun = 0 #散弹枪：升级或将当前武器更换为散弹枪
    lazer = 1 #激光：升级或将当前武器更换为激光
    missile = 2 #导弹：添加导弹发射器并舍弃火箭发射器
    super = 3 #超级：将当前武器升至满级
    rocket = 4 #火箭：添加火箭发射器并舍弃导弹发射器
    magabomb = 5 #核弹：增加核弹持有数量
    medic = 6 #血包：回复血量
```

### 武器类名

- `Shotgun`：散弹枪，玩家的初始武器
- `LazerGun`：激光
- `MissileLauncher`：导弹发射器
- `RocketLauncher`：火箭发射器
- `EnergyWeapon`：能量武器，敌人使用
- `Shotgun_slow`：慢速的散弹枪，敌人使用
- `Shotgun_normal`：中等的散弹枪，敌人使用
- `MissileLauncher_slow`慢速的导弹发射器，敌人使用
