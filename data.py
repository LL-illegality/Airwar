import random
import asyncio
import math
from enum import Enum
import threading
import json
from const import *
from entities import *

class Board:...

class GameMode(Enum):
    single = 0
    multi = 1
    join = 2

class Server:
    def __init__(self, ip: str, port: int, board: Board) -> None:
        self.ip = ip
        self.port = port
        self.board = board
        self.thread = threading.Thread(target=self.serve)
    
    def run(self) -> None:
        self.thread.start()
    
    def serve(self) -> None:
        asyncio.run(self.serverMain())
    
    async def handleClient(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        data = await reader.read(100)
        message = data.decode()
        addr = writer.get_extra_info("peername")
        print(f"received {message!r} from {addr!r}")
        sendData = "none".encode()
        if message == "getBoard":
            sendData = json.dumps(self.board.dumpData(), skipkeys=True).encode()
        if message == "joinPlayer":
            player = Player(1)
            self.board.addPlayer(player)
        if message.startswith("move"):  # message format: move {id} {x} {y}
            splited = message.split(' ')
            player_id = int(splited[1])
            new_x = float(splited[2])
            new_y = float(splited[3])
            for player in self.board.playerList:# [index]
                if player.id == player_id:
                    player.x = new_x
                    player.y = new_y
                    break
        if message.startswith("shoot"):  #message format: shoot {shooterId} {bulletType} {shooterRace} {speed} {shootMode}
            splited = message.split(' ')
            player_id = int(splited[1])
            bulletType = splited[2]
            race = splited[3]
            speed = int(splited[4])
            mode = splited[5]
            self.board.unitShoot(player_id, bulletType, race, speed, mode)
        print(f"send {sendData}")
        writer.write(sendData)
        await writer.drain()
        writer.close()
    
    async def serverMain(self) -> None:
        self.server: asyncio.Server = await asyncio.start_server(
        self.handleClient, "127.0.0.1", self.port
    )
        addr = self.server.sockets[0].getsockname()
        print(f"Serving on {addr}")
        try:
            async with self.server:
                await self.server.serve_forever()
        except:
            return

class Client:
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
    
    async def tcp_echo_client(self, message: str):
        reader, writer = await asyncio.open_connection(self.ip, self.port)
        print(f"Send: {message!r}")
        writer.write(message.encode())
        await writer.drain()
        receive: bytes = await reader.read(-1)# todo: -1 or 100 not sure
        data = None
        string: str = receive.decode()
        if string != 'none':
            data = json.loads(string)
        print(f"Received: {data}")
        writer.close()
        await writer.wait_closed()
        return data
    
    def sendMessage(self, message: str):
        return asyncio.run(self.tcp_echo_client(message))

class Board(object):
    def __init__(self) -> None:
        self.playerList: list[Player] = []
        self.unitList: list[Unit] = []
        self.bulletList: list[Projectiles] = []
        self.currentId = -1
    
    def update(self) -> None:
        for i in self.playerList:
            if i.data['shootCooldown'] > 0:
                i.data['shootCooldown'] -= 1
        for i in self.bulletList:
            if i.isDisappeared == True:
                self.bulletList.remove(i)
            i.update(self.find(i.get('target')))
        for i in self.unitList:
            if i.isDisappeared == True:
                self.unitList.remove(i)
            if i.data['shootCooldown'] > 0:
                i.data['shootCooldown'] -= 1
            i.update()
            self.unitShoot(i.id, 'bullet', 'enemy', 2, 'auto')
    
    def generateId(self) -> int:
        self.currentId += 1
        if self.currentId == 1:
            self.currentId += 1
        return self.currentId
    
    def addPlayer(self, player: Player) -> bool:
        if len(self.playerList) < 2:
            self.playerList.append(player)
            self.generateId()
            return True
        else:
            return False
    
    def addUnit(self, unit: Projectiles | Unit) -> None:
        if type(unit) in list(Projectiles.projectilesTypes.values()):
            self.bulletList.append(unit)
        elif type(unit) == Unit:
            self.unitList.append(unit)
        else:
            return
        unit.id = self.generateId()
    
    def find(self, unitId: int) -> Player | Projectiles | Unit | None:
        for i in self.playerList:
            if i.id == unitId:
                return i
        for i in self.bulletList:
            if i.id == unitId:
                return i
        for i in self.unitList:
            if i.id == unitId:
                return i
        return None
    
    def unitShoot(self, unitId: int, bulletType: str, race: str, speed: int, mode: str) -> None:
        #mode: auto or forward
        shooter = self.find(unitId)
        if shooter == None:
            return
        if shooter.data['shootCooldown'] == 0:
            bullet = Projectiles.create(Projectiles(type = bulletType, race = race, owner = unitId, speed = speed, direction = 0, id = -1, x = shooter.x, y = shooter.y, acceleration = [0, 0]))
            shooter.data['shootCooldown'] = shooter.data['shootDuration']
            if type(bullet) == Bullet:
                if mode == 'auto':
                    if race == 'player':
                        target = random.choice(self.unitList)
                    if race == 'enemy':
                        target = random.choice(self.playerList)
                    bullet.data['direction'] = math.atan2(-(shooter.y-target.y),-(shooter.x-target.x))
                if mode == 'forward':
                    if race == 'player':
                        bullet.data['direction'] = 1.5*pi
                    if race == 'enemy':
                        bullet.data['direction'] = pi/2
            if type(bullet) == Missile:
                bullet.data['acceleration'] = [0.5, 1.5*pi]
                bullet.data['direction'] = 1.5*pi
                bullet.data['target'] = (random.choice(self.unitList).id) if len(self.unitList) > 0 else (-1)
            self.addUnit(bullet)
    
    def dumpData(self) -> dict:
        player_data = [player.__dict__ for player in self.playerList]
        unit_data = [unit.__dict__ for unit in self.unitList]
        bullet_data = [bullet.__dict__ for bullet in self.bulletList]
        return {
            'playerList': player_data,
            'unitList': unit_data,
            'bulletList': bullet_data
        }
    
    def loadData(self, data: dict) -> None:
        self.playerList = [Player(**player_data) for player_data in data['playerList']]
        self.bulletList = [Projectiles.create(Projectiles(**bullet_data)) for bullet_data in data['bulletList']]
        self.unitList = [Unit(**unit_data) for unit_data in data['unitList']]
