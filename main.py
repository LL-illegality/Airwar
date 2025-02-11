import json
import asyncio
import time
import random
import guide
import data
import sys
import threading
from const import *
import pygame
from server import *
import client

'''developed by LL'''

TITLE = "Airwar"
WIDTH = SCREENSIZE[0]
HEIGHT = SCREENSIZE[1] + 64
version = '1.0.0'
gamemode = GameMode.single
game = None
websocket = None
waitTime = 0

class ImageLoader:
    def __init__(self) -> None:
        self.dataList: list = []
        self.drawTriangle = False
        self.awaitingSurfaceList: list[pygame.Surface] = []
    
    async def getData(self) -> None:
        global websocket
        response = await websocket.sendMessage(Message(websocket.player_id, "get", {}))
        self.dataList = response['content']['objects']
    
    def setTutorial(self, *args) -> None:
        global waitTime
        if websocket != None:
            data = websocket.resopnse['content']['step']
            playerKeys: list[int] = websocket.resopnse['content']['playerKeys']
            if data == 1:
                self.awaitingSurfaceList.append(font.render("----------Airwar----------", True, (0, 0, 0)))
                waitTime = 5 * 60
            if data == 2:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("欢迎来到Airwar新手教程", True, (0, 0, 0)))
                isBusy = pygame.mixer.music.get_busy()
                if isBusy == False:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                pygame.mixer.music.load(musicMap.music[Music("tutorial")])
                pygame.mixer.music.play(-1)
                waitTime = 3 * 60
            if data == 3:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("按下W S A D键来控制飞机移动", True, (0, 0, 0)))
                waitTime = 10 * 60
            if data == 4:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("按下空格键来发射子弹", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 5:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("按下Z键可在自身下方绘制标记", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 6:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("标记可在多人游戏中帮助辨别自己的位置", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 7:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("长按C键进入准备状态", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 8:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("当所有玩家都进入准备状态后，游戏开始", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 9:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("敌人出现了，试着移动并击杀敌人", True, (0, 0, 0)))
                waitTime = 2147483647
            if data == 10:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("很好", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 11:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("击杀敌人后可能会掉落道具", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 12:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("试着再次击杀敌人吧", True, (0, 0, 0)))
                waitTime = 2147483647
            if data == 13:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("不同的道具有不同的效果", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 14:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("可以升级武器，回复血量，或者更换武器等等", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 15:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("试着击杀敌人并收集道具吧", True, (0, 0, 0)))
                waitTime = 2147483647
            if data == 16:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("当敌人数量过多无法解决时", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 17:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("若右下角有核弹图标", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 18:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("则可以按下E键使用核弹", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 19:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("核弹可以一次性消灭所有敌人", True, (0, 0, 0)))
                waitTime = 2 * 60
            if data == 20:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("使用核弹消灭敌人吧", True, (0, 0, 0)))
                waitTime = 2147483647
            if data == 21:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("很好，你已经学会了所有技能了", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 22:
                self.awaitingSurfaceList.clear()
                self.awaitingSurfaceList.append(fontChinese.render("教程结束", True, (0, 0, 0)))
                waitTime = 3 * 60
            if data == 23:
                sys.exit()
            pygame.mixer.Sound.play(soundMap.sounds[Sounds.transmission])
    
    def draw_(self, *args) -> None:
        #asyncio.run(self.getData())
        screen.fill((230, 230, 230))
        for surface in self.awaitingSurfaceList:
            rect = surface.get_rect()
            rect.center = (WIDTH/2, HEIGHT/3)
            screen.blit(surface, rect)
        if websocket != None:
            self.dataList = websocket.resopnse['content']['objects']
            for data in self.dataList:
                image = imageMap.images[Images(data['image'])]
                image = pygame.transform.rotate(image, -data['rotation'])
                rect = image.get_rect()
                rect.center = (data['x'], data['y'])
                screen.blit(image, rect)
                if 'isReady' in data:
                    if data['isReady'] == True and ResourcesLoader.currGameState == GameState.mainMenu:
                        tick = imageMap.images[Images.ready]
                        rect = tick.get_rect()
                        rect.center = (data['x'], data['y'] - 48)
                        screen.blit(tick, rect)
                if 'player_id' in data:
                    try:
                        if data['player_id'] == websocket.player_id:
                            if self.drawTriangle == True:
                                pygame.draw.polygon(screen, (0, 192, 0), [(data['x'], data['y'] + 24), (data['x'] - 4, data['y'] + (12*1.732)), (data['x'] + 4, data['y'] + (12*1.732))])
                            stateBar = pygame.Surface((WIDTH, 64))
                            stateBar.fill((192, 192, 192))
                            stateBar.blit(font.render(f"Player{data['player_id']}", True, (19, 19, 19)), (0, 4))
                            stateBar.blit(font.render(f"HP:", True, (19, 19, 19)), (0, 24))
                            pygame.draw.rect(stateBar, (19, 19, 19), (35, 25, 202, 18))
                            pygame.draw.rect(stateBar, (255 * (1 - data['health'] / 100), 255 * (data['health'] / 100), 0), (36, 26, data['health'] * 2, 16))
                            bombs = imageMap.images[Images.item_maga]
                            for i in range(data['magabombQuantity']):
                                rect = bombs.get_rect()
                                rect.center = (WIDTH - 32 - (i * 32), 32)
                                stateBar.blit(bombs, rect)
                            screen.blit(stateBar, (0, HEIGHT - 64))
                    except:
                        pass

class SoundLoader:
    def __init__(self) -> None:
        self.soundData = ''
    
    def play(self, *args) -> None:
        if websocket != None:
            self.soundData = websocket.resopnse['content']['sound']
            self.play_once(self.soundData)

    def play_once(self, name: str) -> None:
        pygame.mixer.Sound.play(soundMap.sounds[Sounds(name)])

class MusicLoader:
    def __init__(self) -> None:
        self.data: int = 0
        self.msc = None
        self.historyData = None

    def play(self, *args) -> None:
        if websocket != None:
            self.data = websocket.resopnse['content']['state']
            if self.data == self.historyData:
                return
            self.historyData = self.data
            isBusy = pygame.mixer.music.get_busy()
            msc = random.choice(list(MusicIntro))
            if isBusy == True:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            if self.data == GameState.mainMenu.value:
                pygame.mixer.music.load(musicMap.music[Music("mainmenu")])
                pygame.mixer.music.play(-1)
            if self.data == GameState.loadLevel.value:
                self.msc = msc
                pygame.mixer.music.load(musicMap.music[Music(msc.value)])
                pygame.mixer.music.play(-1)
            if self.data == GameState.inGame.value:
                if self.msc == None:
                    self.play()
                    return
                mscloop = introLoopMap[self.msc]
                pygame.mixer.music.load(musicMap.music[Music(mscloop.value)])
                pygame.mixer.music.play(-1)

class ResourcesLoader:
    currGameState = GameState.mainMenu
    def __init__(self) -> None:
        self.imageLoader = ImageLoader()
        self.soundLoader = SoundLoader()
        self.musicLoader = MusicLoader()
        self.processMappingTable: dict[str, callable | None] = {
            "screen_info": self.imageLoader.draw_,
            "game_state_changed": self.on_gamestate_changed,
            "setTutorial": self.imageLoader.setTutorial,
            "playsound": self.soundLoader.play,
        }
    
    def process(self, responseMessage: Message) -> None:
        if responseMessage.type in self.processMappingTable.keys():
            self.processMappingTable[responseMessage.type](responseMessage)
    
    def on_gamestate_changed(self, responseMessage: Message) -> None:
        self.currGameState = GameState(responseMessage.content['state'])
        self.musicLoader.play()

'''program launching configuration'''

async def launchClient() -> None:
    global websocket
    websocket = client.Client(0, guide.launchArg['ip'], guide.launchArg['port'])
    await asyncio.gather(*[websocket.connect()])

guide.gameguide()
if guide.launchArg["mode"] == "single":
    gamemode = GameMode.single
    websocket = client.SinglePlayerClient(0, game)
    game = Game(websocket.msgQueue)
    websocket.game = game
    websocket.newPlayer()
elif guide.launchArg["mode"] == "multi":
    gamemode = GameMode.multiJoin
    thread = threading.Thread(target=lambda:asyncio.run(launchClient()))
    thread.start()
else:
    sys.exit()

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consola", 30)
fontChinese = pygame.font.SysFont("SimHei", 30)
pygame.mouse.set_visible(False)
pygame.display.set_caption(TITLE)
#pygame.display.set_icon(pygame.image.load(".\\images\\game.ico"))

resourcesLoader = ResourcesLoader()
#music.play_once("lostcity_intro.wav")

def update() -> None:
    pass

def on_key_down(key) -> None:
    # pygame.key.key_code()
    asyncio.run(websocket.sendMessage(Message(str(websocket.player_id), "keyDown", {"key": key})))

def on_key_up(key) -> None:
    asyncio.run(websocket.sendMessage(Message(str(websocket.player_id), "keyUp", {"key": key})))

async def on_quit() -> None:
    if websocket != None:
        await websocket.disconnect()
    sys.exit()

def mainloop() -> None:
    global waitTime
    def process():
        if websocket != None:
            while websocket.msgQueue.isEmpty() == False:
                websocket.resopnse = websocket.msgQueue.pop()
                if isinstance(websocket.resopnse, Message):
                    websocket.resopnse = json.loads(str(websocket.resopnse))
                if websocket.resopnse != None:
                    if websocket.resopnse['type'] == "playsound":
                        pass
                    resourcesLoader.process(Message(websocket.resopnse['sender'], websocket.resopnse['type'], websocket.resopnse['content']))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                asyncio.run(on_quit())
            elif event.type == pygame.KEYDOWN:
                on_key_down(event.key)
                if event.key == pygame.K_c:
                    pygame.mixer.Sound.play(soundMap.sounds[Sounds.prepare])
            elif event.type == pygame.KEYUP:
                on_key_up(event.key)
                if event.key == pygame.K_c:
                    pygame.mixer.Sound.play(soundMap.sounds[Sounds.unprepare])
                if event.key == pygame.K_z:
                    resourcesLoader.imageLoader.drawTriangle = not resourcesLoader.imageLoader.drawTriangle
        if websocket != None:
            if game != None:
                websocket.update()
                if waitTime == 0:
                    websocket.setTutorialStep()
                else:
                    waitTime -= 1
                if waitTime > 2000000000:
                    if websocket.isScreenEmpty():
                        waitTime = 0
        process()
        pygame.display.flip()
        clock.tick(60)

if guide.launchArg["mode"] == "none":
    sys.exit()
else:
    pygame.mixer.music.load(musicMap.music[Music("mainmenu")])
    pygame.mixer.music.play(-1)
    mainloop()
    sys.exit()
