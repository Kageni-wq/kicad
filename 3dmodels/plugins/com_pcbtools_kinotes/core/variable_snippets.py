"""
KiNotes Variable Snippets - Slash command autocomplete system.

Provides `/` command snippets that resolve to live KiCad board data.
Used by both:
1. Visual editor autocomplete (type /rev → popup → insert value)
2. Import button submenu (Insert Variable → select → insert value)

Usage:
    from core.variable_snippets import (
        get_all_snippets,
        get_matching_snippets,
        resolve_snippet
    )
    
    # Get all available snippets
    snippets = get_all_snippets()
    
    # Filter by prefix (for autocomplete)
    matches = get_matching_snippets("rev")  # Returns [('/rev', {...}), ('/revision', {...})]
    
    # Resolve snippet to actual value
    value = resolve_snippet('/rev')  # Returns "Rev 2.1" or fallback

Author: KiNotes Team (pcbtools.xyz)
License: Apache-2.0
SPDX-License-Identifier: Apache-2.0
"""

import datetime
from typing import Dict, Any, Optional, List, Tuple

# Import extractor for live data
try:
    from .kicad_extractor import get_kicad_extractor
except ImportError:
    from core.kicad_extractor import get_kicad_extractor


# ============================================================
# SNIPPET DEFINITIONS - Single Source of Truth
# ============================================================

SNIPPETS: Dict[str, Dict[str, Any]] = {
    # ----------------------------------------------------------
    # Title Block Variables
    # ----------------------------------------------------------
    '/rev': {
        'source': 'title_block',
        'key': 'REVISION',
        'label': 'Revision',
        'description': 'Board revision from title block',
        'category': 'Title Block',
        'fallback': '1.0',
    },
    '/revision': {
        'source': 'title_block',
        'key': 'REVISION',
        'label': 'Revision',
        'description': 'Board revision from title block',
        'category': 'Title Block',
        'fallback': '1.0',
    },
    '/company': {
        'source': 'title_block',
        'key': 'COMPANY',
        'label': 'Company',
        'description': 'Company name from title block',
        'category': 'Title Block',
        'fallback': '',
    },
    '/date': {
        'source': 'title_block',
        'key': 'DATE',
        'label': 'Date',
        'description': 'Date from title block (or today)',
        'category': 'Title Block',
        'fallback_dynamic': 'today',  # Use today's date if title block empty
    },
    '/title': {
        'source': 'title_block',
        'key': 'TITLE',
        'label': 'Title',
        'description': 'Board title from title block',
        'category': 'Title Block',
        'fallback': '',
    },
    
    # ----------------------------------------------------------
    # User Variables (from Board Setup → Text Variables)
    # ----------------------------------------------------------
    '/engineer': {
        'source': 'user_var',
        'key': 'ENGINEER',
        'label': 'Engineer',
        'description': 'Engineer name from user variables',
        'category': 'User Variables',
        'fallback': '',
    },
    
    # ----------------------------------------------------------
    # Board Info
    # ----------------------------------------------------------
    '/project': {
        'source': 'board',
        'key': 'project_name',
        'label': 'Project Name',
        'description': 'Project name from PCB filename',
        'category': 'Board Info',
        'fallback': 'Untitled',
    },
    '/nets': {
        'source': 'board',
        'key': 'net_count',
        'label': 'Net Count',
        'description': 'Number of nets in PCB',
        'category': 'Board Info',
        'format': '{} nets',
        'fallback': '0 nets',
    },
    '/parts': {
        'source': 'board',
        'key': 'footprint_count',
        'label': 'Component Count',
        'description': 'Number of components in PCB',
        'category': 'Board Info',
        'format': '{} components',
        'fallback': '0 components',
    },
    '/layers': {
        'source': 'board',
        'key': 'layer_count',
        'label': 'Layer Count',
        'description': 'Number of copper layers',
        'category': 'Board Info',
        'format': '{} layers',
        'fallback': '2 layers',
    },
    '/size': {
        'source': 'board',
        'key': 'dimensions',
        'label': 'Board Size',
        'description': 'Board dimensions (W × H)',
        'category': 'Board Info',
        'fallback': '',
    },
    '/width': {
        'source': 'board',
        'key': 'width_mm',
        'label': 'Board Width',
        'description': 'Board width in mm',
        'category': 'Board Info',
        'format': '{}mm',
        'fallback': '',
    },
    '/height': {
        'source': 'board',
        'key': 'height_mm',
        'label': 'Board Height',
        'description': 'Board height in mm',
        'category': 'Board Info',
        'format': '{}mm',
        'fallback': '',
    },
    
    # ----------------------------------------------------------
    # Design Rules
    # ----------------------------------------------------------
    '/track': {
        'source': 'design',
        'key': 'min_track_width',
        'label': 'Min Track',
        'description': 'Minimum track width',
        'category': 'Design Rules',
        'format': 'Min track: {}mm',
        'fallback': '',
    },
    '/via': {
        'source': 'design',
        'key': 'min_via_diameter',
        'label': 'Min Via',
        'description': 'Minimum via diameter',
        'category': 'Design Rules',
        'format': 'Min via: {}mm',
        'fallback': '',
    },
    '/clearance': {
        'source': 'design',
        'key': 'min_clearance',
        'label': 'Min Clearance',
        'description': 'Minimum clearance',
        'category': 'Design Rules',
        'format': 'Min clearance: {}mm',
        'fallback': '',
    },
    
    # ----------------------------------------------------------
    # Date/Time (dynamic, not from board)
    # ----------------------------------------------------------
    '/today': {
        'source': 'dynamic',
        'key': 'today',
        'label': 'Today\'s Date',
        'description': 'Current date (YYYY-MM-DD)',
        'category': 'Date/Time',
        'fallback': '',
    },
    '/now': {
        'source': 'dynamic',
        'key': 'now',
        'label': 'Current Time',
        'description': 'Current date and time',
        'category': 'Date/Time',
        'fallback': '',
    },
}


# ============================================================
# SNIPPET ACCESS FUNCTIONS
# ============================================================

def get_all_snippets() -> Dict[str, Dict[str, Any]]:
    """Get all available snippets."""
    return SNIPPETS.copy()


def get_snippet_commands() -> List[str]:
    """Get list of all snippet commands (e.g., ['/rev', '/company', ...])."""
    return list(SNIPPETS.keys())


def get_matching_snippets(prefix: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Get snippets matching a prefix (for autocomplete).
    
    Args:
        prefix: Text after '/' to match (e.g., 'rev' matches '/rev', '/revision')
    
    Returns:
        List of (command, snippet_info) tuples
    """
    prefix_lower = prefix.lower()
    matches = []
    
    for cmd, info in SNIPPETS.items():
        # Match against command (without /) or label
        cmd_text = cmd[1:].lower()  # Remove leading /
        label_lower = info.get('label', '').lower()
        
        if cmd_text.startswith(prefix_lower) or label_lower.startswith(prefix_lower):
            matches.append((cmd, info))
    
    # Sort by command length (shorter first), then alphabetically
    matches.sort(key=lambda x: (len(x[0]), x[0]))
    return matches


def get_snippets_by_category() -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
    """
    Get snippets organized by category (for Import button submenu).
    
    Returns:
        Dict of category → list of (command, snippet_info)
    """
    categories: Dict[str, List] = {}
    
    for cmd, info in SNIPPETS.items():
        category = info.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append((cmd, info))
    
    # Sort within each category
    for cat in categories:
        categories[cat].sort(key=lambda x: x[0])
    
    return categories


# ============================================================
# SNIPPET RESOLUTION (Get actual value)
# ============================================================

def resolve_snippet(command: str) -> str:
    """
    Resolve a snippet command to its actual value.
    
    Args:
        command: Snippet command (e.g., '/rev', '/nets')
    
    Returns:
        Resolved value as string, or fallback if unavailable
    """
    if command not in SNIPPETS:
        print(f"[KiNotes Snippet] Command not found: {command}")
        return ''
    
    snippet = SNIPPETS[command]
    source = snippet.get('source', '')
    key = snippet.get('key', '')
    fallback = snippet.get('fallback', '')
    fallback_dynamic = snippet.get('fallback_dynamic', '')  # Dynamic fallback option
    fmt = snippet.get('format', '{}')
    
    print(f"[KiNotes Snippet] Resolving {command}: source={source}, key={key}, fallback='{fallback}'")
    
    try:
        extractor = get_kicad_extractor()
        value = None
        
        if source == 'title_block':
            title_block = extractor.get_title_block()
            value = title_block.get(key, '')
            print(f"[KiNotes Snippet] Title block {key} = '{value}' (block keys: {list(title_block.keys())})")
        
        elif source == 'user_var':
            value = extractor.get_user_variables().get(key, '')
        
        elif source == 'board':
            board_info = extractor.get_board_info()
            if key == 'dimensions':
                # Special handling for board size
                w = board_info.get('width_mm')
                h = board_info.get('height_mm')
                if w is not None and h is not None:
                    value = f"{w:.1f}mm × {h:.1f}mm"
                else:
                    value = fallback
            else:
                value = board_info.get(key)
        
        elif source == 'design':
            value = extractor.get_design_settings().get(key)
            if value is not None:
                value = round(value, 3)  # Round to 3 decimal places
        
        elif source == 'dynamic':
            if key == 'today':
                value = datetime.datetime.now().strftime('%Y-%m-%d')
            elif key == 'now':
                value = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Format value if we have one
        if value is not None and value != '':
            result = fmt.format(value)
            print(f"[KiNotes Snippet] Returning formatted value: '{result}'")
            return result
        
        # Check for dynamic fallback
        if fallback_dynamic:
            if fallback_dynamic == 'today':
                result = datetime.datetime.now().strftime('%Y-%m-%d')
                print(f"[KiNotes Snippet] Using dynamic fallback (today): '{result}'")
                return result
            elif fallback_dynamic == 'now':
                result = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                print(f"[KiNotes Snippet] Using dynamic fallback (now): '{result}'")
                return result
        
        print(f"[KiNotes Snippet] Using static fallback: '{fallback}'")
        return fallback
        
    except Exception as e:
        print(f"[KiNotes Snippet] Exception in resolve_snippet: {e}")
        # Try dynamic fallback even on exception
        if fallback_dynamic == 'today':
            return datetime.datetime.now().strftime('%Y-%m-%d')
        elif fallback_dynamic == 'now':
            return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        return fallback


def get_snippet_preview(command: str) -> str:
    """
    Get preview text for a snippet (command + label + current value).
    
    Used for autocomplete display and Import button menu.
    
    Args:
        command: Snippet command (e.g., '/rev')
    
    Returns:
        Preview string like "/rev - Revision → Rev 2.1"
    """
    if command not in SNIPPETS:
        return command
    
    snippet = SNIPPETS[command]
    label = snippet.get('label', '')
    value = resolve_snippet(command)
    
    if value:
        return f"{command} - {label} → {value}"
    else:
        return f"{command} - {label}"
