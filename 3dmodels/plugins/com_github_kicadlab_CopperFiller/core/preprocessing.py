from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union, transform

from .utils import RoundCoordsTransform, NmToMkr

import logging
import pcbnew

from typing import Dict, List

logger = logging.getLogger('log')

def GetEdgeContours(board, layer) -> Dict[str, List]:
    edge_contours = {
                    'lines': [],
                    'squares': [],
                    'arcs': [],
                    'circles': [],
                    'polys': []
                    }
   
    for d in board.Drawings():
        if d.Type() != 5: # if not PCB_SHAPE_LINE
            continue
        if d.GetLayer() != layer:
            continue
        if d.GetShape() == 0: #line
            edge_contours['lines'].append((
                NmToMkr(d.GetStart().x), NmToMkr(d.GetStart().y), 
                NmToMkr(d.GetEnd().x), NmToMkr(d.GetEnd().y)
                ))
        elif d.GetShape() == 1: #square
            edge_contours['squares'].append((
                NmToMkr(d.GetStart().x), NmToMkr(d.GetStart().y), 
                NmToMkr(d.GetEnd().x), NmToMkr(d.GetEnd().y)
                ))
        elif d.GetShape() == 2: #arc
            edge_contours['arcs'].append((
                NmToMkr(d.GetStart().x), NmToMkr(d.GetStart().y), 
                NmToMkr(d.GetEnd().x), NmToMkr(d.GetEnd().y), 
                NmToMkr(d.GetCenter().x), NmToMkr(d.GetCenter().y)
                ))
        elif d.GetShape() == 3: #circle
            edge_contours['circles'].append((
                NmToMkr(d.GetStart().x), NmToMkr(d.GetStart().y), 
                NmToMkr(d.GetEnd().x), NmToMkr(d.GetEnd().y)
                ))
        elif d.GetShape() == 4: #polys
            poly = d.GetPolyShape()
            temp = []
            for i in range(poly.VertexCount()):
                temp.append((NmToMkr(poly.CVertex(i).x), NmToMkr(poly.CVertex(i).y)))
                
            edge_contours['polys'].append(temp)
        
    return edge_contours

def GetZones(board, layer_name: str, board_margin):
    logger.info(_("Get Zones"))
    zones = []
    zones_count = 0
    removed_zones = 0
    for zone in board.Zones():
        if zone.GetLayerSet() is not None:
            for l_z in zone.GetLayerSet().Seq():
                if board.GetLayerID(pcbnew.LayerName(l_z)) == board.GetLayerID(layer_name):
                    zones_count += 1
                    if zone.GetZoneName() == 'EmptySpace':
                        board.Remove(zone)
                        removed_zones += 1
                    
                    if zone.GetIsRuleArea():
                        version_kicad = int(pcbnew.Version().split(".")[0])
                        if version_kicad < 10:
                            if not zone.GetDoNotAllowCopperPour():
                                continue
                        else:
                            if not zone.GetDoNotAllowZoneFills():
                                continue
                    
                    zone_poly = Polygon((NmToMkr(zone.Outline().CVertex(i).x), NmToMkr(zone.Outline().CVertex(i).y)) for i in range(zone.Outline().VertexCount()))
                    zones.append(zone_poly)
    zones = unary_union([transform(RoundCoordsTransform, Polygon(zone_poly).buffer(board_margin)) for zone_poly in zones])
    logger.info(_("Zone count: {zones_count}, removed: {removed_zones}").format(zones_count=zones_count, removed_zones=removed_zones))
    
    return zones

def GetMasks(board, layer_name: str, board_margin):
    logger.info(_("Get Masks"))
    mask = None
    if board.GetLayerID(layer_name) == 0:
        mask = pcbnew.F_Mask
    elif board.GetLayerID(layer_name) == 2:
        mask = pcbnew.B_Mask
    
    masks = []
    if mask:
        masks = GetEdgeContours(board, mask)
        masks_count = len(masks['polys']) if 'polys' in masks else 0
        masks = unary_union([transform(RoundCoordsTransform, Polygon(m).buffer(board_margin)) for m in masks['polys']])
    else:
        masks = None
        masks_count = 0
    logger.info(_("Masks count: {masks_count}").format(masks_count=masks_count))

    return masks

def GetTracks(board, layer_name: str, clearance, element_clearance):
    logger.info(_("Get Tracks"))
    tracks = []
    diff_tracks_polygons = []
    tracks_count = 0
    diff_tracks_count = 0
    for track in board.GetTracks():
        if track.GetLayer() == board.GetLayerID(layer_name):
            tracks_count += 1

            start = track.GetStart()
            end = track.GetEnd()
            width_nm = track.GetWidth()
            net = track.GetNet()

            width_mkr = NmToMkr(width_nm)
            start_mkr = (NmToMkr(start.x), NmToMkr(start.y))
            end_mkr = (NmToMkr(end.x), NmToMkr(end.y))

            line = LineString([start_mkr, end_mkr])
                    
            buffer_distance = width_mkr / 2.0
            track_poly = line.buffer(buffer_distance, cap_style=3, join_style=2)

            is_diff_pair = False
            if net and hasattr(net, 'GetNetname'):
                netname = net.GetNetname()
                if netname.endswith('P') or netname.endswith('N'):
                    is_diff_pair = True
                    diff_tracks_count += 1

            if is_diff_pair:
                diff_tracks_polygons.append(track_poly)
                if element_clearance == 0.12:
                    diff_clearance = element_clearance * 5
                elif width_mkr > 0.2:
                    diff_clearance = width_mkr * 5
            else:
                tracks.append(track_poly)
            
    tracks = unary_union([transform(RoundCoordsTransform, Polygon(track_poly).buffer(clearance)) for track_poly in tracks])
    diff_tracks = unary_union([transform(RoundCoordsTransform, Polygon(track_poly).buffer(diff_clearance)) for track_poly in diff_tracks_polygons])

    logger.info(_("Tracks count: {tracks_count}").format(tracks_count=tracks_count))
            
    return tracks, diff_tracks

def GetPads(board, layer_name: str, clearance):
    logger.info(_("Get Pads"))
    pads = []
    pads_count = 0
    for pad in board.GetPads():
        if pad.GetLayerSet().Seq() is not None:
            for p in pad.GetLayerSet().Seq():
                if board.GetLayerID(pcbnew.LayerName(p)) == board.GetLayerID(layer_name):
                    pads_count += 1
                    poly = pcbnew.SHAPE_POLY_SET()
                    poly = pad.GetEffectivePolygon(board.GetLayerID(layer_name), 0)
                    pad_poly = Polygon((NmToMkr(poly.CVertex(i).x), NmToMkr(poly.CVertex(i).y)) for i in range(poly.VertexCount()))
                    pads.append(pad_poly)
                            
    pads = unary_union([transform(RoundCoordsTransform, Polygon(pad_poly).buffer(clearance)) for pad_poly in pads])
    logger.info(_("Pads count: {pads_count}").format(pads_count=pads_count))
    return pads

def _create_circle_polygon(center_x, center_y, radius, num_points=12):
    import math
        
    points = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))
        
    return Polygon(points)

def GetVias(board, layer_name: str, clearance):
    logger.info(_("Get Vias"))
    vias = []
    vias_count = 0
    for via in board.GetTracks():
        if via.GetLayerSet().Seq() is not None:
            for v in via.GetLayerSet().Seq():
                if board.GetLayerID(pcbnew.LayerName(v)) == board.GetLayerID(layer_name):
                    vias_count += 1
                    if via.Type() != pcbnew.PCB_VIA_T:
                        continue

                    via = via.Cast()
                    if via is None:
                        continue

                    layer_set = via.GetLayerSet()
                    if layer_set.Contains(board.GetLayerID(layer_name)):
                        pos = via.GetPosition()
                        diameter_nm = via.GetDrillValue() + via.GetWidth()  # Диаметр = отверстие + медь
                                
                        x_mkr = NmToMkr(pos.x)
                        y_mkr = NmToMkr(pos.y)
                        radius_mkr = NmToMkr(diameter_nm / 2.0) + clearance
                                
                        via_poly = _create_circle_polygon(x_mkr, y_mkr, radius_mkr, num_points=8)
                        vias.append(via_poly)
            
    vias = unary_union([transform(RoundCoordsTransform, Polygon(via_poly).buffer(clearance)) for via_poly in vias])
    logger.info(_("Vias count: {vias_count}").format(vias_count=vias_count))
    return vias

def GetText(board, layer_name: str, clearance):
    logger.info(_("Get Text Blocks"))
    text = []
    text_count = 0
    for item in board.Drawings():
        if isinstance(item, pcbnew.PCB_TEXT):
            for i in item.GetLayerSet().Seq():
                if board.GetLayerID(pcbnew.LayerName(i)) == board.GetLayerID(layer_name):
                    text_count += 1

                    poly = pcbnew.SHAPE_POLY_SET()
                    item.TransformShapeToPolygon(poly, board.GetLayerID(layer_name), 0, 0, 0)
                    text_poly = Polygon((NmToMkr(poly.CVertex(i).x), NmToMkr(poly.CVertex(i).y)) for i in range(poly.VertexCount()))
                    
                    text.append(text_poly)
    text = unary_union([transform(RoundCoordsTransform, Polygon(text_poly).buffer(clearance)) for text_poly in text])
    logger.info(_("Text count: {text_count}").format(text_count=text_count))
    return text
