import asyncio
import json
import websockets
import server
from const import *
import random
from data import Message, Queue

class SinglePlayerClient:
    def __init__(self, player_id: int, game = None, playerName = "{default}") -> None:
        self.player_id = player_id
        self.resopnse = None
        self.isRunning = True
        self.playerName = playerName
        self.msgQueue = Queue()
        self.game: server.Game = game
        self.tutorialStep = 0
        self.maxTutorialStep = 100
    
    def newPlayer(self) -> None:
        player = server.Player(self.player_id)
        player.x = SCREENSIZE[0] / 2
        player.y = 2/3 * SCREENSIZE[1]
        player.image = Images.player1
        if self.playerName == "{default}":
            player.name = str(self.player_id)
        else:
            player.name = self.playerName
        self.game.board.addPlayer(player)
    
    def isScreenEmpty(self) -> bool:
        return len(self.game.board.units) == 0

    def addTutorialUnit(self, unit: server.Unit) -> None:
        unit.x = SCREENSIZE[0] / 2
        unit.boundingBox = server.BoundingBox(56, 56)
        self.game.board.addUnit(unit, 'unit')
        unit.race = Race.enemy
    
    def setTutorialStep(self) -> None:
        self.tutorialStep += 1
        self.msgQueue.push(Message('server', 'setTutorial', {'step': self.tutorialStep, 'playerKeys': self.game.board.players[0].pressedKeyList}))
        if self.tutorialStep == 9:
            unit = server.EnemyBuilder().build()
            self.addTutorialUnit(unit)
        if self.tutorialStep == 12:
            unit = server.EnemyBuilder(inventory=[0], weapon=["Shotgun_normal"]).build()
            self.addTutorialUnit(unit)
        if self.tutorialStep == 15:
            for i in range(7):
                unit = server.EnemyBuilder(inventory=[i], image=random.choice([Images.ca, Images.enemy, Images.enemy2, Images.rship, Images.unit1])).build()
                self.addTutorialUnit(unit)
        if self.tutorialStep == 20:
            for player in self.game.board.players:
                if player.magabombQuantity == 0:
                    player.magabombQuantity += 1
            for _ in range(10):
                unit = server.EnemyBuilder(health=1000000, image=random.choice([Images.ca, Images.enemy, Images.enemy2, Images.rship, Images.unit1])).build()
                self.addTutorialUnit(unit)
        #self.resopnse = {'sender': 'server', 'type': 'setTutorial', 'content': {'step': self.tutorialStep, 'playerKeys': self.game.board.players[0].pressedKeyList}}

    async def disconnect(self) -> None:
        ...
    
    async def sendMessage(self, msg: Message) -> str:
        if msg.type == 'keyDown':
            player = self.game.board.findPlayer(int(msg.sender))
            if player != None:
                player.pressedKeyList.append(msg.content['key'])
        if msg.type == 'keyUp':
            player = self.game.board.findPlayer(int(msg.sender))
            if player != None:
                key = msg.content['key']
                if key in player.pressedKeyList:
                    player.pressedKeyList.remove(msg.content['key'])
    
    def requestToResponse(self) -> None:
        self.resopnse = json.loads(str(self.msgQueue.pop()))
    
    def update(self) -> None:
        if self.game != None:
            self.game.update()
            for i in self.game.board.players:
                if i.health < 10:
                    i.health = 10

class Client:
    def __init__(self, player_id: int, ip: str = "localhost", port: int = 8765, playerName: str = "{default}") -> None:
        self.player_id = player_id
        self.ip = ip
        self.port = port
        self.playerName = playerName
        self.msgQueue = Queue()
        self.resopnse = None
        self.isRunning = True
    
    async def sendMessage(self, message: Message) -> str:
        uri = f"ws://{self.ip}:{self.port}"
        async with websockets.connect(uri) as websocket:
            # 发送玩家动作
            await websocket.send(str(message))
            # 接收游戏状态
            async for message in websocket:
                response = json.loads(message)
                #print(f"msg response: {response}")
                return response
    
    async def connect(self) -> None:
        uri = f"ws://{self.ip}:{self.port}"
        async with websockets.connect(uri) as websocket:
            # 发送玩家动作
            msg = Message(str(self.player_id), "connect", {"playerName": self.playerName})
            await websocket.send(str(msg))
            # 接收游戏状态
            async for message in websocket:
                game_state = json.loads(message)
                #print(f"connect response: {game_state}")
                if game_state["type"] == "connect":
                    self.player_id = game_state["content"]["player_id"]
                    print(f"player connected")
                    if self.player_id == -1:
                        self.isRunning = False
                    game_state = None
                #self.resopnse = game_state
                self.msgQueue.push(game_state)
                if not self.isRunning:
                    await websocket.send(str(Message(str(self.player_id), "disconnect", {})))
                    return
    
    async def disconnect(self) -> None:
        self.isRunning = False

async def main() -> None:
    # 创建多个客户端
    c1 = Client(1)
    #c2 = Client(2)
    tasks = [c1.connect()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())