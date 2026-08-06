"""
KiCad Settings Sync - Read KiCad backup preferences for autosave sync.

Provides read-only access to KiCad's kicad_common.json settings to sync
autosave behavior with KiCad's backup interval preferences.

Supports KiCad 9.0 paths only (required for PCM).
Uses pcbnew.SETTINGS_MANAGER_GetUserSettingsPath() when available,
falls back to OS-specific paths otherwise.

Usage:
    from core.kicad_settings_sync import KiCadSettingsSync
    
    sync = KiCadSettingsSync()
    interval_ms = sync.get_autosave_interval_ms()  # Returns ms or None
    if interval_ms:
        # Use KiCad's backup interval

Author: KiNotes Team (pcbtools.xyz)
License: Apache-2.0
SPDX-License-Identifier: Apache-2.0
"""

import os
import sys
import json
from pathlib import Path

# Import debug_print for console logging
try:
    from .defaultsConfig import debug_print, KICAD_SYNC_DEFAULTS
except ImportError:
    from core.defaultsConfig import debug_print, KICAD_SYNC_DEFAULTS


class KiCadSettingsSync:
    """
    Read-only access to KiCad settings for autosave sync.
    
    Reads kicad_common.json to get auto_backup settings.
    Never writes to KiCad settings - read-only for safety.
    """
    
    KICAD_VERSION = "9.0"  # Only support KiCad 9.x
    
    def __init__(self):
        """Initialize sync module - find KiCad settings path."""
        self._settings_path = None
        self._common_json_path = None
        self._cached_settings = None
        self._find_settings_path()
    
    def _find_settings_path(self):
        """Find KiCad settings directory using pcbnew API or OS fallback."""
        # Try pcbnew API first (most reliable when running in KiCad)
        try:
            import pcbnew
            if hasattr(pcbnew, 'SETTINGS_MANAGER_GetUserSettingsPath'):
                self._settings_path = pcbnew.SETTINGS_MANAGER_GetUserSettingsPath()
                debug_print(f"[KiNotes Sync] Found KiCad settings via API: {self._settings_path}")
        except ImportError:
            debug_print("[KiNotes Sync] pcbnew not available, using OS fallback")
        except Exception as e:
            debug_print(f"[KiNotes Sync] pcbnew API error: {e}")
        
        # OS-specific fallback for KiCad 9.0
        if not self._settings_path:
            self._settings_path = self._get_os_settings_path()
            if self._settings_path:
                debug_print(f"[KiNotes Sync] Using OS fallback path: {self._settings_path}")
        
        # Set common.json path
        if self._settings_path:
            self._common_json_path = os.path.join(self._settings_path, 'kicad_common.json')
    
    def _get_os_settings_path(self) -> str:
        """Get KiCad 9.0 settings path based on OS."""
        if sys.platform == 'win32':
            # Windows: %APPDATA%\kicad\9.0
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                return os.path.join(appdata, 'kicad', self.KICAD_VERSION)
        
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Preferences/kicad/9.0
            return str(Path.home() / 'Library' / 'Preferences' / 'kicad' / self.KICAD_VERSION)
        
        else:
            # Linux: $XDG_CONFIG_HOME/kicad/9.0 or ~/.config/kicad/9.0
            xdg_config = os.environ.get('XDG_CONFIG_HOME', '')
            if xdg_config:
                return os.path.join(xdg_config, 'kicad', self.KICAD_VERSION)
            return str(Path.home() / '.config' / 'kicad' / self.KICAD_VERSION)
        
        return None
    
    def _load_common_settings(self) -> dict:
        """Load kicad_common.json with full error handling."""
        if not self._common_json_path:
            debug_print("[KiNotes Sync] No KiCad settings path found")
            return None
        
        if not os.path.exists(self._common_json_path):
            debug_print(f"[KiNotes Sync] kicad_common.json not found: {self._common_json_path}")
            return None
        
        try:
            with open(self._common_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                debug_print("[KiNotes Sync] Successfully loaded kicad_common.json")
                return data
        except json.JSONDecodeError as e:
            debug_print(f"[KiNotes Sync] Invalid JSON in kicad_common.json: {e}")
        except PermissionError:
            debug_print("[KiNotes Sync] Permission denied reading kicad_common.json")
        except OSError as e:
            debug_print(f"[KiNotes Sync] OS error reading kicad_common.json: {e}")
        except Exception as e:
            debug_print(f"[KiNotes Sync] Unexpected error: {e}")
        
        return None
    
    def get_auto_backup_settings(self) -> dict:
        """
        Get KiCad's auto_backup settings section (Project Backup).
        
        Returns:
            Dict with auto_backup settings, or None if unavailable.
            Keys: enabled, backup_on_autosave, min_interval, limit_total_files, etc.
        """
        settings = self._load_common_settings()
        if not settings:
            return None
        
        auto_backup = settings.get('auto_backup')
        if auto_backup:
            debug_print(f"[KiNotes Sync] KiCad auto_backup: {auto_backup}")
        return auto_backup
    
    def get_session_autosave_seconds(self) -> int:
        """
        Get KiCad's Session → Auto save interval in seconds.
        
        This is the main autosave interval from KiCad Preferences → Common → Session.
        Located at system.autosave_interval in kicad_common.json.
        
        Returns:
            Interval in seconds (e.g., 600 = 10 minutes), or None if unavailable.
        """
        settings = self._load_common_settings()
        if not settings:
            return None
        
        system = settings.get('system', {})
        interval = system.get('autosave_interval')
        if interval is not None:
            debug_print(f"[KiNotes Sync] KiCad Session autosave interval: {interval}s")
            return interval
        return None
    
    def get_backup_interval_seconds(self) -> int:
        """
        Get KiCad's backup min_interval in seconds (Project Backup section).
        
        Note: This is the Project Backup interval, NOT the Session autosave.
        Use get_session_autosave_seconds() for the main autosave interval.
        
        Returns:
            Interval in seconds (default KiCad value is 300 = 5 minutes),
            or None if unavailable.
        """
        auto_backup = self.get_auto_backup_settings()
        if not auto_backup:
            return None
        
        interval = auto_backup.get('min_interval')
        if interval is not None:
            debug_print(f"[KiNotes Sync] KiCad backup interval: {interval}s")
            return interval
        return None
    
    def get_autosave_interval_ms(self) -> int:
        """
        Get KiCad's Session autosave interval converted to milliseconds.
        
        Uses KiCad's system.autosave_interval (Session → Auto save) setting.
        Returns KiCad's exact interval with no cap.
        
        Returns:
            Interval in milliseconds, or None if unavailable.
        """
        interval_sec = self.get_session_autosave_seconds()
        if interval_sec is None:
            return None
        
        interval_ms = interval_sec * 1000
        debug_print(f"[KiNotes Sync] Using KiCad Session interval: {interval_sec}s ({interval_ms}ms)")
        return interval_ms
    
    def get_all_backup_settings(self) -> dict:
        """
        Get all relevant KiCad settings for display in KiNotes settings panel.
        
        Includes Session autosave interval and Project Backup settings.
        
        Returns:
            Dict with settings and formatted values, or empty dict.
        """
        settings = self._load_common_settings()
        if not settings:
            return {}
        
        # Get Session autosave interval (system.autosave_interval)
        system = settings.get('system', {})
        session_interval = system.get('autosave_interval', 0)
        
        # Format Session interval for display
        if session_interval >= 60:
            mins = session_interval // 60
            secs = session_interval % 60
            session_display = f"{mins}m {secs}s" if secs else f"{mins} min"
        else:
            session_display = f"{session_interval}s"
        
        # Get Project Backup settings
        auto_backup = settings.get('auto_backup', {})
        backup_interval = auto_backup.get('min_interval', 0)
        
        return {
            # Session settings (what we sync with)
            'session_autosave_interval': session_interval,
            'session_autosave_display': session_display,
            'session_autosave_ms': session_interval * 1000,
            # Project Backup settings (for info display)
            'enabled': auto_backup.get('enabled', False),
            'backup_on_autosave': auto_backup.get('backup_on_autosave', False),
            'min_interval': backup_interval,
            'limit_total_files': auto_backup.get('limit_total_files', 0),
            'limit_daily_files': auto_backup.get('limit_daily_files', 0),
        }
    
    def is_backup_enabled(self) -> bool:
        """Check if KiCad backup is enabled."""
        auto_backup = self.get_auto_backup_settings()
        if not auto_backup:
            return False
        return auto_backup.get('enabled', False)
    
    def get_settings_path(self) -> str:
        """Get the detected KiCad settings path."""
        return self._settings_path
    
    def is_available(self) -> bool:
        """Check if KiCad settings are accessible."""
        return self._common_json_path is not None and os.path.exists(self._common_json_path)


# Singleton instance for convenience
_sync_instance = None

def get_kicad_sync() -> KiCadSettingsSync:
    """Get singleton KiCadSettingsSync instance."""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = KiCadSettingsSync()
    return _sync_instance
