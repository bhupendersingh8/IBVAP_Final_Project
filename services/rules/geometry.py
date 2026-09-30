from typing import List
from .schemas import Point
from ..detection.schemas import BBox

def bbox_center(bbox: BBox) -> Point:
    return Point(x=bbox.center_x, y=bbox.center_y)

def bbox_ground_point(bbox: BBox) -> Point:
    """Bottom-center reference point for ground-contact intrusion detection (prevents false positives from upper body overlap)."""
    return Point(x=bbox.center_x, y=bbox.y2)

def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
    """Ray casting algorithm to check if a point is inside a polygon."""
    x, y = point.x, point.y
    inside = False
    n = len(polygon)
    
    p1 = polygon[0]
    for i in range(1, n + 1):
        p2 = polygon[i % n]
        if y > min(p1.y, p2.y):
            if y <= max(p1.y, p2.y):
                if x <= max(p1.x, p2.x):
                    if p1.y != p2.y:
                        xinters = (y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y) + p1.x
                    if p1.x == p2.x or x <= xinters:
                        inside = not inside
        p1 = p2
    return inside

def ccw(A: Point, B: Point, C: Point) -> bool:
    return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)

def line_segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """Check if line segment p1-p2 intersects with segment p3-p4."""
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
