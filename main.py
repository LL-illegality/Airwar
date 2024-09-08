import pgzrun
import pgzero
from pgzero.builtins import *
import json
import asyncio
import time
import random
import guide
import data
from data import pi
import sys
from const import *
from entities import *

'''developed by LL'''

TITLE = "Airwar"
WIDTH = SCREENSIZE[0]
HEIGHT = SCREENSIZE[1]
version = '1.0.0'
gamemode = data.GameMode.single

class ImageLoader:
    imageList: dict[str, Actor] = {}
    actorList: list[Actor] = []
    pressedKeyList: list = []
    currtick: float = 0
    def __init__(self) -> None:
        for i in range(2):
            act = Actor(f'player{str(i+1)}.png', anchor = ('center', 'center'))
            self.imageList[f"player{str(i+1)}"] = act
        for i in projectileNameList:
            act = Actor(f'{i}.png', anchor=('center', 'center'))
            self.imageList[f"{i}"] = act
        for i in range(1):
            act = Actor(f'unit{str(i+1)}.png', anchor=('center', 'center'))
            self.imageList[f"unit{str(i+1)}"] = act
    
    def draw_(self) -> None:
        self.actorList.clear()
        for i in board.playerList:
            act = self.imageList[f"player{str(i.id+1)}"]
            act.pos = (i.x, i.y)
            act.draw()
            self.actorList.append(act)
        for i in board.bulletList:
            act = self.imageList[f"{i.get('type')}"]
            act.pos = (i.x, i.y)
            act.angle = (i.get('direction')) * (-180 / pi) - 90
            act.draw()
            self.actorList.append(act)
        for i in board.unitList:
            act = self.imageList[f"unit{str(i.get('type')+1)}"]
            act.pos = (i.x, i.y)
            act.draw()
            self.actorList.append(act)
    
    def onKeyDown(self, key) -> None:
        if key not in self.pressedKeyList:
            self.pressedKeyList.append(key)
    
    def onKeyUp(self, key) -> None:
        if key in self.pressedKeyList:
            self.pressedKeyList.remove(key)
    
    def checkCollision(self) -> None:
        quadTree = Quadtree((0, 0, WIDTH, HEIGHT))
        for i in self.actorList:
            rect = i
            quadTree.insert(rect)
        for actor in self.actorList:
            rangeRect = actor
            potentialCollisions = quadTree.query(rangeRect)
            for other in potentialCollisions:
                if actor != other:
                    if actor.colliderect(other):
                        print(f"collision between {actor.image} and {other.image}")
    
    def update(self) -> None:
        global board, gamemode
        self.currtick += 1/60
        if self.currtick >= gametick:
            pos: tuple = (-1, -1)
            if gamemode == data.GameMode.join:
                board.loadData(web.sendMessage("getBoard"))
                self.currtick = 0
                if keys.SPACE in self.pressedKeyList:
                    web.sendMessage(f"shoot {mainPlayer.id} bullet player 10 forward")
            if gamemode != data.GameMode.join:
                self.currtick = 0
                self.checkCollision()
                board.update()
                if keys.SPACE in self.pressedKeyList:
                    board.unitShoot(mainPlayer.id, 'missile', 'player', 0, 'forward')
            if keys.W in self.pressedKeyList:
                pos = mainPlayer.move(1.5*pi, 3)
            if keys.S in self.pressedKeyList:
                pos = mainPlayer.move(pi/2, 3)
            if keys.A in self.pressedKeyList:
                pos = mainPlayer.move(pi, 3)
            if keys.D in self.pressedKeyList:
                pos = mainPlayer.move(0, 3)
            if pos != (-1, -1) and gamemode == data.GameMode.join:
                web.sendMessage(f"move {mainPlayer.id} {pos[0]} {pos[1]}")


'''program launch config'''

guide.gameguide()

board: data.Board = data.Board()
mainPlayer: data.Player = data.Player(0)
board.addPlayer(mainPlayer)
board.addUnit(data.Unit(type = 0, race = "player", moveFunction = 'x=10*cos(tan(0.1*t))+400;y=20*sin(cot(0.1*t))+y', speed = 1, x = 400, y = 300))
imageLoader: ImageLoader = ImageLoader()
#music.play_once("lostcity_intro.wav")
if guide.launchArg['mode'] == 'multi' and guide.launchArg['host'] == False:
    gamemode = data.GameMode.join
    web = data.Client(guide.launchArg['ip'], guide.launchArg['port'])
    web.sendMessage("joinPlayer")
    board.loadData(web.sendMessage("getBoard"))
    mainPlayer = board.find(1)
elif guide.launchArg['mode'] == 'multi' and guide.launchArg['host'] == True:
    web = data.Server(guide.launchArg['ip'], guide.launchArg['port'], board)
    web.run()
    gamemode = data.GameMode.multi
else:
    web = None
    gamemode = data.GameMode.single

def draw() -> None:
    screen.fill((230, 230, 230))
    imageLoader.draw_()

def on_key_down(key) -> None:
    imageLoader.onKeyDown(key)

def on_key_up(key) -> None:
    imageLoader.onKeyUp(key)

def update() -> None:
    imageLoader.update()

def on_music_end():
    music.play('lostcity.wav')

if guide.launchArg["mode"] == "none":
    sys.exit()
else:
    pgzrun.go()
    if gamemode == data.GameMode.multi:
        web.server.close()
