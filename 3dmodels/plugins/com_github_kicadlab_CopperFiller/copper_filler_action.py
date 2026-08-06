import os
import pcbnew, wx
import json
from pathlib import Path
import platform
import time
import psutil
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree

from .ui.action_dialog import CopperFillerDialog
from .ui.info_dialog import InfoDialog
from .locale import init_locale
from .core.utils import MmToMkr, NmToMkr, MkrToNm, RoundCoordsTransform
from .logger import Logger
from .core.preprocessing import GetZones, GetEdgeContours, GetMasks, GetTracks, GetPads, GetVias, GetText
from .core.edge_cuts_utils import BuildPolys, GetType
from .core.clipping import ShapeClipper

class CopperFillerPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        """Функция стандартной инициализации плагина
        Returns:
            NoReturn: Без возвращаемого значения
        """
        self.name = "Copper Filler"
        self.category = "plugins"
        self.description = "Fill circuit with copper on active layer"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'data', 'images', 'icon.png')

    def Run(self):
        init_locale(pcbnew.GetLanguage()) # Enable localization

        self.logger = Logger(dir=self._get_log_dir())
        self.logger.setup_logger() # Init logger
        try:
            self.logger._info(_("START PLUGIN COPPER FILLER"))

            self.logger._info(_("Get board classes"))
            board_classes = {}
            with open(os.path.join(os.path.dirname(__file__), 'data', 'json', 'board_class.json')) as json_file:
                board_classes = json.load(json_file)
                
            board = pcbnew.GetBoard()
            self.logger._info(_("Board: {board}").format(board=board.GetFileName())) # Project
            self.logger._info(_("System {system}, version {version}").format(system=platform.system(), version=platform.version())) # System 
            self.logger._info(_("Kicad version {version}").format(version=pcbnew.Version())) #ver kicad
            self.logger._info(_("Processor {proc}, RAM {ram}").format(proc=platform.processor(), ram=round(psutil.virtual_memory().total / (1024**3), 0))) #proc, ram
 
            copper_layers = {
                        id : board.GetLayerName(l) 
                        for id, l in enumerate(board.GetLayerSet().Seq()) 
                        if pcbnew.IsCopperLayer(l)}
            layers = sorted(copper_layers.items(), key=lambda x: (x[1] == copper_layers[2], x[0]))

            settings_file = os.path.join(os.path.dirname(pcbnew.GetBoard().GetFileName()), 'settings.json')

            color_settings = os.path.join(pcbnew.GetSettingsManager().GetColorSettingsPath(), 'user.json')
            if(not os.path.exists(color_settings)):
                color_settings = os.path.join(os.path.dirname(__file__), 'data', 'json', 'user.json')

            self.logger._info(_("Show setting dialog"))
            pcb_frame = next(x for x in wx.GetTopLevelWindows() if x.GetName() == "PcbFrame")
            params = {}

            dialog = CopperFillerDialog(
                parent=pcb_frame, 
                active_layers=list(name for _, name in layers), 
                board_class=board_classes,
                settings=settings_file,
                colors=color_settings
                )
            
            if dialog.ShowModal() != wx.ID_OK:
                dialog.Destroy()
                self.logger._warning(_("User cancelled operation!"))
                return
            else:
                params = dialog.GetValues()
                if dialog.save_checkBox.GetValue():
                    try:
                        with open(settings_file, 'w', encoding='utf-8') as f:
                            json.dump(params, f, indent=4, ensure_ascii=False)
                        wx.MessageBox(_("Settings are saved in {settings_file}").format(settings_file=settings_file), "Copper Filler", wx.OK | wx.ICON_INFORMATION)
                    except Exception as e:
                        wx.MessageBox(_("Error while saving settings: {e}").format(e=e), "Copper Filler", wx.OK | wx.ICON_ERROR)

                params["size_mm"] = MmToMkr(params["size_mm"])
                params["shift_x"] = MmToMkr(params["shift_x"])
                params["shift_y"] = MmToMkr(params["shift_y"])
                params["element_clearance"] = MmToMkr(params["element_clearance"])
                params["object_clearance"] = MmToMkr(params["object_clearance"])
            
            dialog.Destroy()

            progress_dialog = wx.ProgressDialog(
                    "Copper Filler",
                    "Инициализация плагина...",
                    maximum=100,
                    parent=pcb_frame,
                    style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME
                    )
            progress_dialog.Update(0)

            start_total = time.time()

            self.logger._info(_(
                                """
                                Filler Settings:
                                \tLayer: {layer_name}
                                \tShape: {shape}
                                \tSize: {size} µm
                                \tDensity: {density} %
                                \tClearance: {clearance} µm
                                \tOffset X: {offset_x} µm
                                \tOffset Y: {offset_y} µm
                                """
                                ).format(
                                    layer_name=params['layer_name'], 
                                    shape=params['kind'], 
                                    size=params['size_mm'], 
                                    density=params['density'],
                                    clearance=params['element_clearance'],
                                    offset_x=params['shift_x'],
                                    offset_y=params['shift_y']))

            board_margin = params["object_clearance"]

            self._update_progress(progress_dialog, 15, _("Get Edge_Cuts..."))
            start_time = time.time()
            edges = GetEdgeContours(board, pcbnew.Edge_Cuts)
            edge_cuts = BuildPolys(edges['lines'], edges['arcs'], edges['circles'], edges['squares'], edges['polys'])
            outer, inner = GetType(edge_cuts)
            if outer is None:
                raise Exception(_("Failed to obtain the board edges. Check for closed edges in the Edge.Cuts layer"))
            edge_time = time.time() - start_time
            self.logger._info(_("Get Edge_Cuts: {edge_time:.3f} sec").format(edge_time=edge_time))

            outer = transform(RoundCoordsTransform, Polygon(outer).buffer(-board_margin))
            inner = unary_union([transform(RoundCoordsTransform, Polygon(inner_poly).buffer(board_margin)) for inner_poly in inner])

            self._update_progress(progress_dialog, 20, _("Get zones..."))
            start_time = time.time()
            zones = GetZones(board, params['layer_name'], board_margin)
            zones_time = time.time() - start_time
            self.logger._info(_("Get zones: {zones_time:.3f} sec").format(zones_time=zones_time))
            
            self._update_progress(progress_dialog, 25, _("Get masks..."))
            start_time = time.time()
            masks = GetMasks(board, params['layer_name'], board_margin)
            masks_time = time.time() - start_time
            self.logger._info(_("Get masks: {masks_time:.3f} sec").format(masks_time=masks_time))

            self._update_progress(progress_dialog, 30, _("Get tracks..."))
            start_time = time.time()
            tracks, diff_tracks = GetTracks(board, params['layer_name'], board_margin, params['element_clearance'])
            tracks_time = time.time() - start_time
            self.logger._info(_("Get tracks: {tracks_time:.3f} sec").format(tracks_time=tracks_time))

            self._update_progress(progress_dialog, 35, _("Get pads..."))
            start_time = time.time()
            pads = GetPads(board, params['layer_name'], board_margin)
            pads_time = time.time() - start_time
            self.logger._info(_("Get pads: {pads_time:.3f} sec").format(pads_time=pads_time))

            self._update_progress(progress_dialog, 40, _("Get vias..."))
            start_time = time.time()
            vias = GetVias(board, params['layer_name'], board_margin)
            vias_time = time.time() - start_time
            self.logger._info(_("Get vias: {vias_time:.3f} sec").format(vias_time=vias_time))

            self._update_progress(progress_dialog, 43, _("Get text..."))
            start_time = time.time()
            text = GetText(board, params['layer_name'], board_margin)
            text_time = time.time() - start_time
            self.logger._info(_("Get text: {text_time:.3f} sec").format(text_time=text_time))

            edges_bbox = board.GetBoardEdgesBoundingBox()

            for zone in board.Zones():
                if board.GetLayerID(pcbnew.LayerName(zone.GetLayer())) == board.GetLayerID(params['layer_name']):
                    if zone.GetZoneName() == 'EmptySpace':
                        board.Remove(zone)
                    
            main_zone = pcbnew.ZONE(board)
                    
            main_zone_edges = {
                                'start_x': NmToMkr(edges_bbox.GetPosition().x),
                                'start_y': NmToMkr(edges_bbox.GetPosition().y),
                                'end_x': NmToMkr(edges_bbox.GetPosition().x + edges_bbox.GetWidth()),
                                'end_y': NmToMkr(edges_bbox.GetPosition().y + edges_bbox.GetHeight())
                            }

            element_diam = params['size_mm']
            step = self.StepFromDensity(params['density'], params['size_mm'])
                                
            if step < params['element_clearance']:
                step = params['element_clearance']

            board_width = main_zone_edges['end_x'] - main_zone_edges['start_x']
            board_height = main_zone_edges['end_y'] - main_zone_edges['start_y']
            self.logger._info(_("Board size: {board_width:.1f} x {board_height:.1f} µm").format(board_width=board_width, board_height=board_height))
            self.logger._info(_("Element size: {element_diam} µm, step: {step:.3f} µm").format(element_diam=element_diam, step=step))
                    
            self.logger._info(_("START MAIN LOOP"))
            start_fill_loop = time.time()
            total_shapes = 0
            clipped_shapes = 0
            clipper_total_time = []
            shape_creation_time = 0

            num_threads = max(1, min(10, int(psutil.cpu_count(logical=False))))
            self.logger._info(_("Proccessing Threads Count: {num_threads}").format(num_threads=num_threads))

            self._update_progress(progress_dialog, 45, _("Check pre-count shapes..."))
            total_estimated_shapes = self._estimate_total_shapes(main_zone_edges, params, step)
            self.logger._info(_("Pre-count shape: {total_estimated_shapes}").format(total_estimated_shapes=total_estimated_shapes))

            sections = self.SplitIntoSections(main_zone_edges, num_threads, element_diam, step)

            progress_per_section = int(40 / num_threads)
            completed_sections = 0

            progress_dialog.SetRange(100)

            self._update_progress(progress_dialog, 50, _("Start copper filling..."))

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for i in range(num_threads):
                    future = executor.submit(
                            self.ProcessSection,
                            sections[i], params, step,
                            i,  # section number
                            zones, outer, inner, masks, tracks, pads, vias, diff_tracks, text
                        )
                    futures.append(future)
                        
                all_shapes_polys = []  
                all_shape_outlines = []
                        
                for future in as_completed(futures):
                    try:
                        section_result = future.result(timeout=300)
                        all_shapes_polys.extend(section_result['shapes_polys'])
                        all_shape_outlines.extend(section_result['shape_outlines'])
                        total_shapes += section_result['total_shapes']
                        clipped_shapes += section_result['clipped_shapes']
                        shape_creation_time += section_result['shape_creation_time']
                        clipper_total_time.append(section_result['clipper_total_time'])
                                
                        completed_sections += 1
                        self._update_progress(progress_dialog, 50 + (completed_sections*progress_per_section),
                                                _("Fill copper... Section {completed_sections}/{num_threads}").format(completed_sections=completed_sections, num_threads=num_threads))
                                
                        self.logger._info(_("Section {section_id} ends: {total_shapes} elements, {clipped_shapes} added").format(
                            section_id=section_result['section_id'],
                            total_shapes=section_result['total_shapes'],
                            clipped_shapes=section_result['clipped_shapes']
                        ))
                    except Exception as e:
                        self.logger._error(_("Error while processing: {e}").format(e=str(e)))
                        raise
                        
                if all_shapes_polys:
                    self._update_progress(progress_dialog, 85, _("Checking isolated shapes..."))
                    start_isolated = time.time()
                    filtered_outlines, removed_count = self.FilterIsolatedShapes(
                        all_shape_outlines, all_shapes_polys, element_diam, step
                    )
                    isolated_time = time.time() - start_isolated
                    self.logger._info(_("Removed {removed_count} isolated shapes in {isolated_time:.3f} sec").format(
                        removed_count=removed_count, isolated_time=isolated_time
                    ))

                    clipped_shapes -= removed_count
                    for shape_outline in filtered_outlines:
                        main_zone.Outline().AddOutline(shape_outline)

                else:
                    for shape_outline in all_shape_outlines:
                        main_zone.Outline().AddOutline(shape_outline)
                    
            fill_loop_time = time.time() - start_fill_loop
            self.logger._info(_("MAIN LOOP ENDED"))
            self.logger._info(_("Main loop time: {fill_loop_time:.3f} sec").format(fill_loop_time=fill_loop_time))
            self.logger._info(_("Total shapes: {total_shapes}").format(total_shapes=total_shapes))
            self.logger._info(_("Clipped shapes: {clipped_shapes}").format(clipped_shapes=clipped_shapes))
            self.logger._info(_("Shape creation time: {shape_creation_time:.3f} sec").format(shape_creation_time=shape_creation_time))
            clipper_total_time = sum(clipper_total_time)/len(clipper_total_time)
            self.logger._info(_("Average clipper total time: {clipper_total_time:.3f} sec").format(clipper_total_time=clipper_total_time))
            self.logger._info(_("Average time to element: {a:.2f} msec").format(a=clipper_total_time/max(total_shapes, 1)*1000))
            self.logger._info(_("Added element persentage: {a:.1f}%").format(a=clipped_shapes/max(total_shapes, 1)*100))
                        
            self._update_progress(progress_dialog, 98, _("End zone..."))
            start_time = time.time()

            settings = pcbnew.ZONE_SETTINGS()
            settings.m_HatchGap = 500000
            settings.ExportSetting(main_zone, True)

            main_zone.SetLayer(board.GetLayerID(params['layer_name']))
            main_zone.SetNetCode(0)
            main_zone.SetZoneName('EmptySpace')
            main_zone.SetIsRuleArea(False)

            board.Add(main_zone) 
            filler = pcbnew.ZONE_FILLER(board)
            filler.Fill([main_zone])
            fill_time = time.time() - start_time
            self.logger._info(_("Add and fill zones: {fill_time:.3f} sec").format(fill_time=fill_time))
                    
            pcbnew.Refresh()
                    
            total_time = time.time() - start_total
                    
            self.logger._info(_("TOTAL INFORMATION"))
            self.logger._info(_("Total time: {total_time:.3f} sec").format(total_time=total_time))
            self.logger._info(_("Preproccessing time: {t:.3f} sec ({a:.1f}%)").format(
                t=total_time - fill_loop_time - fill_time,
                a=(total_time - fill_loop_time - fill_time)/total_time*100))
            self.logger._info(_("Main loop time: {fill_loop_time:.3f} sec ({a:.1f}%)").format(
                fill_loop_time=fill_loop_time,
                a=fill_loop_time/total_time*100
            ))
            self.logger._info(_("Zone fill: {fill_time:.3f} sec ({a:.1f}%)").format(
                fill_time=fill_time,
                a=fill_time/total_time*100
            ))
            self.logger._info(_(
                """
                    Preprocessing details:
                    \tEdge contours: {edge_time:.3f} sec
                    \tZones: {zones_time:.3f} sec
                    \tMasks: {masks_time:.3f} sec
                    \tTracks: {tracks_time:.3f} sec
                    \tPads: {pads_time:.3f} sec
                    \tVias: {vias_time:.3f} sec
                """
            ).format(
                edge_time=edge_time,
                zones_time=zones_time,
                masks_time=masks_time,
                tracks_time=tracks_time,
                pads_time=pads_time,
                vias_time=vias_time
            ))
            self.logger._info(_("END PLUGIN"))

            progress_dialog.Update(100, _("End!"))
            time.sleep(0.5)
            progress_dialog.Destroy()
                
            dialog = InfoDialog(parent=pcb_frame, total_time=total_time, shapes=total_shapes, clipped=clipped_shapes, log_dir=self._get_log_dir() / 'logs')
            dialog.ShowModal()
            dialog.Destroy()
            
        except InterruptedError as e:
            self.logger._warning(_("Operation cancelled by user: {e}").format(e=str(e)))
            progress_dialog.Destroy()
            wx.MessageBox(_("Operation cancelled by user"), "Copper Filler", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            self.logger._error(_("Critical error: {e}").format(e=str(e)))
            progress_dialog.Destroy()
            wx.MessageBox(_("Critical error: {e}").format(e=str(e)), "Copper Filler", wx.OK | wx.ICON_ERROR)


    def _get_log_dir(self) -> Path:
        log_dir = None
        if platform.system() == 'Windows':
            log_dir = Path(__file__).parent.absolute()
        elif platform.system() == 'Linux':
            home_dir = Path.home()
            log_dir = home_dir / ".kicad" / "logs" / "copper_filler"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

        return log_dir
    
    def _estimate_total_shapes(self, edges: Dict, params: Dict, step: float) -> int:
        """Estimate total number of shapes for progress bar"""
        width = edges['end_x'] - edges['start_x']
        height = edges['end_y'] - edges['start_y']

        cols_estimate = width / (params['size_mm'] + step)
        rows_estimate = height / (params['size_mm'] + step)

        cols = int(cols_estimate) + 1
        rows = int(rows_estimate) + 1
        
        return cols * rows
    
    def SplitIntoSections(self, coords: Dict[str, float], num_sections: int, element_diam: float,
                           clearance: float = 0.0) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        
        x_min, y_min = coords['start_x'], coords['start_y']
        x_max, y_max = coords['end_x'], coords['end_y']

        width = x_max - x_min

        elem_count = math.ceil(width / (element_diam + clearance))
        n_for_section =  math.ceil(elem_count / num_sections)

        start_x, start_y = x_min, y_min
        sections = []
        for i in range(num_sections):
            temp = dict()
            if i == num_sections-1:
                temp = {
                    'start_x': start_x,
                    'start_y': start_y,
                    'end_x': coords['end_x'],
                    'end_y': coords['end_y']
                }
            else:
                temp = {
                    'start_x': start_x,
                    'start_y': start_y,
                    'end_x': start_x + (element_diam + clearance)*n_for_section,
                    'end_y': coords['end_y']
                }
            sections.append(temp)
            start_x = start_x + (element_diam + clearance)*(n_for_section - 1)

        return sections
    
    def MakeShape(self, kind: str, diam: int, x, y):
        shape = pcbnew.SHAPE_LINE_CHAIN()
        if(kind == 'Круг' or kind == 'Circle'):
            #Fill from element_diam = 0.6mm
            radius = diam / 2
            num_points = 12
            for i in range(num_points):
                angle = 2 * 3.1415926 * i / num_points
                px = x + radius * math.cos(angle)
                py = y + radius * math.sin(angle)
                shape.Append(pcbnew.VECTOR2I(MkrToNm(px), MkrToNm(py)))
        elif(kind == 'Квадрат' or kind == 'Square'):
            #Fill from element_diam = 0.5mm
            shape.Append(MkrToNm(x), MkrToNm(y))  # up left
            shape.Append(MkrToNm(x), MkrToNm(y + diam))  # up right
            shape.Append(MkrToNm(x + diam), MkrToNm(y + diam))  # down right
            shape.Append(MkrToNm(x + diam), MkrToNm(y))  # down left
            
        shape.SetClosed(True)
        return shape
    
    def FromPolyToShapeLineChain(self, poly):
        chain = pcbnew.SHAPE_LINE_CHAIN()
        coords = list(poly.exterior.coords)
        
        for x,y in coords:
            chain.Append(pcbnew.VECTOR2I(int(MkrToNm(x)), int(MkrToNm(y))))
            
        return chain
    
    def StepFromDensity(self, density: int, side: float) -> float:
        d = float(density)/100.0
        step = side * ((1.0 - d)/ d)
        return step
    
    def ProcessSection(self, edges: Dict, params: Dict, step, section_id,
                        zones, outer, inner, masks, tracks, pads, vias, diff_tracks, text):
        """Processing one section of board"""

        shapes_polys = []
        shape_outlines = []
        total_shapes = 0
        clipped_shapes = 0
        clipper_total_time = 0
        shape_creation_time = 0
        row = 0

        section_edges = Polygon([
                (edges['start_x'], edges['start_y']),  # down left
                (edges['end_x'], edges['start_y']),    # down right
                (edges['end_x'], edges['end_y']),      # up right
                (edges['start_x'], edges['end_y']),    # up left
                (edges['start_x'], edges['start_y'])   # closing (optional)
            ])

        estimated_shapes_in_section = 0
        y = edges['start_y'] + params['shift_y']
        while y < edges['end_y']:
            x = edges['start_x'] + params['shift_x']
                
            while x < edges['end_x']:
                estimated_shapes_in_section += 1
                x += params['size_mm'] + step
            y += params['size_mm'] + step
            row += 1
        
        y = edges['start_y'] + params['shift_y']
        row = 0
        processed_shapes = 0
        
        while y < edges['end_y']:
            x = edges['start_x'] + params['shift_x']

            while x < edges['end_x']:
                total_shapes += 1
                processed_shapes += 1
                
                shape_start = time.time()
                shape_outline = self.MakeShape(params['kind'], params['size_mm'], x, y)
                shape_creation_time += time.time() - shape_start

                clipper_start = time.time()
                clipper = ShapeClipper(zones, section_edges, outer, inner, masks, tracks, pads, vias, diff_tracks, text)
                clipped = clipper.process_shape(shape_outline)
                clipper_time = time.time() - clipper_start
                clipper_total_time += clipper_time
                if clipped is not None:
                    clipped_shapes += 1
                    if isinstance(clipped, MultiPolygon):
                        for geom in clipped.geoms:
                            shape_outline_geom = self.FromPolyToShapeLineChain(geom)
                            shape_outlines.append(shape_outline_geom)
                            shapes_polys.append(geom)
                    else:
                        shape_outline_geom = self.FromPolyToShapeLineChain(clipped)
                        shape_outlines.append(shape_outline_geom)
                        shapes_polys.append(clipped)
                
                x += params['size_mm'] + step
            y += params['size_mm'] + step
            row += 1
        
        return {
            'shapes_polys': shapes_polys,
            'shape_outlines': shape_outlines,
            'total_shapes': total_shapes,
            'clipped_shapes': clipped_shapes,
            'section_id': section_id,
            'clipper_total_time': clipper_total_time,
            'shape_creation_time': shape_creation_time
        }
    
    def FilterIsolatedShapes(self, shape_outlines, shape_polys, element_diam, step):
        """
        Фильтрует изолированные фигуры.
        Фигура считается изолированной, если у нее нет соседей на расстоянии <= шаг + диаметр элемента.
        
        Args:
            shape_outlines: список SHAPE_LINE_CHAIN
            shape_polys: список полигонов shapely
            element_diam: диаметр элемента
            step: шаг между элементами
            
        Returns:
            tuple: (отфильтрованные shape_outlines, количество удаленных фигур)
        """
        if not shape_polys:
            return shape_outlines, 0
        
        centroids = []
        valid_indices = []
        
        for i, poly in enumerate(shape_polys):
            if poly.is_valid and not poly.is_empty:
                centroid = poly.centroid
                centroids.append(centroid)
                valid_indices.append(i)
        
        if len(centroids) < 2:
            if len(centroids) == 1:
                self.logger._info(_("Single shape detected - it will be removed as isolated"))
                return [], 1
            return shape_outlines, 0
        
        tree = STRtree(centroids)
        neighbor_distance = (element_diam + step) * 1.2
        has_neighbor = [False] * len(centroids)
        
        for i, centroid in enumerate(centroids):
            nearest_indices = tree.query(centroid.buffer(neighbor_distance)) 
            for j in nearest_indices:
                if i != j:
                    distance = centroid.distance(centroids[j])
                    if distance <= neighbor_distance:
                        has_neighbor[i] = True
                        has_neighbor[j] = True

        filtered_outlines = []
        removed_count = 0
        
        for idx, (outline, has_neigh) in enumerate(zip(shape_outlines, has_neighbor)):
            if has_neigh:
                filtered_outlines.append(outline)
            else:
                removed_count += 1
        
        self.logger._info(_("Isolated shapes filter: {removed} shapes removed, {kept} shapes kept").format(
            removed=removed_count, kept=len(filtered_outlines)
        ))
        
        return filtered_outlines, removed_count
    
    def _update_progress(self, progress_dialog, value, message=None):
        """Update progress bar"""
        if message:
            progress_dialog.Update(value, message)
        else:
            progress_dialog.Update(value)

        wx.YieldIfNeeded()

        if progress_dialog.WasCancelled():
            msg = "Операция отменена пользователем"
            self.logger._warning(msg)
            raise InterruptedError(msg)