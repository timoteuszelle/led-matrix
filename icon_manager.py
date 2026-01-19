"""
Icon Manager for LED Matrix
Loads and caches pre-rendered icon JSON files
"""

import os
import json
from pathlib import Path
import numpy as np


# Default search paths for icons (in priority order)
DEFAULT_SEARCH_DIRS = [
    Path('icons/rendered'),  # Repo-local icons
    Path(os.getenv('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'led-matrix' / 'icons',
    Path.home() / '.local' / 'share' / 'led-matrix' / 'icons',
]


class IconManager:
    """Manages loading and caching of pre-rendered LED matrix icons"""
    
    def __init__(self, search_dirs=None):
        """
        Initialize icon manager
        
        Args:
            search_dirs: List of Path objects to search for icons (optional)
        """
        self.search_dirs = search_dirs or DEFAULT_SEARCH_DIRS
        self._cache = {}
    
    def load_icon(self, name: str) -> np.ndarray:
        """
        Load icon from JSON file (cached)
        
        Args:
            name: Icon name (e.g., 'lock_small', 'lock_large')
            
        Returns:
            numpy array (uint8) with icon data
            
        Raises:
            FileNotFoundError: If icon cannot be found in search paths
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]
        
        # Search for icon in all search directories
        for base_dir in self.search_dirs:
            candidate = base_dir / name / 'static.json'
            if candidate.exists():
                try:
                    with open(candidate, 'r') as f:
                        data = json.load(f)
                    # Convert to numpy array and transpose
                    # (icon_renderer outputs transposed, so this reverses it for direct grid overlay)
                    arr = np.array(data, dtype=np.uint8)
                    self._cache[name] = arr
                    return arr
                except Exception as e:
                    raise RuntimeError(f"Error loading icon '{name}' from {candidate}: {e}")
        
        # Icon not found in any search path
        search_paths = ', '.join(str(d) for d in self.search_dirs)
        raise FileNotFoundError(
            f"Icon '{name}' not found. Searched in: {search_paths}\n"
            f"Expected file: {name}/static.json"
        )
    
    def clear_cache(self):
        """Clear the icon cache"""
        self._cache.clear()


def overlay_icon(grid: np.ndarray, icon: np.ndarray, position='center', opacity=1.0) -> np.ndarray:
    """
    Overlay an icon onto a grid
    
    Args:
        grid: Target grid (numpy array)
        icon: Icon to overlay (numpy array)
        position: Position on grid ('center', 'top-left', 'top-right', 'bottom-left', 'bottom-right')
        opacity: Icon opacity (0.0-1.0)
        
    Returns:
        Modified grid with icon overlaid
    """
    ih, iw = icon.shape
    gh, gw = grid.shape
    
    # Calculate position
    if position == 'center':
        x0 = (gw - iw) // 2
        y0 = (gh - ih) // 2
    elif position == 'top-left':
        x0, y0 = 0, 0
    elif position == 'top-right':
        x0 = gw - iw
        y0 = 0
    elif position == 'bottom-left':
        x0 = 0
        y0 = gh - ih
    elif position == 'bottom-right':
        x0 = gw - iw
        y0 = gh - ih
    else:
        # Default to center if position unknown
        x0 = (gw - iw) // 2
        y0 = (gh - ih) // 2
    
    # Bounds checking
    x0 = max(0, min(x0, gw - iw)) if iw <= gw else 0
    y0 = max(0, min(y0, gh - ih)) if ih <= gh else 0
    
    # Apply icon with opacity
    icon_scaled = (icon.astype(np.float32) * float(opacity)).astype(np.uint8)
    grid[y0:y0+ih, x0:x0+iw] = icon_scaled
    
    return grid

