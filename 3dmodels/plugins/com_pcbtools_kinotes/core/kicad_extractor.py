"""
KiCad Settings Extractor - CENTRALIZED extraction for ALL KiCad data.

This module is the SINGLE SOURCE OF TRUTH for extracting:
- Environment info (version, paths, install type)
- User variables (${REVISION}, ${COMPANY}, etc.)
- Session settings (autosave interval)
- Backup settings (project backup config)
- Appearance settings (theme, icons)
- Board info (loaded, filename, nets, footprints)
- Design settings (min track, clearance)
- Title block (date, revision, company)

Usage:
    from core.kicad_extractor import get_kicad_extractor
    
    extractor = get_kicad_extractor()
    
    # Get specific data
    env = extractor.get_environment()
    board = extractor.get_board_info()
    vars = extractor.get_user_variables()
    
    # Get everything
    all_data = extractor.get_all()
    
    # Quick access functions
    from core.kicad_extractor import (
        get_kicad_version,
        get_project_name,
        get_project_dir,
        is_board_loaded,
        get_autosave_interval_ms,
        get_user_variable
    )

Author: KiNotes Team (pcbtools.xyz)
License: Apache-2.0
SPDX-License-Identifier: Apache-2.0
"""

import os
import sys
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import debug_print for console logging
try:
    from .defaultsConfig import debug_print
except ImportError:
    from core.defaultsConfig import debug_print

# Try to import pcbnew (only available inside KiCad)
try:
    import pcbnew
    HAS_PCBNEW = True
except ImportError:
    HAS_PCBNEW = False
    pcbnew = None


class KiCadExtractor:
    """
    Centralized KiCad data extractor.
    
    Single source for all KiCad settings and board information.
    AI-friendly: Each method is focused, <50 lines, well-documented.
    """
    
    KICAD_VERSION = "9.0"  # Only support KiCad 9.x
    
    def __init__(self):
        """Initialize extractor with cache."""
        self._config_path: Optional[str] = None
        self._common_settings: Optional[Dict] = None
        self._pcbnew_settings: Optional[Dict] = None
        self._cache_valid: bool = False
    
    # ============================================================
    # ENVIRONMENT
    # ============================================================
    
    def get_environment(self) -> Dict[str, Any]:
        """
        Get KiCad environment information.
        
        Returns:
            Dict with kicad_version, python_version, platform, paths, etc.
        """
        env = {
            'kicad_available': HAS_PCBNEW,
            'kicad_version': None,
            'kicad_build_date': None,
            'python_version': platform.python_version(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'config_path': self._get_config_path(),
            'user_documents': self._get_user_documents_path(),
            'install_type': self._detect_install_type(),
            'plugin_path': self._get_plugin_path(),
        }
        
        if HAS_PCBNEW:
            try:
                env['kicad_version'] = pcbnew.GetBuildVersion()
                if hasattr(pcbnew, 'GetBuildDate'):
                    env['kicad_build_date'] = pcbnew.GetBuildDate()
            except Exception as e:
                env['_error'] = str(e)
        
        return env
    
    def _get_config_path(self) -> Optional[str]:
        """Get KiCad configuration directory path."""
        if self._config_path:
            return self._config_path
        
        # Try pcbnew API first
        if HAS_PCBNEW:
            try:
                if hasattr(pcbnew, 'SETTINGS_MANAGER_GetUserSettingsPath'):
                    self._config_path = pcbnew.SETTINGS_MANAGER_GetUserSettingsPath()
                    return self._config_path
            except:
                pass
        
        # OS-specific fallback
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                self._config_path = os.path.join(appdata, 'kicad', self.KICAD_VERSION)
        elif sys.platform == 'darwin':
            self._config_path = str(Path.home() / 'Library' / 'Preferences' / 'kicad' / self.KICAD_VERSION)
        else:  # Linux
            xdg_config = os.environ.get('XDG_CONFIG_HOME', '')
            if xdg_config:
                self._config_path = os.path.join(xdg_config, 'kicad', self.KICAD_VERSION)
            else:
                self._config_path = str(Path.home() / '.config' / 'kicad' / self.KICAD_VERSION)
        
        return self._config_path
    
    def _get_user_documents_path(self) -> Optional[str]:
        """Get KiCad user documents path (templates, plugins, etc.)."""
        if sys.platform == 'win32':
            docs = os.environ.get('USERPROFILE', os.path.expanduser('~'))
            return os.path.join(docs, 'Documents', 'KiCad', self.KICAD_VERSION)
        elif sys.platform == 'darwin':
            return str(Path.home() / 'Documents' / 'KiCad' / self.KICAD_VERSION)
        else:
            return str(Path.home() / 'Documents' / 'KiCad' / self.KICAD_VERSION)
    
    def _get_plugin_path(self) -> str:
        """Get current plugin installation path."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _detect_install_type(self) -> str:
        """Detect how the plugin was installed."""
        plugin_path = self._get_plugin_path()
        if "3rdparty" in plugin_path:
            return "PCM (Plugin Manager)"
        elif "scripting" in plugin_path.lower():
            return "Manual (scripting folder)"
        else:
            return "Development / Unknown"
    
    # ============================================================
    # BOARD INFO
    # ============================================================
    
    def get_board_info(self) -> Dict[str, Any]:
        """
        Get current board information.
        
        Returns:
            Dict with loaded, filename, project_name, project_dir,
            footprint_count, net_count, track_count, layer_count, etc.
        """
        info = {
            'loaded': False,
            'filename': None,
            'project_name': None,
            'project_dir': None,
            'footprint_count': 0,
            'net_count': 0,
            'track_count': 0,
            'layer_count': 0,
            'width_mm': None,
            'height_mm': None,
        }
        
        if not HAS_PCBNEW:
            return info
        
        try:
            board = pcbnew.GetBoard()
            if board:
                info['loaded'] = True
                filename = board.GetFileName()
                if filename:
                    info['filename'] = filename
                    info['project_name'] = os.path.splitext(os.path.basename(filename))[0]
                    info['project_dir'] = os.path.dirname(filename)
                
                # Counts
                footprints = board.GetFootprints()
                info['footprint_count'] = len(footprints) if footprints else 0
                
                tracks = board.GetTracks()
                info['track_count'] = len(tracks) if tracks else 0
                
                netinfo = board.GetNetInfo()
                info['net_count'] = netinfo.GetNetCount() if netinfo else 0
                
                info['layer_count'] = board.GetCopperLayerCount()
                
                # Board dimensions
                bbox = board.GetBoardEdgesBoundingBox()
                if bbox:
                    info['width_mm'] = pcbnew.ToMM(bbox.GetWidth())
                    info['height_mm'] = pcbnew.ToMM(bbox.GetHeight())
        except Exception as e:
            info['_error'] = str(e)
        
        return info
    
    # ============================================================
    # USER VARIABLES (Text Variables)
    # ============================================================
    
    def get_user_variables(self) -> Dict[str, str]:
        """
        Get project text variables from the current board.
        
        These are set in: Board Setup → Text & Graphics → Text Variables
        Common: ${REVISION}, ${COMPANY}, ${ENGINEER}, custom vars
        
        Returns:
            Dict of variable name → value
        """
        variables = {}
        
        if not HAS_PCBNEW:
            return variables
        
        try:
            board = pcbnew.GetBoard()
            if board:
                # GetProperties() returns dict of text variables
                props = board.GetProperties()
                if props:
                    variables = dict(props)
        except Exception as e:
            variables['_error'] = str(e)
        
        return variables
    
    def get_title_block(self) -> Dict[str, str]:
        """
        Get title block information from the current board.
        
        Returns:
            Dict with TITLE, DATE, REVISION, COMPANY, COMMENT1-4
        """
        title_block = {
            'TITLE': '',
            'DATE': '',
            'REVISION': '',
            'COMPANY': '',
            'COMMENT1': '',
            'COMMENT2': '',
            'COMMENT3': '',
            'COMMENT4': '',
        }
        
        if not HAS_PCBNEW:
            return title_block
        
        try:
            board = pcbnew.GetBoard()
            if board:
                tb = board.GetTitleBlock()
                if tb:
                    title_block['TITLE'] = tb.GetTitle()
                    title_block['DATE'] = tb.GetDate()
                    title_block['REVISION'] = tb.GetRevision()
                    title_block['COMPANY'] = tb.GetCompany()
                    title_block['COMMENT1'] = tb.GetComment(0)
                    title_block['COMMENT2'] = tb.GetComment(1)
                    title_block['COMMENT3'] = tb.GetComment(2)
                    title_block['COMMENT4'] = tb.GetComment(3)
        except Exception as e:
            title_block['_error'] = str(e)
        
        return title_block
    
    def get_all_variables(self) -> Dict[str, str]:
        """
        Get all variables (user + title block).
        
        User variables override title block values if same name.
        """
        all_vars = {}
        all_vars.update(self.get_title_block())
        all_vars.update(self.get_user_variables())  # Override with user vars
        return all_vars
    
    # ============================================================
    # SESSION & BACKUP SETTINGS (from kicad_common.json)
    # ============================================================
    
    def _load_common_settings(self) -> Optional[Dict]:
        """Load kicad_common.json settings file."""
        if self._common_settings is not None:
            return self._common_settings
        
        config_path = self._get_config_path()
        if not config_path:
            return None
        
        common_file = os.path.join(config_path, 'kicad_common.json')
        
        try:
            if os.path.exists(common_file):
                with open(common_file, 'r', encoding='utf-8') as f:
                    self._common_settings = json.load(f)
                    debug_print(f"[KiNotes Extractor] Loaded kicad_common.json")
                    return self._common_settings
        except json.JSONDecodeError as e:
            debug_print(f"[KiNotes Extractor] Invalid JSON: {e}")
        except PermissionError:
            debug_print("[KiNotes Extractor] Permission denied")
        except Exception as e:
            debug_print(f"[KiNotes Extractor] Error: {e}")
        
        return None
    
    def get_session_settings(self) -> Dict[str, Any]:
        """
        Get Session settings from Preferences → Common → Session.
        
        Returns:
            Dict with autosave_interval, file_history_size, etc.
        """
        settings = self._load_common_settings()
        system = settings.get('system', {}) if settings else {}
        
        interval = system.get('autosave_interval', 600)  # Default 10 min
        
        return {
            'autosave_interval': interval,
            'autosave_interval_ms': interval * 1000,
            'autosave_interval_display': self._format_interval(interval),
            'file_history_size': system.get('file_history_size', 9),
            '3d_cache_duration': system.get('3d_cache_file_duration', 30),
            'remember_open_files': system.get('remember_open_files', False),
        }
    
    def get_backup_settings(self) -> Dict[str, Any]:
        """
        Get Project Backup settings from Preferences → Common → Project Backup.
        
        Returns:
            Dict with enabled, min_interval, limits, etc.
        """
        settings = self._load_common_settings()
        backup = settings.get('auto_backup', {}) if settings else {}
        
        interval = backup.get('min_interval', 300)  # Default 5 min
        total_size = backup.get('limit_total_size', 104857600)  # 100 MB
        
        return {
            'enabled': backup.get('enabled', True),
            'backup_on_autosave': backup.get('backup_on_autosave', True),
            'min_interval': interval,
            'min_interval_display': self._format_interval(interval),
            'limit_total_files': backup.get('limit_total_files', 25),
            'limit_daily_files': backup.get('limit_daily_files', 5),
            'limit_total_size': total_size,
            'limit_total_size_mb': total_size / (1024 * 1024),
        }
    
    def get_autosave_interval_ms(self) -> int:
        """
        Get KiCad's Session autosave interval in milliseconds.
        
        Returns:
            Interval in ms, or default 600000 (10 min) if unavailable.
        """
        return self.get_session_settings().get('autosave_interval_ms', 600000)
    
    # ============================================================
    # APPEARANCE SETTINGS
    # ============================================================
    
    def get_appearance_settings(self) -> Dict[str, Any]:
        """
        Get Appearance settings from Preferences → Common.
        
        Returns:
            Dict with color_theme, icon_theme, canvas_scale, etc.
        """
        settings = self._load_common_settings()
        appearance = settings.get('appearance', {}) if settings else {}
        graphics = settings.get('graphics', {}) if settings else {}
        
        return {
            'color_theme': appearance.get('color_theme', 'KiCad Default'),
            'icon_theme': appearance.get('icon_theme', 'auto'),
            'icon_scale': appearance.get('icon_scale', 0),  # 0 = auto
            'canvas_scale': appearance.get('canvas_scale', 0),
            'use_icons_in_menus': appearance.get('use_icons_in_menus', True),
            'show_scrollbars': appearance.get('show_scrollbars', False),
            'toolbar_icon_size': graphics.get('toolbar_icon_size', 'normal'),
            'high_contrast_dimming': graphics.get('high_contrast_mode_dimming_factor', 0.8),
        }
    
    # ============================================================
    # DESIGN SETTINGS (from board)
    # ============================================================
    
    def get_design_settings(self) -> Dict[str, Any]:
        """
        Get board design settings (design rules).
        
        Returns:
            Dict with min_track_width, min_via_diameter, min_clearance, etc.
        """
        settings = {}
        
        if not HAS_PCBNEW:
            return settings
        
        try:
            board = pcbnew.GetBoard()
            if board:
                ds = board.GetDesignSettings()
                if ds:
                    settings['min_track_width'] = pcbnew.ToMM(ds.m_TrackMinWidth)
                    settings['min_via_diameter'] = pcbnew.ToMM(ds.m_ViasMinSize)
                    settings['min_via_drill'] = pcbnew.ToMM(ds.m_MinThroughDrill)
                    settings['min_clearance'] = pcbnew.ToMM(ds.m_MinClearance)
                    
                    if hasattr(ds, 'm_HoleClearance'):
                        settings['min_hole_clearance'] = pcbnew.ToMM(ds.m_HoleClearance)
        except Exception as e:
            settings['_error'] = str(e)
        
        return settings
    
    # ============================================================
    # LIBRARY PATHS
    # ============================================================
    
    def get_library_paths(self) -> Dict[str, str]:
        """
        Get KiCad library paths from environment variables.
        
        Returns:
            Dict of env var name → path
        """
        paths = {}
        
        env_vars = [
            'KICAD9_SYMBOL_DIR',
            'KICAD9_FOOTPRINT_DIR',
            'KICAD9_3DMODEL_DIR',
            'KICAD9_TEMPLATE_DIR',
            'KICAD_USER_TEMPLATE_DIR',
            'KICAD_SYMBOL_DIR',
            'KICAD_FOOTPRINT_DIR',
            'KICAD_3DMODEL_DIR',
            'KICAD_CONFIG_HOME',
            'KICAD_DOCUMENTS_HOME',
        ]
        
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                paths[var] = value
        
        return paths
    
    # ============================================================
    # COMPREHENSIVE EXTRACTION
    # ============================================================
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get ALL available KiCad data in one call.
        
        Useful for debugging and comprehensive access.
        """
        return {
            'environment': self.get_environment(),
            'board': self.get_board_info(),
            'title_block': self.get_title_block(),
            'user_variables': self.get_user_variables(),
            'session': self.get_session_settings(),
            'backup': self.get_backup_settings(),
            'appearance': self.get_appearance_settings(),
            'design_settings': self.get_design_settings(),
            'library_paths': self.get_library_paths(),
        }
    
    def refresh(self):
        """Clear cached data and reload everything."""
        self._common_settings = None
        self._pcbnew_settings = None
        self._cache_valid = False
        debug_print("[KiNotes Extractor] Cache cleared")
    
    # ============================================================
    # HELPERS
    # ============================================================
    
    def _format_interval(self, seconds: int) -> str:
        """Format seconds into human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs:
                return f"{minutes}m {secs}s"
            return f"{minutes} min"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes:
                return f"{hours}h {minutes}m"
            return f"{hours}h"


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_extractor_instance: Optional[KiCadExtractor] = None

def get_kicad_extractor() -> KiCadExtractor:
    """Get singleton KiCad extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = KiCadExtractor()
    return _extractor_instance


# ============================================================
# QUICK ACCESS FUNCTIONS (Backward compatible)
# ============================================================

def get_kicad_version() -> Optional[str]:
    """Quick access to KiCad version string."""
    return get_kicad_extractor().get_environment().get('kicad_version')

def get_project_name() -> Optional[str]:
    """Quick access to current project name."""
    return get_kicad_extractor().get_board_info().get('project_name')

def get_project_dir() -> Optional[str]:
    """Quick access to current project directory."""
    return get_kicad_extractor().get_board_info().get('project_dir')

def is_board_loaded() -> bool:
    """Quick check if a board is loaded."""
    return get_kicad_extractor().get_board_info().get('loaded', False)

def get_autosave_interval_ms() -> int:
    """Quick access to KiCad autosave interval in milliseconds."""
    return get_kicad_extractor().get_autosave_interval_ms()

def get_user_variable(name: str) -> Optional[str]:
    """Quick access to a specific user variable."""
    return get_kicad_extractor().get_all_variables().get(name)

def get_title_block_value(name: str) -> Optional[str]:
    """Quick access to a specific title block value."""
    return get_kicad_extractor().get_title_block().get(name)

def get_footprint_count() -> int:
    """Quick access to footprint count."""
    return get_kicad_extractor().get_board_info().get('footprint_count', 0)

def get_net_count() -> int:
    """Quick access to net count."""
    return get_kicad_extractor().get_board_info().get('net_count', 0)


# ============================================================
# BACKWARD COMPATIBILITY (for kicad_settings_sync.py users)
# ============================================================

class KiCadSettingsSync:
    """
    DEPRECATED: Use get_kicad_extractor() instead.
    
    This class is kept for backward compatibility with existing code.
    All methods delegate to the centralized KiCadExtractor.
    """
    
    def __init__(self):
        self._extractor = get_kicad_extractor()
    
    def get_autosave_interval_ms(self) -> Optional[int]:
        """Get KiCad autosave interval in ms."""
        return self._extractor.get_autosave_interval_ms()
    
    def get_session_autosave_seconds(self) -> Optional[int]:
        """Get KiCad autosave interval in seconds."""
        return self._extractor.get_session_settings().get('autosave_interval')
    
    def get_backup_interval_seconds(self) -> Optional[int]:
        """Get KiCad backup interval in seconds."""
        return self._extractor.get_backup_settings().get('min_interval')
    
    def get_auto_backup_settings(self) -> Optional[Dict]:
        """Get KiCad backup settings."""
        return self._extractor.get_backup_settings()
    
    def get_all_backup_settings(self) -> Dict:
        """Get all backup settings for display."""
        session = self._extractor.get_session_settings()
        backup = self._extractor.get_backup_settings()
        return {
            'session_autosave_interval': session.get('autosave_interval', 0),
            'session_autosave_display': session.get('autosave_interval_display', ''),
            'session_autosave_ms': session.get('autosave_interval_ms', 0),
            'enabled': backup.get('enabled', False),
            'backup_on_autosave': backup.get('backup_on_autosave', False),
            'min_interval': backup.get('min_interval', 0),
            'limit_total_files': backup.get('limit_total_files', 0),
            'limit_daily_files': backup.get('limit_daily_files', 0),
        }
    
    def is_backup_enabled(self) -> bool:
        """Check if KiCad backup is enabled."""
        return self._extractor.get_backup_settings().get('enabled', False)
    
    def get_settings_path(self) -> Optional[str]:
        """Get KiCad settings path."""
        return self._extractor._get_config_path()
    
    def is_available(self) -> bool:
        """Check if KiCad settings are accessible."""
        config_path = self._extractor._get_config_path()
        if not config_path:
            return False
        common_file = os.path.join(config_path, 'kicad_common.json')
        return os.path.exists(common_file)


def get_kicad_sync() -> KiCadSettingsSync:
    """
    DEPRECATED: Use get_kicad_extractor() instead.
    
    Returns backward-compatible KiCadSettingsSync wrapper.
    """
    return KiCadSettingsSync()
