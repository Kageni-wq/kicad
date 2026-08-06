from .core.check_libs import _is_in_call_stack, ensure_dependencies

from .ui.missing_lib_dialog import MissingLibsDialog

if _is_in_call_stack("LoadPluginModule", "pcbnew"):
    libs = ["shapely", "psutil"]
    if ensure_dependencies(libs):
        from .copper_filler_action import CopperFillerPlugin

        CopperFillerPlugin().register()
    else:
        dialog = MissingLibsDialog()
        dialog.ShowModal()
        dialog.Destroy()
