import json
import sys
import random
import pygame
from typing import Any
from const import *
from data import Message
from server import EnemyBuilder, BoundingBox, Race, Images, Unit


class TutorialManager:
    def __init__(self, game: Any, msgQueue: Any, font: pygame.font.Font, fontChinese: pygame.font.Font):
        self.game = game
        self.msgQueue = msgQueue
        self.font = font
        self.fontChinese = fontChinese
        self.tutorialStep = 0
        self.waitTime = 0
        self.awaitingSurfaceList: list[pygame.Surface] = []
        self._isActive = False
        self.completed = False
        self._showTutorial = True
        self._loadConfig()

    def _loadConfig(self) -> None:
        try:
            with open(".\\configs\\initializeSettings.json", "r") as f:
                config = json.load(f)
                if config.get("showTutorial", True) == False:
                    self._showTutorial = False
        except:
            pass

    def _saveConfig(self) -> None:
        try:
            with open(".\\configs\\initializeSettings.json", "r") as f:
                config = json.load(f)
        except:
            config = {}
        config["showTutorial"] = False
        with open(".\\configs\\initializeSettings.json", "w") as f:
            json.dump(config, f)

    def shouldShowTutorial(self) -> bool:
        return self._showTutorial

    def isActive(self) -> bool:
        return self._isActive

    def isComplete(self) -> bool:
        return self.completed

    def isScreenEmpty(self) -> bool:
        if self.game is None:
            return True
        return len(self.game.board.units) == 0

    def addTutorialUnit(self, unit: Unit) -> None:
        if self.game is None:
            return
        unit.x = SCREENSIZE[0] / 2
        unit.boundingBox = BoundingBox(56, 56)
        self.game.board.addUnit(unit, 'unit')
        unit.race = Race.enemy

    def start(self) -> None:
        if not self._showTutorial or self.game is None:
            self.completed = True
            return
        self._isActive = True
        self.tutorialStep = 0
        self.waitTime = 0
        self.awaitingSurfaceList.clear()

    def update(self) -> None:
        if not self._isActive or self.completed:
            return
        if self.waitTime == 0:
            self._advanceStep()
        else:
            self.waitTime -= 1
        if self.waitTime > 2000000000:
            if self.isScreenEmpty():
                self.waitTime = 0

    def _advanceStep(self) -> None:
        self.tutorialStep += 1
        step = self.tutorialStep
        self.awaitingSurfaceList.clear()

        operationText = keyBoardOperationTexts

        if step == 1:
            self.awaitingSurfaceList.append(self.font.render("----------Airwar----------", True, (19, 19, 19)))
            self.waitTime = 5 * gametick
        elif step == 2:
            self.awaitingSurfaceList.append(self.fontChinese.render("欢迎来到Airwar新手教程", True, (19, 19, 19)))
            isBusy = pygame.mixer.music.get_busy()
            if isBusy == False:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            pygame.mixer.music.load(musicMap.music[Music("tutorial")])
            pygame.mixer.music.play(-1)
            self.waitTime = 3 * gametick
        elif step == 3:
            self.awaitingSurfaceList.append(self.fontChinese.render(f"使用{operationText['move']}来控制飞机移动", True, (19, 19, 19)))
            self.waitTime = 10 * gametick
        elif step == 4:
            self.awaitingSurfaceList.append(self.fontChinese.render(f"按下{operationText['shoot']}来发射子弹", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 5:
            self.awaitingSurfaceList.append(self.fontChinese.render(f"按下{operationText['drawMarker']}可在自身下方绘制标记", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 6:
            self.awaitingSurfaceList.append(self.fontChinese.render("标记可在多人游戏中帮助辨别自己的位置", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 7:
            self.awaitingSurfaceList.append(self.fontChinese.render(f"长按{operationText['prepare']}进入准备状态", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 8:
            self.awaitingSurfaceList.append(self.fontChinese.render("当所有玩家都进入准备状态后，游戏开始", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 9:
            self.awaitingSurfaceList.append(self.fontChinese.render("敌人出现了，试着移动并击杀敌人", True, (19, 19, 19)))
            self.waitTime = 2147483647
            unit = EnemyBuilder().build()
            self.addTutorialUnit(unit)
        elif step == 10:
            self.awaitingSurfaceList.append(self.fontChinese.render("很好", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 11:
            self.awaitingSurfaceList.append(self.fontChinese.render("击杀敌人后可能会掉落道具", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 12:
            self.awaitingSurfaceList.append(self.fontChinese.render("试着再次击杀敌人吧", True, (19, 19, 19)))
            self.waitTime = 2147483647
            unit = EnemyBuilder(inventory=[0], weapon=["Shotgun_normal"]).build()
            self.addTutorialUnit(unit)
        elif step == 13:
            self.awaitingSurfaceList.append(self.fontChinese.render("不同的道具有不同的效果", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 14:
            self.awaitingSurfaceList.append(self.fontChinese.render("可以升级武器，回复血量，或者更换武器等等", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 15:
            self.awaitingSurfaceList.append(self.fontChinese.render("试着击杀敌人并收集道具吧", True, (19, 19, 19)))
            self.waitTime = 2147483647
            for i in range(7):
                unit = EnemyBuilder(inventory=[i], image=random.choice([Images.ca, Images.enemy, Images.enemy2, Images.rship, Images.unit1])).build()
                self.addTutorialUnit(unit)
        elif step == 16:
            self.awaitingSurfaceList.append(self.fontChinese.render("当敌人数量过多无法解决时", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 17:
            self.awaitingSurfaceList.append(self.fontChinese.render("若右下角有核弹图标", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 18:
            self.awaitingSurfaceList.append(self.fontChinese.render(f"则可以按下{operationText['nuclear']}使用核弹", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 19:
            self.awaitingSurfaceList.append(self.fontChinese.render("核弹可以一次性消灭所有敌人", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 20:
            self.awaitingSurfaceList.append(self.fontChinese.render("使用核弹消灭敌人吧", True, (19, 19, 19)))
            self.waitTime = 2147483647
            for player in self.game.board.players:
                if player.magabombQuantity == 0:
                    player.magabombQuantity += 1
            for _ in range(10):
                unit = EnemyBuilder(health=1000000, image=random.choice([Images.ca, Images.enemy, Images.enemy2, Images.rship, Images.unit1])).build()
                self.addTutorialUnit(unit)
        elif step == 21:
            self.awaitingSurfaceList.append(self.fontChinese.render("很好，你已经学会了所有技能了", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 22:
            self.awaitingSurfaceList.append(self.fontChinese.render("教程结束", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 23:
            self.awaitingSurfaceList.append(self.fontChinese.render("接下来按下准备即可开始游戏", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 24:
            self._finishTutorial()
            return

        pygame.mixer.Sound.play(soundMap.sounds[Sounds.transmission])

    def _finishTutorial(self) -> None:
        self._saveConfig()
        self._isActive = False
        self.completed = True
        self.awaitingSurfaceList.clear()
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

    def getAwaitingSurfaceList(self) -> list[pygame.Surface]:
        return self.awaitingSurfaceList
