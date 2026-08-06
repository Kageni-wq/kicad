import inspect
import os, sys
import platform
import importlib.util
import subprocess as sp

from typing import List

def _is_in_call_stack(function_name: str, module_name: str) -> bool:
    current_stack = inspect.stack()

    for frame_info in current_stack:
        frame = frame_info.frame
        if frame.f_globals.get("__name__") == module_name:
            if function_name in frame.f_locals or function_name in frame.f_globals:
                return True

    return False

def ensure_dependencies(libs: List[str]) -> bool:
    """Проверяет и устанавливает зависимости при необходимости"""

    system = platform.system()

    for lib in libs:
        shapely_spec = importlib.util.find_spec(lib)
        if shapely_spec is None:
            if system == 'Windows':
                sp.check_call([os.path.dirname(sys.executable) + '\Scripts\pip.exe', 'install', lib])
            elif system == 'Linux':
                return False
    return True