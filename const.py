import math
import sympy as sp

pi: float = 3.14159
t = sp.Symbol('t')
currPos = {'x': sp.Symbol('x'), 'y': sp.Symbol('y')}
SCREENSIZE = (800, 600)
CAPACITY = 4
disappearAera = (-50, -50, SCREENSIZE[0]+50, SCREENSIZE[1]+50)
raceList: list = ["player", "enemy"]
projectileNameList: list = ['bullet', 'missile']
gametick: int = 1/30 #1gt = 1/30 sec

class Vector:
    def __init__(self, magnitude, angle) -> None:
        self.magnitude = magnitude
        self.angle = angle  # angle in radians
    
    def __str__(self) -> str:
        return f"Vector({self.magnitude}, {self.angle})"
    
    def __add__(self, other) -> "Vector":
        x1 = self.magnitude * math.cos(self.angle)
        y1 = self.magnitude * math.sin(self.angle)
        x2 = other.magnitude * math.cos(other.angle)
        y2 = other.magnitude * math.sin(other.angle)
        x = x1 + x2
        y = y1 + y2
        magnitude = math.sqrt(x**2 + y**2)
        angle = math.atan2(y, x)
        return Vector(magnitude, angle)
    
    def __sub__(self, other: "Vector") -> "Vector":
        x1 = self.magnitude * math.cos(self.angle)
        y1 = self.magnitude * math.sin(self.angle)
        x2 = other.magnitude * math.cos(other.angle)
        y2 = other.magnitude * math.sin(other.angle)
        x = x1 - x2
        y = y1 - y2
        magnitude = math.sqrt(x**2 + y**2)
        angle = math.atan2(y, x)
        return Vector(magnitude, angle)

class Quadtree:
    def __init__(self, boundary: tuple, capacity: int = CAPACITY) -> None:
        self.boundary: tuple = boundary
        self.capacity: int = capacity
        self.objects: list = []
        self.divided: bool = False
        self.nw = None
        self.ne = None
        self.sw = None
        self.se = None

    def subdivide(self) -> None:
        x, y, w, h = self.boundary
        hw = w / 2
        hh = h / 2
        self.nw = Quadtree((x, y, hw, hh), self.capacity)
        self.ne = Quadtree((x + hw, y, hw, hh), self.capacity)
        self.sw = Quadtree((x, y + hh, hw, hh), self.capacity)
        self.se = Quadtree((x + hw, y + hh, hw, hh), self.capacity)
        self.divided = True

    def insert(self, obj) -> bool:
        x, y, w, h = obj
        rect = self._center_to_rect(x, y, w, h)
        if not self._in_boundary(rect):
            return False
        if len(self.objects) < self.capacity:
            self.objects.append(obj)
            return True
        if not self.divided:
            self.subdivide()
        return (self.nw.insert(obj) or
                self.ne.insert(obj) or
                self.sw.insert(obj) or
                self.se.insert(obj))
    
    def _center_to_rect(self, x, y, w, h) -> tuple:
        return (x - w / 2, y - h / 2, w, h)

    def _in_boundary(self, obj) -> bool:
        x, y, w, h = self.boundary
        ox, oy, ow, oh = obj
        return not (ox + ow < x or ox > x + w or oy + oh < y or oy > y + h)

    def query(self, range_rect) -> list:
        results = []
        if not self._intersects(range_rect):
            return results
        for obj in self.objects:
            if self._intersects_rect(range_rect, obj):
                results.append(obj)
        if self.divided:
            results.extend(self.nw.query(range_rect))
            results.extend(self.ne.query(range_rect))
            results.extend(self.sw.query(range_rect))
            results.extend(self.se.query(range_rect))
        return results

    def _intersects(self, range_rect) -> bool:
        x, y, w, h = self.boundary
        rx, ry, rw, rh = range_rect
        return not (rx + rw < x or rx > x + w or ry + rh < y or ry > y + h)

    def _intersects_rect(self, rect1, rect2) -> bool:
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        return not (x1 + w1 < x2 or x1 > x2 + w2 or y1 + h1 < y2 or y1 > y2 + h2)
