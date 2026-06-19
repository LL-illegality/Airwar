import math
from enum import Enum
from typing import Any
import pygame
import json
import os

pygame.mixer.init()

pi: float = 3.141592653589793
SCREENSIZE = (800, 600)
CELL_SIZE = 100
CAPACITY = 4
disappearAera = (-100, -100, SCREENSIZE[0]+100, SCREENSIZE[1]+100)
gametick: int = 30

class Keys:
    a = 97
    s = 115
    d = 100
    w = 119
    c = 99
    e = 101
    p = 112
    space = 32
    esc = 27

class ItemTypes(Enum):
    shotgun = 0
    lazer = 1
    missile = 2
    super = 3
    rocket = 4
    magabomb = 5
    medic = 6
    autocannon = 7

class Images(Enum):
    player1 = 'player1'
    player2 = "player2"
    bullet1 = "bullet1"
    bullet_enemy = "bullet_enemy"
    lazer1 = "lazer_level1"
    lazer2 = "lazer_level2"
    lazer3 = "lazer_level3"
    lazer4 = "lazer_level4"
    lazer5 = "lazer_level5"
    lazer6 = "lazer_level6"
    lazer7 = "lazer_level7"
    lazer8 = "lazer_level8"
    lazer9 = "lazer_level9"
    lazer10 = "lazer_level10"
    autocannon12 = "autocannon_level12"
    autocannon34 = "autocannon_level34"
    autocannon56 = "autocannon_level56"
    autocannon7 = "autocannon_level7"
    autocannon8 = "autocannon_level8"
    autocannon9 = "autocannon_level9"
    autocannon10 = "autocannon_level10"
    missile = "missile"
    unit1 = "unit1"
    big1 = "big1"
    big2 = "big2"
    rocket = "rocket"
    rocket_enemy = "rocket_enemy"
    energyball = "energyball"
    energyball_enhanced = "energyball_enhanced"
    magabomb = "magabomb"
    en = "en"
    enemy2 = "enemy2"
    enemy3 = "enemy3"
    enemy4 = "enemy4"
    enemy5 = "enemy5"
    ready = "ready"
    enemy = "enemy"
    rship = "rship"
    rship2 = "rship2"
    rship3 = "rship3"
    rship4 = "rship4"
    item_shotgun = "item_shotgun"
    item_missile = "item_missile"
    item_lazer = "item_lazer"
    item_autocannon = "item_autocannon"
    item_super = "item_super"
    item_rocket = "item_rocket"
    item_maga = "item_maga"
    item_medic = "item_medic"
    ca = "ca"

class Music(Enum):
    future = "future"
    future_intro = "future_intro"
    lostcity = "lostcity"
    lostcity_intro = "lostcity_intro"
    pop = "pop"
    pop_intro = "pop_intro"
    universe41 = "universe41"
    universe41_intro = "universe41_intro"
    beach = "beach"
    beach_intro = "beach_intro"
    escape = "escape"
    escape_intro = "escape_intro"
    mainmenu = "mainmenu"
    tutorial = "tutorial"

class MusicIntro(Enum):
    future = "future_intro"
    lostcity = "lostcity_intro"
    pop = "pop_intro"
    universe41 = "universe41_intro"
    beach = "beach_intro"
    escape = "escape_intro"

class MusicLoop(Enum):
    future = "future"
    lostcity = "lostcity"
    pop = "pop"
    universe41 = "universe41"
    beach = "beach"
    escape = "escape"

class Sounds(Enum):
    prepare = "prepare"
    unprepare = "unprepare"
    transmission = "transmission"
    explode1 = "explode1"
    explode2 = "explode2"
    explode3 = "explode3"
    explode4 = "explode4"
    explode5 = "explode5"
    missile_shoot = "missile_shoot"
    rocket_shoot = "rocket_shoot"
    nuclear_missile_shoot = "nuclear_missile_shoot"
    nuclear_missile_explode = "nuclear_missile_explode"
    lazer_shoot = "lazer_shoot"
    shotgun_shoot = "shotgun_shoot"
    autocannon_shoot = "autocannon_shoot"
    itemget = "itemget"

class ImageMap:
    def __init__(self) -> None:
        self.images: dict[Images, pygame.Surface] = {}
        for img in Images:
            image = pygame.image.load(f".\\images\\{img.value}.png")
            #rect = image.get_rect()
            self.images[img] = image

class MusicMap:
    def __init__(self) -> None:
        self.music: dict = {}
        for music in Music:
            self.music[music] = f".\\music\\{music.value}.wav"

class SoundMap:
    def __init__(self) -> None:
        self.sounds: dict = {}
        for sound in Sounds:
            self.sounds[sound] = pygame.mixer.Sound(f".\\sounds\\{sound.value}.wav")

class GameMode(Enum):
    single = 0
    multiHost = 1
    multiJoin = 2

class Race(Enum):
    player = 0
    enemy = 1
    neutral = 2

class WeaponJamType(Enum):
    none = 0
    shotgun = 1
    lazer = 2

class FlagFinishCondition(Enum):
    waitForTime = 0
    killAll = 1

class GameState(Enum):
    mainMenu = 0
    loadLevel = 1
    inGame = 2
    gameOver = 3
    pause = 4
    gameWin = 5

class Configuration:
    def __init__(self) -> None:
        cfgFiles = os.listdir(".\\configs")
        for cfg in cfgFiles:
            if cfg.endswith(".json"):
                with open(f".\\configs\\{cfg}", "r") as f:
                    self.__dict__[cfg[:-5]] = json.load(f)
    
    def __getattr__(self, name: str) -> Any:
        return self.__dict__.get(name)

configuration: Any = Configuration()
imageMap = ImageMap()
soundMap = SoundMap()
musicMap = MusicMap()

introLoopMap = {
    list(MusicIntro)[i]: list(MusicLoop)[i] for i in range(len(MusicIntro))
}

itemMap = {
    ItemTypes.shotgun: Images.item_shotgun,
    ItemTypes.lazer: Images.item_lazer,
    ItemTypes.missile: Images.item_missile,
    ItemTypes.super: Images.item_super,
    ItemTypes.rocket: Images.item_rocket,
    ItemTypes.magabomb: Images.item_maga,
    ItemTypes.medic: Images.item_medic,
    ItemTypes.autocannon: Images.item_autocannon
}

keyBoardOperationTexts = {
    "move": "W S A D",
    "shoot": "Space",
    "drawMarker": "Z",
    "prepare": "C",
    "nuclear": "E"
}

joyStickOperationTexts = {
    "move": "左摇杆/十字键",
    "shoot": "按钮4",
    "drawMarker": "按钮2",
    "prepare": "按钮1",
    "nuclear": "按钮3"
}
