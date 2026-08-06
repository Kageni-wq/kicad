import math
from typing import List, Tuple, Dict

def PolygonArea(points: List[Tuple]) -> float:
    """Расчет площади контура

    Args:
        points (List): Точки контура

    Returns:
        float: Полученная площадь по формуле Гаусса
    """
    area = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        area += x1*y2 - x2*y1
    return area / 2.0

def InterpolateArc(start: Tuple, end: Tuple, center: Tuple, steps: int = 10) -> List[Tuple]:
    """Аппроксимация дуги набором точек

    Args:
        start (Tuple): _description_
        end (Tuple): _description_
        center (Tuple): _description_
        steps (int, optional): _description_. Defaults to 10.

    Returns:
        List[Tuple]: _description_
    """
    (x1, y1), (x2, y2), (cx, cy) = start, end, center
    r = math.hypot(x1 - cx, y1 - cy)
    a1 = math.atan2(y1 - cy, x1 - cx)
    a2 = math.atan2(y2 - cy, x2 - cx)
    
    # normalize
    if a2 < a1:
        a2 += 2*math.pi
    points = []
    for i in range(steps+1):
        a = a1 + (a2 - a1) * i / steps
        x = cx + r*math.cos(a)
        y = cy + r*math.sin(a)
        if i == 0:
            points.append(start)
        elif i == steps:
            points.append(end)
        else:
            points.append((round(x, 2), round(y, 2)))
    
    return points

def InterpolateCircle(center: Tuple[float, float], radius: Tuple[float, float], start_angle: float = 0.0, end_angle: float = 2*math.pi, steps: int = 32) -> List[Tuple[float, float]]:
    """Аппроксимация по центру и радиусу для окружности (набор точек)

    Args:
        center (Tuple[float, float]): Координаты центра окружности
        radius (Tuple[float, float]): Координаты радиуса окружности (крайняя точка окружности)
        start_angle (float, optional): Стартовый угол построения. Defaults to 0.0.
        end_angle (float, optional): Конечный угол построения. Defaults to 2*math.pi.
        steps (int, optional): Количество точек. Defaults to 32.

    Returns:
        List[Tuple[float, float]]: Набор точек для окружности
    """
    cx, cy = center
    rx, ry = radius
    rad = math.sqrt((cx - rx)**2 + (cy - ry)**2)
    points = []
    
    if end_angle < start_angle:
        end_angle += 2*math.pi
    
    total_angle = end_angle - start_angle
    if abs(total_angle - 2*math.pi) < 1e-6:
        steps_for_circle = steps
    else:
        steps_for_circle = max(2, int(steps*total_angle / (2*math.pi)))
        
    for i in range(steps_for_circle + 1):
        angle = start_angle + total_angle* i / steps_for_circle
        x = cx + rad * math.cos(angle)
        y = cy + rad * math.sin(angle)
        points.append((round(x, 2), round(y, 2)))
    
    return points

def BuildSquare(start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple]:
    (x1, y1), (x2, y2) = start, end
    points = []
    
    points.append((round(x1, 2), round(y1, 2)))
    points.append((round(x2, 2), round(y1, 2)))
    points.append((round(x2, 2), round(y2, 2)))
    points.append((round(x1, 2), round(y2, 2)))
    
    return points
    

def BuildPolys(segments: List[Tuple], arcs: List[Tuple] = None, circles: List[Tuple] = None, squares: List[Tuple] = None, edges_poly: List[Tuple] = None) -> Dict[str, List[Tuple]]:
    """Собирает полигоны из сегментов, дуг, кругов
    Args:
        segments (List[Tuple]): Координаты сегментов (в основном линии)
        arcs (List[Tuple], optional): Координаты дуг. Defaults to None.

    Returns:
        Dict[str, List[Tuple]]: Словарь с внешним полигоном и внутренними вырезами
    """
    
    def round_point(p: Tuple) -> Tuple:
        return (round(p[0], 2), round(p[1], 2))
    
    all_segments = []
    
    for x1, y1, x2, y2 in segments:
        all_segments.append((round_point((x1, y1)), round_point((x2, y2))))
        
    if arcs:
        for x1, y1, x2, y2, c1, c2 in arcs:
            arc_points = InterpolateArc(round_point((x1, y1)), round_point((x2, y2)), round_point((c1, c2)))
            for i in range(len(arc_points) - 1):
                all_segments.append((arc_points[i], arc_points[i + 1]))
                
    unused = all_segments[:]
    polys = []

    while unused:
        seg = unused.pop(0)
        poly = [seg[0], seg[1]]
        extended = True
        
        while extended:
            extended = False
            for s in unused[:]:
                if poly[-1] == s[0]:
                    poly.append(s[1])
                    unused.remove(s)
                    extended = True
                elif poly[-1] == s[1]:
                    poly.append(s[0])
                    unused.remove(s)
                    extended = True
                elif poly[0] == s[0]:
                    poly.insert(0, s[1])
                    unused.remove(s)
                    extended = True
                elif poly[0] == s[1]:
                    poly.insert(0, s[0])
                    unused.remove(s)
                    extended = True
        if poly[0] == poly[-1]:
            polys.append(poly)
    
    if circles:
        for circle in circles:
            circle_points = InterpolateCircle(round_point((circle[0], circle[1])), round_point((circle[2], circle[3])))
            polys.append(circle_points)
    
    if squares:
        for square in squares:
            square_points = BuildSquare(round_point((square[0], square[1])), round_point((square[2], square[3])))
            polys.append(square_points)
            
    if edges_poly:
        for p in edges_poly:
            polys.append(p)
    
    return polys

def GetType(polygons: List):
    """Разбить полигоны на внешний контур и внутренние вырезы

    Args:
        polygons (List): Список полигонов на слое Edge.Cuts

    """
    areas = [abs(PolygonArea(p)) for p in polygons]
    if areas:
        max_idx = areas.index(max(areas))
        outer = polygons[max_idx]
        inner = [c for i, c in enumerate(polygons) if i != max_idx]
        
        return outer, inner
    else:
        return None, None