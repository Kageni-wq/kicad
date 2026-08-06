"""
KiNotes Icons - Unicode icon constants for UI elements.

Cross-platform compatible icons using Unicode characters.
Works consistently across Windows, macOS, and Linux.

Usage:
    from .icons import Icons
    button.SetLabel(Icons.SAVE + " Save")
"""


class Icons:
    """Unicode icon constants for UI elements."""
    
    # Tab icons
    NOTES = "\u270F"        # ✏ Pencil
    TODO = "\u2611"         # ☑ Checkbox
    BOM = "\u2630"          # ☰ Menu/List
    CHANGELOG = "\U0001F4DD" # 📝 Memo
    
    # Action icons
    IMPORT = "\u21E9"       # ⇩ Down arrow
    SAVE = "\u2713"         # ✓ Checkmark
    PDF = "\u21B5"          # ↵ Export
    ADD = "+"               # + Plus
    DELETE = "\U0001F5D1"   # 🗑 Trash
    CLEAR = "\u2716"        # ✖ X mark
    SETTINGS = "\u2699"     # ⚙ Gear
    GENERATE = "\u25B6"     # ▶ Play
    
    # Theme icons
    DARK = "\U0001F319"     # 🌙 Moon
    LIGHT = "\u2600"        # ☀ Sun
    
    # Import menu icons
    BOARD = "\u25A1"        # □ Square
    LAYERS = "\u2261"       # ≡ Layers
    NETLIST = "\u2194"      # ↔ Bidirectional
    RULES = "\u2263"        # ≣ Rules
    DRILL = "\u25CE"        # ◎ Bullseye
    ALL = "\u2606"          # ☆ Star
    GLOBE = "\U0001F310"    # 🌐 Globe
    
    # Status icons
    TIMER = "\u23F1"        # ⏱ Stopwatch
    FOLDER = "\U0001F4C1"   # 📁 Folder
    LINK = "\U0001F517"     # 🔗 Link
