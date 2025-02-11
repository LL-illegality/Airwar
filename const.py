import math
from enum import Enum
from typing import Any
import pygame
import json
import os

pygame.mixer.init()

pi: float = 3.141592653589793
SCREENSIZE = (800, 600)
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

class Images(Enum):
    player1 = 'player1'
    player2 = "player2"
    bullet1 = "bullet1"
    lazer1 = "lazer_level1"
    lazer2 = "lazer_level2"
    lazer3 = "lazer_level3"
    lazer4 = "lazer_level4"
    lazer5 = "lazer_level5"
    missile = "missile"
    unit1 = "unit1"
    rocket = "rocket"
    energyball = "energyball"
    magabomb = "magabomb"
    en = "en"
    enemy2 = "enemy2"
    ready = "ready"
    enemy = "enemy"
    rship = "rship"
    item_shotgun = "item_shotgun"
    item_missile = "item_missile"
    item_lazer = "item_lazer"
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
    mainmenu = "mainmenu"
    tutorial = "tutorial"

class MusicIntro(Enum):
    future = "future_intro"
    lostcity = "lostcity_intro"
    pop = "pop_intro"

class MusicLoop(Enum):
    future = "future"
    lostcity = "lostcity"
    pop = "pop"

class Sounds(Enum):
    prepare = "prepare"
    unprepare = "unprepare"
    transmission = "transmission"

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

configuration = Configuration()
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
    ItemTypes.medic: Images.item_medic
}
