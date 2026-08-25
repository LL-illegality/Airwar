import json
import sys
import random
import pygame
from typing import Any
from const import *
from data import Message
from server import EnemyBuilder, BoundingBox, Race, Images, Unit, Game, WeaponGroup, Shotgun


class TutorialManager:
    def __init__(self, game: Game, msgQueue: Any, font: pygame.font.Font, fontChinese: pygame.font.Font):
        self.game: Game = game
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
            if configuration.initializeSettings["showTutorial"] == False:
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
            self.awaitingSurfaceList.append(self.fontChinese.render("现在你的武器升级了", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 14:
            self.awaitingSurfaceList.append(self.fontChinese.render("当获得与当前武器类型相同的道具时可以升级武器", True, (19, 19, 19)))
            self.waitTime = 4 * gametick
        elif step == 15:
            self.awaitingSurfaceList.append(self.fontChinese.render("若类型不同则会将当前武器替换为新武器", True, (19, 19, 19)))
            self.waitTime = 4 * gametick
        elif step == 16:
            self.awaitingSurfaceList.append(self.fontChinese.render("你当前的武器是霰弹枪，升级增加子弹数量", True, (19, 19, 19)))
            self.waitTime = 4 * gametick
        elif step == 17:
            self.awaitingSurfaceList.append(self.fontChinese.render("现在来试试这个", True, (19, 19, 19)))
            self.waitTime = 2147483647
            unit = EnemyBuilder(inventory=[1]).build()
            self.addTutorialUnit(unit)
        elif step == 18:
            self.awaitingSurfaceList.append(self.fontChinese.render("这是激光武器，发射激光，升级增加伤害", True, (19, 19, 19)))
            self.waitTime = 5 * gametick
        elif step == 19:
            self.awaitingSurfaceList.append(self.fontChinese.render("再来试试这个", True, (19, 19, 19)))
            self.waitTime = 2147483647
            unit = EnemyBuilder(inventory=[7]).build()
            self.addTutorialUnit(unit)
        elif step == 20:
            self.awaitingSurfaceList.append(self.fontChinese.render("这是自动机炮，可以自动瞄准敌人，升级增加子弹速度和伤害", True, (19, 19, 19)))
            self.waitTime = 5 * gametick
        elif step == 21:
            self.awaitingSurfaceList.append(self.fontChinese.render("当然，除了这些武器以外还有副武器", True, (19, 19, 19)))
            self.waitTime = 2147483647
            unit = EnemyBuilder(inventory=[2]).build()
            self.addTutorialUnit(unit)
        elif step == 22:
            self.awaitingSurfaceList.append(self.fontChinese.render("这是导弹发射器，发射导弹，但是不可以升级", True, (19, 19, 19)))
            self.waitTime = 5 * gametick
        elif step == 23:
            self.awaitingSurfaceList.append(self.fontChinese.render("类似的还有这个", True, (19, 19, 19)))
            self.waitTime = 2147483647
            unit = EnemyBuilder(inventory=[4]).build()
            self.addTutorialUnit(unit)
        elif step == 24:
            self.awaitingSurfaceList.append(self.fontChinese.render("这是火箭发射器，伤害高于导弹，同样不可以升级", True, (19, 19, 19)))
            self.waitTime = 5 * gametick
        elif step == 25:
            self.awaitingSurfaceList.append(self.fontChinese.render("此外，还有一些其他道具", True, (19, 19, 19)))
            self.waitTime = 2147483647
            for i in range(3):
                unit = EnemyBuilder(inventory=[[3, 5, 6][i]]).build()
                self.addTutorialUnit(unit)
        elif step == 26:
            self.awaitingSurfaceList.append(self.fontChinese.render("他们分别可以将武器升至满级，回复血量，以及获得一个核弹", True, (19, 19, 19)))
            self.waitTime = 5 * gametick
        elif step == 27:
            self.awaitingSurfaceList.append(self.fontChinese.render("当敌人数量过多无法解决时", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 28:
            self.awaitingSurfaceList.append(self.fontChinese.render("若右下角有核弹图标", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 29:
            self.awaitingSurfaceList.append(self.fontChinese.render(f"则可以按下{operationText['nuclear']}使用核弹", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 30:
            self.awaitingSurfaceList.append(self.fontChinese.render("核弹可以一次性消灭所有敌人", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 31:
            self.awaitingSurfaceList.append(self.fontChinese.render("使用核弹消灭敌人吧", True, (19, 19, 19)))
            self.waitTime = 2147483647
            for player in self.game.board.players:
                if player.magabombQuantity == 0:
                    player.magabombQuantity += 1
            for _ in range(10):
                unit = EnemyBuilder(health=1000000, image=random.choice([Images.ca, Images.enemy, Images.enemy2, Images.rship, Images.unit1])).build()
                self.addTutorialUnit(unit)
        elif step == 32:
            self.awaitingSurfaceList.append(self.fontChinese.render("很好，你已经学会了所有技能了", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 33:
            self.awaitingSurfaceList.append(self.fontChinese.render("教程结束", True, (19, 19, 19)))
            self.waitTime = 3 * gametick
        elif step == 34:
            self.awaitingSurfaceList.append(self.fontChinese.render("接下来按下准备即可开始游戏", True, (19, 19, 19)))
            self.waitTime = 2 * gametick
        elif step == 35:
            for player in self.game.board.players:
                player.inventory = []
                player.gottenItem = []
                player.weapon = WeaponGroup(Shotgun(player.race))
                player.health = 100
                player.magabombQuantity = 1
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
