import re
import wx
import pcbnew

from typing import Dict, List

def _parse_color_string(color_str: str):
    """Парсит строку цвета формата rgb(r,g,b) или rgba(r,g,b,a) в wx.Colour"""
    if not color_str:
        return None
            
    try:
        color_str = color_str.strip()
            
        # Parse rgb(r,g,b)
        if color_str.startswith('rgb('):
            match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
            if match:
                r, g, b = map(int, match.groups())
                return wx.Colour(r, g, b)
            
        # Parse rgba(r,g,b,a)
        elif color_str.startswith('rgba('):
            match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', color_str)
            if match:
                r, g, b, a = match.groups()
                r, g, b = map(int, (r, g, b))
                a = float(a)

                return wx.Colour(r, g, b)
            
        # Parse hex
        elif color_str.startswith('#'):
            return wx.Colour(color_str)
                
    except Exception as e:
        print(f"Ошибка парсинга цвета {color_str}: {e}")
            
    return None

def create_layer_colors_from_json(json_color: Dict, active_layers: List) -> Dict:
    """Создает словарь цветов слоев на основе json_color"""
    layer_colors = {}
        
    # Get color copper from board.copper
    if 'board' in json_color and 'copper' in json_color['board']:
        copper_colors = json_color['board']['copper']
            
        # Main layers
        layer_mapping = {
            active_layers[0]: 'f',      # Front layer
            active_layers[-1]: 'b',      # Bottom layer
        }
            
        # Inner layers In1.Cu, In2.Cu etc.
        for id, item in enumerate(active_layers, 0):
            if pcbnew.IsInnerCopperLayer(pcbnew.GetBoard().GetLayerID(item)):
                layer_name = item
                color_key = f'in{id}'
                layer_mapping[layer_name] = color_key
            
        for layer_name, color_key in layer_mapping.items():
            if isinstance(copper_colors, dict) and color_key in copper_colors:
                color_str = copper_colors[color_key]
                color = _parse_color_string(color_str)
                if color:
                    layer_colors[layer_name] = color

    if not layer_colors and 'gerbview' in json_color and 'layers' in json_color['gerbview']:
        gerbview_layers = json_color['gerbview']['layers']
        layer_names = ['F.Cu', 'B.Cu'] + [f'In{i}.Cu' for i in range(1, len(gerbview_layers)-1)]
            
        for i, layer_name in enumerate(layer_names):
            if i < len(gerbview_layers):
                color_str = gerbview_layers[i]
                color = _parse_color_string(color_str)
                if color:
                    layer_colors[layer_name] = color
        
    non_copper_mapping = {
        'F.Silks': ('board', 'f_silks'),
        'B.Silks': ('board', 'b_silks'),
        'F.Mask': ('board', 'f_mask'),
        'B.Mask': ('board', 'b_mask'),
        'F.Paste': ('board', 'f_paste'),
        'B.Paste': ('board', 'b_paste'),
        'F.CrtYd': ('board', 'f_crtyd'),
        'B.CrtYd': ('board', 'b_crtyd'),
        'F.Fab': ('board', 'f_fab'),
        'B.Fab': ('board', 'b_fab'),
        'F.Adhes': ('board', 'f_adhes'),
        'B.Adhes': ('board', 'b_adhes'),
        'Edge.Cuts': ('board', 'edge_cuts'),
        'Margin': ('board', 'margin'),
        'Eco1.User': ('board', 'eco1_user'),
        'Eco2.User': ('board', 'eco2_user'),
        'Cmts.User': ('board', 'cmts_user'),
        'Dwgs.User': ('board', 'dwgs_user'),
    }
        
    for layer_name, (section, color_key) in non_copper_mapping.items():
        if section in json_color and color_key in json_color[section]:
            color_str = json_color[section][color_key]
            color = _parse_color_string(color_str)
            if color:
                layer_colors[layer_name] = color
        
    # Add User layers
    for i in range(1, 46):
        user_layer = f'User.{i}'
        color_key = f'user_{i}'

        for section in ['board', 'schematic', '3d_viewer']:
            if section in json_color and color_key in json_color[section]:
                color_str = json_color[section][color_key]
                color = _parse_color_string(color_str)
                if color:
                    layer_colors[user_layer] = color
                    break
        
    return layer_colors
    
