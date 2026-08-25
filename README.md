# **Airwar**

Airwar 是一款基于 Python 开发的飞行射击闯关游戏，支持桌面客户端与浏览器双端游玩。玩家操控飞机击败敌人、收集道具升级武器、闯过全部关卡，也可与好友在同一服务器中并肩作战。

## 快速开始

### 环境依赖

```bash
pip install -r requirements.txt       # 桌面端依赖：pygame、websockets
pip install -r requirements-web.txt   # 浏览器端 Web 服务依赖：Flask（可选）
```

### 桌面客户端

启动 `Airwar.exe` 或运行 `python main.py`，在启动窗口（Game Guide）中进行设置：

- **Single Player**：单人闯关
- **Multi-Player**：填写服务器 IP 与端口（默认 `8000`）加入多人游戏
- **Fullscreen** 复选框：勾选以全屏启动，取消则以窗口模式启动，选择会保存到 `configs/initializeSettings.json`，下次启动自动恢复

进入游戏后按 `F11` 或 `Alt+Enter` 可在全屏与窗口之间随时切换（窗口模式下可自由拉伸大小，画面等比缩放）。

首次游玩将自动进入新手教程。

### 浏览器客户端

1. 启动 Web 服务：`python web.py`（默认端口 `8080`）
2. 浏览器打开 `http://localhost:8080`（局域网内其他设备访问 `http://<服务器IP>:8080`）
3. 填写玩家名并点击 **加入游戏**，服务器地址默认自动从 `/api/config` 获取，也可手动指定

浏览器端支持鼠标键盘与触屏操作（虚拟摇杆 + 按钮），页面右下角可调节画面缩放（`0.5x ~ 3x`，键盘 `+` / `-` / `0` 亦可）。

### 多人游戏服务器

运行 `python server.py`（或 `server.exe`）即可启动游戏服务器，终端会输出本机 IPv4 / IPv6 地址。服务器同时服务桌面客户端（WebSocket 协议）与浏览器客户端。

---

## 游戏内操作

### 键盘（需切换到英文输入法）

| 按键 | 功能 |
|------|------|
| W / 上 | 向前移动 |
| S / 下 | 向后移动 |
| A / 左 | 向左移动 |
| D / 右 | 向右移动 |
| C（长按） | 进入准备状态 |
| Z | 在自身下方绘制标记 |
| E | 释放核弹 |
| Space | 发射子弹 |
| P | 暂停游戏 |

### 手柄

启动时会自动检测并连接第一个手柄。

| 操作 | 功能 |
|------|------|
| 左摇杆 / 十字键 | 移动 |
| 按钮 1（长按） | 进入准备状态 |
| 按钮 2 | 绘制标记 |
| 按钮 3 | 释放核弹 |
| 按钮 4 | 发射子弹 |
| Start | 暂停游戏 |

---

## 游戏系统

### 玩家

- 飞机拥有红蓝两种颜色，在多人游玩时方便区分
- 屏幕底部为状态栏，显示当前玩家 ID、血量及持有的核弹数量
- 玩家加入游戏、复活时会从屏幕下方飞入战场，约 1 秒内减速停在加入位置，飞入期间不受伤害
- 玩家血量归零后死亡，持有的物品会掉落供其他玩家拾取；死亡后仍可观察战场
- 每通过一关，本关死去的玩家会在新关卡开始时重新飞入战场
- 所有玩家死亡后 5 秒、或通关全部关卡后 10 秒，服务器自动回到主菜单并重生所有在线玩家，等待再次开局

### 敌人

- 敌人在关卡开始时从屏幕外飞入（从顶部俯冲或从左右两侧横飞），不会凭空出现在屏幕上
- 敌人拥有不同的移动方式与攻击方式，配合血量、速度、碰撞体积构成多样的威胁
- 敌人死亡时可能掉落道具

**移动方式**：部分敌人随机游走，部分横向往返（strafe），部分绕圈巡航（circle），部分飞入战场后驻留原地（station）。

**攻击方式**：除直接射击外，部分敌人使用更具策略性的攻击模式，例如扇形扫射、扇形齐射、预判玩家位置的精确狙击（结合玩家速度与加速度计算提前量，且受最大速度限制）、蓄力后连射、按图案发射弹幕（环形/螺旋/十字/菱形）、连续扩散的环形弹幕，以及随时间或血量切换攻击阶段的 BOSS。

### 物品道具

道具会在屏幕内弹跳，只可被玩家拾取，无视敌人和弹射物，超时后消失，消失前会有闪烁动画作为提醒。

主武器道具和副武器道具会在一定时间后变为同类型的其他道具

| 道具 | 效果 |
|------|------|
| 散弹枪 / 激光 / 自动机炮 | 更换或升级当前武器（同类型升级，不同类型替换） |
| 导弹 / 火箭 | 添加或更改为副武器，不替换主武器 |
| 超级 | 将当前武器升至满级 |
| 血包 | 随机回复25%~75%的血量 |
| 核弹 | 增加玩家核弹持有数量 |

### 武器系统

武器分为10个等级，等级越高伤害和射速越强。玩家初始持有散弹枪。

| 武器 | 说明 |
|------|------|
| `Shotgun` | 散弹枪，初始武器 |
| `LazerGun` | 激光 |
| `Autocannon` | 自动机炮 |
| `MissileLauncher` | 导弹发射器（副武器，自动追踪） |
| `RocketLauncher` | 火箭发射器（副武器，直线高速） |
| 敌人武器 | 敌人使用的能量武器、火箭等，以及机制型攻击模式（见开发者文档） |

### 核弹

按下 E 键从玩家位置投下，落地后清除屏幕内所有敌人和弹射物（不影响队友），是危急时刻的清场手段。

### 关卡系统

关卡以 JSON 格式存放在 `levels/` 目录下。游戏按文件名的系统顺序加载关卡。每关由多波（Flag）敌人组成，通过后进入下一关，全部通关后回到主菜单重新开始。

以下为一个只含有一波出怪的关卡示例

```json
{
    "name": "level0",
    "totalFlags": 1,
    "drops": [0, 1, 6, 2, 4],
    "flags": [
        {
            "unitTypeList": ["weakling"],
            "timeBeforeNext": 300,
            "finishCondition": 0
        }
    ]
}
```

关卡支持**动态分波**：当玩家平均武器等级较低且敌人数量较多时，当前波会自动分割，随机将部分敌人延后到下一波，降低压力。分割时也会根据玩家的核弹持有量调整分波数量。

### 视觉与粒子效果

- **动态天空背景**：蓝色渐变天空、块状云朵、蜿蜒河流、灰度山脉，所有元素持续向下滚动模拟飞行感
- **粒子特效**：爆炸（敌机、玩家、导弹、火箭、核弹）、武器命中特效（子弹橙黄、激光亮蓝、机炮浅红）、飞行尾焰（导弹/火箭），每个粒子均带有随机亮度变化
- **背景音乐**：主菜单、关卡加载、战斗阶段分别播放不同的循环音乐

### 网络架构

- 游戏服务器（`server.py`）基于 `websockets` + `asyncio`，负责全部游戏逻辑计算（碰撞、伤害、AI、关卡推进等），支持 **IPv4 / IPv6 双栈**，同时服务桌面与浏览器客户端
- 桌面客户端负责渲染、音频播放和按键监听，与服务器通过 WebSocket 通信
- 浏览器客户端通过 WebSocket 连接服务器，画面渲染、粒子特效、背景与音乐均在浏览器端实现
- Web 静态服务（`web.py`，Flask）负责托管浏览器端页面与资源，并提供 `/api/config` 等接口辅助客户端连接

---

## 开发者文档

### 配置文件

`Configuration` 类自动读取 `configs/` 目录下所有 JSON 文件，以文件名（不含后缀）作为属性名挂载到全局对象上：

```python
configuration = Configuration()
configuration.设置文件名["key"]
```

### 关卡属性（`Level`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 关卡名称，加载时显示在屏幕中央 |
| `totalFlags` | `int` | 总波数，应与 `flags` 长度一致 |
| `flags` | `list[dict]` | 每波的定义 |
| `drops` | `list[int]` | 关卡中会掉落的道具（枚举值列表） |

### 波属性（`Flag`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `unitTypeList` | `list[str]` | 该波中的敌人种类列表 |
| `timeBeforeNext` | `int` | 下一波到来前的等待时间（游戏刻） |
| `finishCondition` | `int` | 波的完成条件（0 = 计时结束即加载，1 = 计时结束且屏幕无敌人） |

### 敌人种类构建者（`EnemyBuilder`）

支持在 `configs/enemyTypes.json` 中定义敌人：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `health` | `int` | 100 | 血量 |
| `image` | `str` | `"en"` | 图片文件名（无后缀） |
| `weapon` | `list[str]` | `None` | 武器类名列表（玩家武器、敌人武器或机制攻击模式均可） |
| `weapon_params` | `dict` | `{}` | 按武器类名覆盖其构造参数，如 `{"FanSweepNormal": {"fire_rate": 15}}` |
| `velocity` | `dict` | `{"x":0,"y":0}` | 初始速度（像素/游戏刻） |
| `acceleration` | `dict` | `{"x":0,"y":0}` | 初始加速度（像素/游戏刻²） |
| `boundingBox` | `dict` | `None` | 碰撞箱 `{"width":56,"height":56}` |
| `targetPos` | `list[int]` | `None` | 目标坐标 `[x, y]`（station 敌人的驻留点） |
| `maxVelocity` | `int` | `None` | 最大速度 |
| `velocityMultiplier` | `float` | `0.9` | 阻力系数（<1 减速，=1 匀速，>1 加速） |
| `inventory` | `list[int]` | `[]` | 死亡时掉落的道具枚举值列表 |
| `move_pattern` | `str` | `"random"` | 移动方式（见下表） |
| `shoot_pattern` | `str` | `"auto"` | 射击节奏（`auto` 持续射击 / `burst` 间歇射击） |
| `move_thrust` | `float` | `1.5` | 移动推力（strafe / circle / station 飞行共用，调小可降低移速） |

**移动方式（`move_pattern`）**

| 值 | 说明 |
|----|------|
| `random` | 随机游走（默认） |
| `station` | 飞入战场后驻留在 `targetPos`（未配置则随机选点）并定住不动 |
| `strafe` | 屏幕上部横向往返 |
| `circle` | 绕屏幕中心圆周运动 |

### 敌人攻击模式（机制武器）

机制武器类继承 `EnemyWeapon`，通过 `weapon` 字段按类名启用，参数可用 `weapon_params` 覆盖。模式基类定义攻击逻辑，难度变体类提供默认参数组合（如 `FanSweepNormal` / `FanSweepHard`），也可自行继承基类创建新变体。

| 模式 | 基类 | 说明 |
|------|------|------|
| 扇形扫射 | `FanSweep` | 扇形中心持续朝向玩家旋转，扇形内均匀撒弹（`fan_angle` / `sweep_speed` / `bullets_per_shot`） |
| 扇形齐射 | `FanVolley` | 间隔一段时间向玩家方向齐射一轮扇形弹（`volley_count` / `fan_angle` / `burst_interval`） |
| 预判射击 | `LeadShot` | 结合玩家速度与加速度求解命中方程，向玩家未来位置精确射击；受玩家最大速度限制防止预判过头（`bullet_speed` / `prediction_factor`） |
| 蓄力连射 | `ChargeBurst` | 蓄力（期间停止移动）→ 快速连射 → 休息，循环（`charge_duration` / `burst_count` / `rest_duration`） |
| 固定弹幕 | `FixedPattern` | 按预设图案发射一圈弹幕（`pattern`：`ring` / `spiral` / `cross` / `diamond`，`pattern_params` 可覆盖） |
| 环形弹幕 | `RingBlast` | 连续发射多圈向外扩散的环形弹（`ring_count` / `rings` / `ring_interval`） |
| 阶段切换 | `PhaseSwitch` | 按时间或血量阈值在多个子武器间切换（`phases` / `trigger`：`time` / `health` / `hp_ratio`） |

### 波完成条件枚举

```python
class FlagFinishCondition(Enum):
    waitForTime = 0  # 计时结束即加载下一波
    killAll = 1      # 计时结束且场上无敌人时加载下一波
```

### 道具种类枚举

```python
class ItemTypes(Enum):
    shotgun = 0     # 散弹枪
    lazer = 1       # 激光
    missile = 2     # 导弹（副武器）
    super = 3       # 超级升级
    rocket = 4      # 火箭（副武器）
    magabomb = 5    # 核弹
    medic = 6       # 血包
    autocannon = 7  # 自动机炮
```

### 可用武器类名

| 类名 | 使用方 |
|------|--------|
| `Shotgun` | 玩家初始武器 |
| `LazerGun` | 玩家 |
| `Autocannon` | 玩家 |
| `MissileLauncher` | 玩家副武器 |
| `RocketLauncher` | 玩家副武器 |
| `Shotgun_slow` / `Shotgun_normal` | 敌人 |
| `MissileLauncher_slow` | 敌人 |
| `RocketLauncherEnemy` | 敌人 |
| `EnergyWeapon` / `EnergyWeaponEnhanced` | 敌人 |
| `FanSweepNormal` / `FanSweepHard` | 敌人（扇形扫射） |
| `FanVolleyNormal` / `FanVolleyHard` | 敌人（扇形齐射） |
| `LeadShotNormal` / `LeadShotHard` | 敌人（预判射击） |
| `ChargeBurstNormal` / `ChargeBurstHard` | 敌人（蓄力连射） |
| `FixedPatternSpiral` / `FixedPatternCross` / `FixedPatternDiamond` | 敌人（固定弹幕） |
| `RingBlastNormal` / `RingBlastWide` | 敌人（环形弹幕） |
| `PhaseSwitchEarly` / `PhaseSwitchLate` | BOSS（阶段切换） |

### 项目结构

```
Airwar/
├── main.py               # 桌面客户端入口
├── server.py             # 游戏服务器（WebSocket + 全部游戏逻辑）
├── web.py                # 浏览器端 Web 服务（Flask 静态托管 + API）
├── client.py             # 桌面客户端网络层（含单人模式）
├── display.py            # 桌面端显示管理（全屏/窗口、缩放、坐标转换）
├── guide.py              # 桌面启动窗口（模式选择、全屏设置）
├── const.py              # 全局常量与枚举（含图片/音效/音乐资源表）
├── data.py               # 消息、队列、向量等基础数据结构
├── configs/              # 配置文件（敌人种类、启动设置）
├── levels/               # 关卡定义（JSON）
├── images/               # 图片资源
├── sounds/               # 音效资源
├── music/                # 音乐资源
├── fonts/                # 字体资源
└── web/                  # 浏览器客户端（HTML/CSS/JS）
```
