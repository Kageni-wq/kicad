SCALE = 1e3

def MkrToNm(value: int) -> int:
    return int(value * SCALE)

def NmToMkr(value: int) -> int:
    return int(value / SCALE)

def MmToMkr(value: float) -> int:
    return int(value * SCALE)

def RoundCoordsTransform(x, y, z=None):
    if z is not None:
        return round(x, 2), round(y, 2), round(z, 2)
    return round(x, 2), round(y, 2)