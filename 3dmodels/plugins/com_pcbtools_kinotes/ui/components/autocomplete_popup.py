"""
KiNotes Autocomplete Popup - Slash command selection widget.

A visual_editor component mimicking VS Code's IntelliSense behavior.
Features rich-text rendering, dynamic cursor tracking ("Follow Cursor" mode), 
and "abc" type icons.

Usage:
    from ui.components.autocomplete_popup import SnippetAutocompletePopup
    
    popup = SnippetAutocompletePopup(parent, dark_mode=True)
    
    # In your editor's text change event:
    popup.show_for_prefix(current_word, editor_ctrl, callback)

Author: KiNotes Team (pcbtools.xyz)
License: Apache-2.0
SPDX-License-Identifier: Apache-2.0
"""

import wx
import wx.html
import wx.richtext as rt
from typing import List, Tuple, Callable, Optional, Any

# --- Core Imports ---
try:
    from core.variable_snippets import get_matching_snippets, resolve_snippet
except ImportError:
    try:
        from ...core.variable_snippets import get_matching_snippets, resolve_snippet
    except ImportError:
        # Fallback for standalone testing
        def get_matching_snippets(prefix): return []
        def resolve_snippet(cmd): return ""


# --- Position Helper (Calculates exact pixel of the cursor) ---
def _get_caret_screen_rect(editor: wx.Window) -> wx.Rect:
    """
    Calculates the exact Screen coordinates (x, y, w, h) of the caret/cursor.
    Supports wx.richtext.RichTextCtrl, wx.stc.StyledTextCtrl, and wx.TextCtrl.
    """
    line_height = 20  # Default fallback
    
    # Case A: RichTextCtrl (KiNotes Visual Editor)
    if isinstance(editor, rt.RichTextCtrl):
        try:
            pos = editor.GetInsertionPoint()
            # PositionToCoords returns client coordinates of the character position
            client_pt = editor.PositionToCoords(pos)
            
            if client_pt and client_pt != wx.Point(-1, -1):
                screen_pt = editor.ClientToScreen(client_pt)
                # Estimate line height from font
                try:
                    font = editor.GetFont()
                    dc = wx.ClientDC(editor)
                    dc.SetFont(font)
                    _, line_height = dc.GetTextExtent("Mg")
                except:
                    line_height = 20
                return wx.Rect(screen_pt.x, screen_pt.y, 1, line_height)
        except Exception as e:
            print(f"[KiNotes Popup] RichTextCtrl position error: {e}")
    
    # Case B: StyledTextCtrl (Scintilla / Code Editors)
    if hasattr(editor, "PointFromPosition"):
        try:
            pos = editor.GetCurrentPos()
            pt = editor.PointFromPosition(pos)
            height = editor.TextHeight(editor.LineFromPosition(pos))
            screen_pt = editor.ClientToScreen(pt)
            return wx.Rect(screen_pt.x, screen_pt.y, 1, height)
        except:
            pass

    # Case C: Standard wx.TextCtrl
    if isinstance(editor, wx.TextCtrl):
        try:
            ip = editor.GetInsertionPoint()
            result = editor.PositionToXY(ip)
            if result[0]:  # Success
                col = result[1]
                row = result[2] if len(result) > 2 else 0
                
                dc = wx.ClientDC(editor)
                dc.SetFont(editor.GetFont())
                _, h = dc.GetTextExtent("Mg")
                
                # Get text width
                try:
                    row_text = editor.GetLineText(row)
                    text_before = row_text[:col]
                    w, _ = dc.GetTextExtent(text_before)
                except:
                    w = col * 8  # Rough estimate
                
                pt = wx.Point(w + 4, row * h)
                screen_pt = editor.ClientToScreen(pt)
                return wx.Rect(screen_pt.x, screen_pt.y, 1, h)
        except:
            pass

    # Fallback: Use editor's screen position with offset
    try:
        editor_pos = editor.GetScreenPosition()
        return wx.Rect(editor_pos.x + 50, editor_pos.y + 30, 1, line_height)
    except:
        return wx.Rect(100, 100, 1, 20)


# --- The Rich HTML List Widget ---
class RichSnippetList(wx.html.HtmlListBox):
    """
    Virtual ListBox using HTML to render VS Code-style autocomplete items.
    Hides scrollbar when mouse is not over the list.
    """
    def __init__(self, parent, dark_mode: bool):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.dark_mode = dark_mode
        self.items: List[Tuple[str, dict]] = []
        self.prefix: str = ""
        self.SetMargins(0, 0)  # Tight margins
        
        # Hide scrollbar by default (VS Code style)
        try:
            self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        except:
            pass  # Some wx versions don't support this
        
        # Show scrollbar on mouse enter, hide on leave
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_mouse_leave)

        # Theme Colors (VS Code Palette)
        if dark_mode:
            self.col_bg = "#252526"
            self.col_fg = "#CCCCCC"
            self.col_match = "#569CD6"   # VS Code Blue
            self.col_detail = "#808080"  # Gray
            self.col_sel_bg = "#04395e"  # Dark Blue Selection
            self.col_sel_fg = "#FFFFFF"
            self.col_icon_border = "#C5C5C5"
        else:
            self.col_bg = "#F3F3F3"
            self.col_fg = "#333333"
            self.col_match = "#0000FF"
            self.col_detail = "#666666"
            self.col_sel_bg = "#0060C0"
            self.col_sel_fg = "#FFFFFF"
            self.col_icon_border = "#666666"

        self.SetBackgroundColour(wx.Colour(self.col_bg))

    def update_data(self, items: List[Tuple[str, dict]], prefix: str):
        self.items = items
        self.prefix = prefix.lower()
        self.SetItemCount(len(items))
        self.Refresh()

    def OnGetItem(self, n: int) -> str:
        if n >= len(self.items): 
            return ""
        
        cmd, info = self.items[n]
        label = info.get('label', cmd)
        full_value = str(resolve_snippet(cmd) or "")
        short_value = (full_value[:25] + '...') if len(full_value) > 25 else full_value

        # --- Text Highlighting (The Blue Match) ---
        display_label = label
        if self.prefix and self.prefix in label.lower():
            start = label.lower().find(self.prefix)
            end = start + len(self.prefix)
            display_label = (f"{label[:start]}"
                             f"<b><font color='{self.col_match}'>{label[start:end]}</font></b>"
                             f"{label[end:]}")

        # --- Row Colors ---
        is_sel = self.GetSelection() == n
        txt_c = self.col_sel_fg if is_sel else self.col_fg
        det_c = self.col_sel_fg if is_sel else self.col_detail
        
        # Simple HTML Layout (compatible with wx.html) - font size 8
        return f"""
        <font color="{txt_c}" size="2">
        <table width="100%" cellspacing="0" cellpadding="1">
            <tr>
                <td><b>{display_label}</b></td>
                <td align="right"><font color="{det_c}">{short_value}</font></td>
            </tr>
        </table>
        </font>
        """

    def OnGetItemAttr(self, n: int):
        """Handle selection background."""
        attr = super().OnGetItemAttr(n)
        if self.GetSelection() == n:
            attr.SetBackgroundColour(wx.Colour(self.col_sel_bg))
        return attr
    
    def _on_mouse_enter(self, event):
        """Show scrollbar when mouse enters."""
        try:
            self.ShowScrollbars(wx.SHOW_SB_DEFAULT, wx.SHOW_SB_DEFAULT)
        except:
            pass
        event.Skip()
    
    def _on_mouse_leave(self, event):
        """Hide scrollbar when mouse leaves."""
        try:
            self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        except:
            pass
        event.Skip()


# --- The Main Popup Window ---
class SnippetAutocompletePopup(wx.PopupTransientWindow):
    """
    VS Code-style autocomplete popup with dynamic cursor tracking.
    
    The popup follows the caret as you type, positioning itself
    below and slightly to the right of the current cursor position.
    """
    
    def __init__(self, parent, dark_mode: bool = False):
        # Use simple constructor for KiCad wxPython compatibility
        super().__init__(parent)
        
        self._dark_mode = dark_mode
        self._callback: Optional[Callable] = None
        self._editor_ref = None
        
        # Border color (visible as 1px frame)
        border_color = wx.Colour(60, 60, 60) if dark_mode else wx.Colour(180, 180, 180)
        self.SetBackgroundColour(border_color)
        
        # Main container panel
        self._panel = wx.Panel(self)
        self._panel.SetBackgroundColour(border_color)
        
        # The HTML list widget
        self._list = RichSnippetList(self._panel, dark_mode)
        
        # Sizer with 1px border padding
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 1) 
        self._panel.SetSizer(sizer)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self._panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        
        # Bind click event
        self._list.Bind(wx.EVT_LEFT_UP, self._on_click)

    def show_for_prefix(self, prefix: str, editor_ref: wx.Window, callback: Callable) -> bool:
        """
        Show popup with dynamic cursor tracking.
        
        The popup positions itself below the current caret position,
        moving as the user types (not anchored to where '/' was typed).
        
        Args:
            prefix: Text after '/' to filter snippets
            editor_ref: The editor widget (for caret position)
            callback: Function to call on selection (cmd, value)
            
        Returns:
            True if popup shown, False if no matches
        """
        self._callback = callback
        self._editor_ref = editor_ref
        
        # 1. Get matching snippets
        items = get_matching_snippets(prefix)
        print(f"[KiNotes Popup] show_for_prefix: prefix='{prefix}', items={len(items)}")
        
        if not items:
            self.safe_dismiss()
            return False
            
        # 2. Update list data
        self._list.update_data(items, prefix)
        self._list.SetSelection(0)
        
        # 3. Get EXACT screen position of the blinking cursor
        caret_rect = _get_caret_screen_rect(editor_ref)
        print(f"[KiNotes Popup] Caret rect: x={caret_rect.x}, y={caret_rect.y}, h={caret_rect.height}")
        
        # --- DYNAMIC CURSOR TRACKING ---
        # Position popup at current caret X (moves right as you type)
        anchor_x = caret_rect.x
        anchor_y = caret_rect.y + caret_rect.height + 2  # Below cursor with 2px gap
        
        # 4. Calculate popup size - compact VS Code style
        row_height = 18  # Smaller rows
        popup_w = 380    # Slightly narrower
        popup_h = min(len(items) * row_height + 4, 250)  # Max 250px
        
        # 5. Screen bounds handling (Smart Flip)
        try:
            display_idx = wx.Display.GetFromWindow(editor_ref)
            if display_idx != wx.NOT_FOUND:
                display = wx.Display(display_idx)
                screen = display.GetClientArea()
            else:
                screen = wx.GetClientDisplayRect()
        except:
            screen = wx.GetClientDisplayRect()
        
        # Flip UP if hitting bottom
        if (anchor_y + popup_h) > (screen.y + screen.height):
            anchor_y = caret_rect.y - popup_h - 2  # Above cursor
            
        # Clamp to right edge
        if (anchor_x + popup_w) > (screen.x + screen.width):
            anchor_x = (screen.x + screen.width) - popup_w - 4
            
        # Clamp to left edge
        if anchor_x < screen.x:
            anchor_x = screen.x + 4
        
        print(f"[KiNotes Popup] Final position: ({anchor_x}, {anchor_y}), size: ({popup_w}, {popup_h})")
        
        self.SetSize(wx.Size(popup_w, popup_h))
        self.SetPosition(wx.Point(anchor_x, anchor_y))
        
        # Show popup
        if not self.IsShown():
            self.Popup()
        return True

    def handle_key(self, key_code: int) -> bool:
        """
        Forward keyboard events from editor to popup.
        
        Returns True if the key was consumed by the popup.
        """
        if not self.IsShown(): 
            return False
        
        sel = self._list.GetSelection()
        count = self._list.GetItemCount()
        
        # Navigation
        if key_code == wx.WXK_DOWN:
            new_sel = (sel + 1) % count
            self._list.SetSelection(new_sel)
            self._list.Refresh()
            return True
            
        elif key_code == wx.WXK_UP:
            new_sel = (sel - 1) if sel > 0 else count - 1
            self._list.SetSelection(new_sel)
            self._list.Refresh()
            return True
            
        elif key_code == wx.WXK_PAGEDOWN:
            new_sel = min(sel + 5, count - 1)
            self._list.SetSelection(new_sel)
            self._list.Refresh()
            return True
            
        elif key_code == wx.WXK_PAGEUP:
            new_sel = max(sel - 5, 0)
            self._list.SetSelection(new_sel)
            self._list.Refresh()
            return True
            
        elif key_code == wx.WXK_HOME:
            self._list.SetSelection(0)
            self._list.Refresh()
            return True
            
        elif key_code == wx.WXK_END:
            self._list.SetSelection(count - 1)
            self._list.Refresh()
            return True
            
        # Selection
        elif key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            self._do_select()
            return True
            
        # Dismiss
        elif key_code == wx.WXK_ESCAPE:
            self.safe_dismiss()
            return True
            
        return False

    def _do_select(self):
        """Execute the selection callback."""
        sel = self._list.GetSelection()
        if self._callback and sel != wx.NOT_FOUND and sel < len(self._list.items):
            cmd, info = self._list.items[sel]
            value = resolve_snippet(cmd)
            # Use CallAfter to safely modify editor from popup context
            wx.CallAfter(self._callback, cmd, value)
        self.safe_dismiss()

    def _on_click(self, event):
        """Handle mouse click selection."""
        item = self._list.HitTest(event.GetPosition())
        if item != wx.NOT_FOUND:
            self._list.SetSelection(item)
            self._do_select()
        else:
            event.Skip()
    
    def safe_dismiss(self):
        """Robust dismissal that handles API differences gracefully."""
        try:
            self.Dismiss()
        except AttributeError:
            self.Hide()
        except RuntimeError:
            pass  # Window already destroyed
    
    def OnDismiss(self):
        """Called automatically when popup is dismissed."""
        pass
