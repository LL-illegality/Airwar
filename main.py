import json
import asyncio
import time
import random
import guide
import data
import sys
import threading
from typing import Any
from const import *
import pygame
from server import *  # type: ignore[reportGeneralTypeIssues]
import client
import tutorial

'''developed by LL'''

TITLE = "Airwar"
WIDTH: int = SCREENSIZE[0]
HEIGHT: int = SCREENSIZE[1] + 64
VERSION: str = 'Ver. 1.1.2'
gamemode: GameMode = GameMode.single
hasJoystick: bool = False
lastJoyAxis: list[float] = [0.0, 0.0]
game: Game | None = None
websocket: client.Client | client.SinglePlayerClient | None = None

class ImageLoader:
    def __init__(self) -> None:
        self.dataList: list = []
        self.drawTriangle = False
        self.levelInfo: list[pygame.Surface] = []
        self.titleInfo: list[dict] = []
        self.operationText: dict = keyBoardOperationTexts
        self.prevEntities: dict[int, dict] = {}
        self.currEntities: dict[int, dict] = {}
        self.lastUpdateTime: float = 0.0
        self.tutorialManager: tutorial.TutorialManager | None = None
    
    async def getData(self) -> None:
        global websocket
        if websocket is not None:
            response = await websocket.sendMessage(Message(str(websocket.player_id), "get", {}))
            if response is not None and isinstance(response, dict):
                content = response.get('content', {})
                obj_list = content.get('objects', [])
                if isinstance(obj_list, list):
                    self.dataList = obj_list
    
    def onScreenInfo(self, *args: Any) -> None:
        global websocket
        if websocket is not None and websocket.resopnse is not None:
            content = websocket.resopnse.get('content', {})
            dataList = content.get('objects', [])
            self.prevEntities = self.currEntities.copy()
            self.currEntities = {d['id']: d for d in dataList}
            self.lastUpdateTime = time.time()
    
    def setTitle(self, *args: Any) -> None:
        global websocket
        if websocket is not None and websocket.resopnse is not None:
            content = websocket.resopnse['content']
            self.titleInfo.clear()
            self.titleInfo.append({"title": fontChinese.render(str(content['title']), True, (19, 19, 19)), "duration": content['duration'], 'delay': content['duration']})
    
    def setLevelInfo(self, *args: Any) -> None:
        global websocket
        if websocket is not None and websocket.resopnse is not None:
            self.levelInfo = []
            self.levelInfo.append(fontChinese.render(str(websocket.resopnse['content']['level']), True, (19, 19, 19)))
    
    def draw_(self, *args: Any) -> None:
        global websocket
        #asyncio.run(self.getData())
        screen.fill((230, 230, 230))
        versionText = font.render(VERSION, True, (19, 19, 19))
        rect = versionText.get_rect()
        rect.topright = (WIDTH - 8, 8)
        screen.blit(versionText, rect)
        for titleDict in self.titleInfo:
            title: pygame.Surface = titleDict['title']
            rect = title.get_rect()
            rect.center = (WIDTH // 2, HEIGHT // 4)
            delay = titleDict['delay']
            if delay <= 1 * gametick:
                title.set_alpha(int(delay / (1 * gametick) * 255))
            screen.blit(title, rect)
            titleDict['delay'] -= 1
            if titleDict['delay'] <= 0:
                self.titleInfo.remove(titleDict)
        if self.tutorialManager is not None:
            for surface in self.tutorialManager.getAwaitingSurfaceList():
                rect = surface.get_rect()
                rect.center = (WIDTH // 2, HEIGHT // 3)
                screen.blit(surface, rect)
        if len(self.titleInfo) == 0:
            for info in self.levelInfo:
                rect = info.get_rect()
                rect.midtop = (WIDTH // 2, 8)
                screen.blit(info, rect)
        if websocket is not None:
            alpha = 0.0
            if self.lastUpdateTime > 0:
                alpha = min(1.0, (time.time() - self.lastUpdateTime) * gametick)
            for data in self.currEntities.values():
                prev = self.prevEntities.get(data['id'], data)
                drawX = prev['x'] + (data['x'] - prev['x']) * alpha
                drawY = prev['y'] + (data['y'] - prev['y']) * alpha
                drawRotation = prev['rotation'] + (data['rotation'] - prev['rotation']) * alpha
                image = imageMap.images[Images(data['image'])]
                image = pygame.transform.rotate(image, -drawRotation)
                rect = image.get_rect()
                rect.center = (int(drawX), int(drawY))
                screen.blit(image, rect)
                if 'isReady' in data:
                    if data['isReady'] == True and ResourcesLoader.currGameState == GameState.mainMenu:
                        tick = imageMap.images[Images.ready]
                        rect = tick.get_rect()
                        rect.center = (int(drawX), int(drawY - 48))
                        screen.blit(tick, rect)
                if 'name' in data:
                    name = littleFont.render(data['name'], True, (19, 19, 19))
                    rect = name.get_rect()
                    rect.center = (int(drawX), int(drawY + 32))
                    screen.blit(name, rect)
                if 'player_id' in data:
                    try:
                        if data['player_id'] == websocket.player_id:
                            if self.drawTriangle == True:
                                pygame.draw.polygon(screen, (0, 192, 0), [(int(drawX), int(drawY + 24)), (int(drawX - 4), int(drawY + (12*1.732))), (int(drawX + 4), int(drawY + (12*1.732)))])
                            stateBar = pygame.Surface((WIDTH, 64))
                            stateBar.fill((192, 192, 192))
                            stateBar.blit(font.render(f"Player {data['name']}", True, (19, 19, 19)), (0, 4))
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
        self.soundData: str = ''
    
    def play(self, *args: Any) -> None:
        global websocket
        if websocket is not None and websocket.resopnse is not None:
            self.soundData = websocket.resopnse['content']['sound']
            self.play_once(self.soundData)

    def play_once(self, name: str) -> None:
        pygame.mixer.Sound.play(soundMap.sounds[Sounds(name)])

class MusicLoader:
    def __init__(self) -> None:
        self.data: int = 0
        self.msc: MusicIntro | None = None
        self.historyData: int | None = None

    def play(self, *args: Any) -> None:
        global websocket
        if websocket is not None and websocket.resopnse is not None:
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
    currGameState: GameState = GameState.mainMenu
    def __init__(self) -> None:
        self.imageLoader = ImageLoader()
        self.soundLoader = SoundLoader()
        self.musicLoader = MusicLoader()
        if hasJoystick:
            self.imageLoader.operationText = joyStickOperationTexts
        self.processMappingTable: dict[str, Any] = {
            "screen_info": self.imageLoader.onScreenInfo,
            "game_state_changed": self.on_gamestate_changed,
            "playsound": self.soundLoader.play,
            "load_level": self.imageLoader.setLevelInfo,
            "set_title": self.imageLoader.setTitle,
        }
    
    def process(self, responseMessage: Message) -> None:
        if responseMessage.type in self.processMappingTable:
            self.processMappingTable[responseMessage.type](responseMessage)
    
    def on_gamestate_changed(self, responseMessage: Message) -> None:
        ResourcesLoader.currGameState = GameState(responseMessage.content['state'])
        self.musicLoader.play()

'''program launching configuration'''

async def launchClient() -> None:
    global websocket
    websocket = client.Client(0, guide.launchArg['ip'], guide.launchArg['port'], guide.launchArg['playerName'])
    await asyncio.gather(*[websocket.connect()])

guide.gameguide()
if guide.launchArg["mode"] == "single":
    gamemode = GameMode.single
    websocket = client.SinglePlayerClient(0, game, guide.launchArg['playerName'])
    game = Game(websocket.msgQueue)
    websocket.game = game
    websocket.newPlayer()
    if game is not None and game.board.players:
        game.board.players[0].isReady = True
elif guide.launchArg["mode"] == "multi":
    gamemode = GameMode.multiJoin
    thread = threading.Thread(target=lambda:asyncio.run(launchClient()))
    thread.start()
else:
    sys.exit()

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
if pygame.joystick.get_count() > 0:
        hasJoystick = True
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
font = pygame.font.SysFont("Consola", 30)
fontChinese = pygame.font.SysFont("SimHei", 30)
littleFont = pygame.font.SysFont("Consola", 20)
pygame.mouse.set_visible(False)
pygame.display.set_caption(TITLE)
#pygame.display.set_icon(pygame.image.load(".\\images\\game.ico"))

resourcesLoader = ResourcesLoader()

def update() -> None:
    pass

def on_key_down(key: int) -> None:
    global websocket
    if websocket is not None:
        asyncio.run(websocket.sendMessage(Message(str(websocket.player_id), "keyDown", {"key": key})))

def on_key_up(key: int) -> None:
    global websocket
    if websocket is not None:
        asyncio.run(websocket.sendMessage(Message(str(websocket.player_id), "keyUp", {"key": key})))

def on_joyaxis(axis: int, value: float) -> None:
    global lastJoyAxis, websocket
    if websocket is not None:
        asyncio.run(websocket.sendMessage(Message(str(websocket.player_id), "joyAxis", {"axis": axis, "value": value})))

def on_hatmotion(value: list[int]) -> None:
    global websocket
    if websocket is not None:
        asyncio.run(websocket.sendMessage(Message(str(websocket.player_id), "joyHat", {"value": value})))

async def on_quit() -> None:
    if websocket != None:
        await websocket.disconnect()
    sys.exit()

def mainloop() -> None:
    global hasJoystick, lastJoyAxis
    GAME_TICK_MS: float = 1000.0 / gametick
    tickAccumulator: float = 0.0

    tutorial_manager: tutorial.TutorialManager | None = None
    if gamemode == GameMode.single and game is not None:
        tutorial_manager = tutorial.TutorialManager(game, websocket.msgQueue, font, fontChinese) if websocket is not None else None
        if tutorial_manager is not None:
            resourcesLoader.imageLoader.tutorialManager = tutorial_manager
            tutorial_manager.start()

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
        dt = clock.tick(60)
        tickAccumulator += dt

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
            if hasJoystick:
                currJoyAxis = (joystick.get_axis(0), joystick.get_axis(1))
                if abs(currJoyAxis[0] - lastJoyAxis[0]) > 0.2:
                    on_joyaxis(0, currJoyAxis[0])
                    lastJoyAxis[0] = currJoyAxis[0]
                if abs(currJoyAxis[1] - lastJoyAxis[1]) > 0.2:
                    on_joyaxis(1, currJoyAxis[1])
                    lastJoyAxis[1] = currJoyAxis[1]
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:
                        on_key_down(pygame.K_c)
                        pygame.mixer.Sound.play(soundMap.sounds[Sounds.prepare])
                    if event.button == 1:
                        on_key_down(pygame.K_z)
                    if event.button == 2:
                        on_key_down(pygame.K_e)
                    if event.button == 3:
                        on_key_down(pygame.K_SPACE)
                if event.type == pygame.JOYBUTTONUP:
                    if event.button == 0:
                        on_key_up(pygame.K_c)
                        pygame.mixer.Sound.play(soundMap.sounds[Sounds.unprepare])
                    if event.button == 3:
                        on_key_up(pygame.K_SPACE)
                    if event.button == 1:
                        resourcesLoader.imageLoader.drawTriangle = not resourcesLoader.imageLoader.drawTriangle
                if event.type == pygame.JOYHATMOTION:
                    on_hatmotion(event.value)

        while tickAccumulator >= GAME_TICK_MS:
            tickAccumulator -= GAME_TICK_MS
            if isinstance(websocket, client.SinglePlayerClient) and game is not None:
                if tutorial_manager is not None and tutorial_manager.isActive():
                    tutorial_manager.update()
                    websocket.update()
                    for player in game.board.players:
                        if player.health < 10:
                            player.health = 10
                else:
                    websocket.update()
                    game.detectLevelState()

        process()
        if websocket is not None:
            resourcesLoader.imageLoader.draw_()
        pygame.display.flip()

if guide.launchArg["mode"] == "none":
    sys.exit()
else:
    pygame.mixer.music.load(musicMap.music[Music("mainmenu")])
    pygame.mixer.music.play(-1)
    mainloop()
    sys.exit()
