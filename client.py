import asyncio
import json
import websockets
import server
from const import *
import random
from data import Message, Queue

class SinglePlayerClient:
    def __init__(self, player_id: int, game: server.Game | None = None, playerName: str = "{default}") -> None:
        self.player_id = player_id
        self.resopnse: dict | None = None
        self.isRunning = True
        self.playerName = playerName
        self.msgQueue = Queue()
        self.game: server.Game | None = game

    def newPlayer(self) -> None:
        if self.game is None:
            return
        player = server.Player(self.player_id)
        player.x = SCREENSIZE[0] / 2.0
        player.y = 2.0 / 3.0 * SCREENSIZE[1]
        player.image = Images.player1
        if self.playerName == "{default}":
            player.name = str(self.player_id)
        else:
            player.name = self.playerName
        self.game.board.addPlayer(player)

    async def disconnect(self) -> None:
        ...

    async def sendMessage(self, msg: Message) -> str | None:
        if self.game is None:
            return None
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
        if msg.type == 'joyAxis':
            player = self.game.board.findPlayer(int(msg.sender))
            if player != None:
                player.joystickAxisList[msg.content['axis']] = msg.content['value']
                if abs(msg.content['value']) < 0.2:
                    player.joystickAxisList[msg.content['axis']] = 0
        if msg.type == 'joyHat':
            player = self.game.board.findPlayer(int(msg.sender))
            if player != None:
                if msg.content['value'] == [0, 0]:
                    player.pressedKeyList.remove(Keys.w) if Keys.w in player.pressedKeyList else None
                    player.pressedKeyList.remove(Keys.s) if Keys.s in player.pressedKeyList else None
                    player.pressedKeyList.remove(Keys.a) if Keys.a in player.pressedKeyList else None
                    player.pressedKeyList.remove(Keys.d) if Keys.d in player.pressedKeyList else None
                else:
                    if msg.content['value'][0] == 1:
                        player.pressedKeyList.append(Keys.d)
                    if msg.content['value'][0] == -1:
                        player.pressedKeyList.append(Keys.a)
                    if msg.content['value'][1] == 1:
                        player.pressedKeyList.append(Keys.w)
                    if msg.content['value'][1] == -1:
                        player.pressedKeyList.append(Keys.s)
        return None

    def requestToResponse(self) -> None:
        self.resopnse = json.loads(str(self.msgQueue.pop()))

    def update(self) -> None:
        if self.game != None:
            self.game.update()

class Client:
    def __init__(self, player_id: int, ip: str = "localhost", port: int = 8765, playerName: str = "{default}") -> None:
        self.player_id = player_id
        self.ip = ip
        self.port = port
        self.playerName = playerName
        self.msgQueue = Queue()
        self.resopnse: dict | None = None
        self.isRunning = True
    
    async def sendMessage(self, msg: Message) -> dict | None:
        uri = f"ws://{self.ip}:{self.port}"
        async with websockets.connect(uri) as ws:
            await ws.send(str(msg))
            async for ws_message in ws:
                response = json.loads(ws_message)
                return response
        return None
    
    async def connect(self) -> None:
        uri = f"ws://{self.ip}:{self.port}"
        async with websockets.connect(uri) as ws:
            msg = Message(str(self.player_id), "connect", {"playerName": self.playerName})
            await ws.send(str(msg))
            async for ws_message in ws:
                game_state = json.loads(ws_message)
                if game_state["type"] == "connect":
                    self.player_id = game_state["content"]["player_id"]
                    print(f"player connected")
                    if self.player_id == -1:
                        self.isRunning = False
                    game_state = None
                if game_state is not None:
                    self.msgQueue.push(game_state)
                if not self.isRunning:
                    await ws.send(str(Message(str(self.player_id), "disconnect", {})))
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