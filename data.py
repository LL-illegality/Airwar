from enum import Enum
import json
from const import *

class Message:
    def __init__(self, sender: str, type_: str, content: dict) -> None:
        self.sender = sender
        self.type = type_
        self.content = content
    
    def __str__(self) -> str:
        ret = {'sender': self.sender, 'type': self.type, 'content': self.content}
        return json.dumps(ret)
    
    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def from_string(cls, msg: str) -> "Message":
        msg_obj = json.loads(msg)
        return cls(msg_obj['sender'], msg_obj['type'], msg_obj['content'])

class Queue:
    def __init__(self) -> None:
        self.queue = []
    
    def push(self, msg) -> None:
        self.queue.append(msg)
    
    def pop(self) -> Any:
        return self.queue.pop(0)
    
    def peek(self) -> Any:
        return self.queue[0]
    
    def isEmpty(self) -> bool:
        return len(self.queue) == 0
    
    def clear(self) -> None:
        self.queue.clear()
    
    def __len__(self) -> int:
        return len(self.queue)

class Vector:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
    
    def __invert__(self) -> float:
        #get the angle of the vector
        return math.atan2(self.y, self.x) * 180 / math.pi + 90
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented
        return self.x == other.x and self.y == other.y
    
    def __str__(self) -> str:
        return f"Vector({self.x}, {self.y})"
    
    def __add__(self, other: "Vector") -> "Vector":
        x1 = self.x
        y1=  self.y
        x2 = other.x
        y2 = other.y
        x0 = x1 + x2
        y0 = y1 + y2
        return Vector(x0, y0)
    
    def __sub__(self, other: "Vector") -> "Vector":
        x1 = self.x
        y1=  self.y
        x2 = other.x
        y2 = other.y
        x0 = x1 - x2
        y0 = y1 - y2
        return Vector(x0, y0)
    
    def __mul__(self, other: float) -> "Vector":
        x1 = self.x
        y1=  self.y
        x0 = x1 * other
        y0 = y1 * other
        return Vector(x0, y0)
    
    def __rmul__(self, other: float) -> "Vector":
        return self.__mul__(other)
