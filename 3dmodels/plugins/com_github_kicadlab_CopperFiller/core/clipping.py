from shapely.geometry import Polygon

from .utils import NmToMkr

class ShapeClipper:
    def __init__(self, zone, outer, counters, inner, masks, tracks, pads, vias, diff_tracks, text):
        self.outer = [outer, counters]
        self.boundings = [inner, zone, masks, tracks, pads, vias, diff_tracks, text]

    def clip_outside(self, shape: Polygon, outers):
        """
        То же, что zone: outer ограничивает допустимую область.
        """
        if shape.within(outers):
            return shape
        
        return None
    
    def clip_inside(self, shape: Polygon, boundings):
        if shape.within(boundings):
            return None  # all inside - delete

        if shape.intersects(boundings):
            return None

        return shape

    def process_shape(self, shape):
        shape_pts = Polygon(((NmToMkr(shape.CPoint(i).x), NmToMkr(shape.CPoint(i).y)) for i in range(shape.PointCount())))
        s = shape_pts
        for out in self.outer:
            s = self.clip_outside(s, out)
            if s == None:
                return None
        
        for bound in self.boundings:
            s = self.clip_inside(s, bound)
            if s == None:
                return None
        
        return s