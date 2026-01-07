# Icon/Logo System with Pre-rendering

## Concept
A drop-in icon system for displaying application logos/icons on the LED matrix with pre-rendered animations to minimize runtime compute.

## Key Features

### 1. Icon Format & Specifications

**Matrix Constraints:**
- Display: 9x34 pixels
- Quadrant: 7x15 pixels (effective area with borders)
- Full panel: 9x34 pixels
- Grayscale: 0-255 intensity levels
- Aware of panels installed, one, either left or right, two panels, 1 left one right. two panels side by side, on the left or right. 
- Prefred rending, 1 or on 2 panels, full panel or with borders.

**Recommended Icon Sizes:**
- **Quadrant icons**: 7x15 or 7x14 pixels
- **Panel icons**: 9x32 or 8x30 pixels (with borders)
- **Small icons**: 5x5 to 7x7 for compact display

**Format Support:**
- Source: PNG, SVG, or JSON (custom format)
- Output: JSON arrays (pre-rendered)
- Intensity levels: 2-5 tones (configurable)

### 2. Icon Library Structure

```
icons/
├── source/              # Source images (PNG, SVG)
│   ├── apps/
│   │   ├── firefox.png
│   │   ├── chrome.svg
│   │   ├── vscode.png
│   │   └── terminal.png
│   ├── system/
│   │   ├── cpu.png
│   │   ├── memory.png
│   │   ├── network.png
│   │   └── battery.png
│   └── custom/
│       └── logo.png
├── rendered/            # Pre-rendered JSON frames
│   ├── firefox/
│   │   ├── static.json
│   │   ├── fade_in/
│   │   │   ├── frame_00.json
│   │   │   ├── frame_01.json
│   │   │   └── ...
│   │   └── pulse/
│   │       └── ...
│   └── ...
└── manifest.yaml        # Icon metadata and mappings
```

### 3. Pre-rendering Tool

```python
# icon_renderer.py - New tool for pre-rendering icons

import numpy as np
from PIL import Image
import json
import os

class IconRenderer:
    def __init__(self, target_size=(7, 15), intensity_levels=5):
        self.target_size = target_size
        self.intensity_levels = intensity_levels
    
    def load_image(self, path):
        """Load and prepare image"""
        img = Image.open(path)
        # Convert to grayscale
        img = img.convert('L')
        # Resize to target
        img = img.resize(self.target_size, Image.Resampling.LANCZOS)
        return np.array(img)
    
    def quantize_intensities(self, img_array):
        """Reduce to N intensity levels"""
        # Map 0-255 to intensity_levels discrete steps
        levels = np.linspace(0, 255, self.intensity_levels)
        quantized = np.zeros_like(img_array)
        for i, level in enumerate(levels):
            if i == 0:
                quantized[img_array <= level] = level
            else:
                mask = (img_array > levels[i-1]) & (img_array <= level)
                quantized[mask] = level
        return quantized.astype(np.uint8)
    
    def render_static(self, image_path, output_path):
        """Render static icon frame"""
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        # Save as JSON
        with open(output_path, 'w') as f:
            json.dump(quantized.tolist(), f)
        return quantized
    
    def render_fade_animation(self, image_path, output_dir, frames=10):
        """Pre-render fade in/out animation"""
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frames):
            alpha = i / (frames - 1)  # 0 to 1
            frame = (quantized * alpha).astype(np.uint8)
            with open(f"{output_dir}/frame_{i:02d}.json", 'w') as f:
                json.dump(frame.tolist(), f)
    
    def render_slide_animation(self, image_path, output_dir, frames=10, direction='left'):
        """Pre-render slide animation"""
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frames):
            progress = i / (frames - 1)
            frame = np.zeros_like(quantized)
            
            if direction == 'left':
                offset = int((1 - progress) * quantized.shape[1])
                width = quantized.shape[1] - offset
                frame[:, :width] = quantized[:, offset:]
            # ... other directions
            
            with open(f"{output_dir}/frame_{i:02d}.json", 'w') as f:
                json.dump(frame.tolist(), f)
    
    def render_pulse_animation(self, image_path, output_dir, frames=20, cycles=1):
        """Pre-render pulse/breathing animation"""
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frames):
            # Sine wave for smooth pulsing
            phase = (i / frames) * 2 * np.pi * cycles
            intensity = 0.5 + 0.5 * np.sin(phase)  # 0 to 1
            frame = (quantized * intensity).astype(np.uint8)
            
            with open(f"{output_dir}/frame_{i:02d}.json", 'w') as f:
                json.dump(frame.tolist(), f)

# CLI tool
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pre-render icons for LED matrix")
    parser.add_argument('input', help='Input image path')
    parser.add_argument('--size', default='7x15', help='Target size (WxH)')
    parser.add_argument('--levels', type=int, default=5, help='Intensity levels (2-5)')
    parser.add_argument('--animations', nargs='+', 
                       choices=['static', 'fade', 'slide', 'pulse'],
                       default=['static'], help='Animations to render')
    # ... more args
```

### 4. Icon Manifest Format

```yaml
# icons/manifest.yaml
icons:
  firefox:
    name: "Firefox Browser"
    source: "source/apps/firefox.png"
    size: [7, 15]
    intensity_levels: 4
    animations:
      - static
      - fade
      - pulse
    default_animation: fade
    
  cpu:
    name: "CPU Monitor"
    source: "source/system/cpu.png"
    size: [7, 14]
    intensity_levels: 3
    animations:
      - static
      - pulse
    default_animation: pulse
    
  custom_logo:
    name: "My Custom Logo"
    source: "source/custom/logo.svg"
    size: [9, 32]  # Full panel
    intensity_levels: 5
    animations:
      - static
      - fade
      - slide
    default_animation: slide
```

### 5. Integration with Config System

```yaml
# config.yaml - Extended with icon support
quadrants:
  top-left:
  - app:
    name: cpu
    duration: 300
    # Display icon with app
    icon:
      name: cpu
      position: center  # left, center, right, overlay
      animation: pulse
      size: small  # or [7, 14]
    
  top-right:
  - app:
    name: custom_browser_stats
    duration: 60
    icon:
      name: firefox
      animation: fade
      transition:
        in: fade
        out: slide_left
```

### 6. Runtime Icon Manager

```python
# icon_manager.py
class IconManager:
    def __init__(self, icons_dir='icons'):
        self.icons_dir = icons_dir
        self.manifest = self.load_manifest()
        self.cache = {}  # Cache loaded frames
    
    def load_manifest(self):
        with open(f"{self.icons_dir}/manifest.yaml") as f:
            return yaml.safe_load(f)
    
    def get_static_frame(self, icon_name):
        """Get static icon frame (cached)"""
        if icon_name not in self.cache:
            path = f"{self.icons_dir}/rendered/{icon_name}/static.json"
            with open(path) as f:
                self.cache[icon_name] = np.array(json.load(f))
        return self.cache[icon_name]
    
    def get_animation_frames(self, icon_name, animation_type):
        """Get pre-rendered animation frames (cached)"""
        cache_key = f"{icon_name}_{animation_type}"
        if cache_key not in self.cache:
            frames = []
            anim_dir = f"{self.icons_dir}/rendered/{icon_name}/{animation_type}"
            for frame_file in sorted(os.listdir(anim_dir)):
                with open(f"{anim_dir}/{frame_file}") as f:
                    frames.append(np.array(json.load(f)))
            self.cache[cache_key] = frames
        return self.cache[cache_key]
    
    def overlay_icon(self, grid, icon_name, position='center', brightness=1.0):
        """Overlay icon onto existing grid"""
        icon = self.get_static_frame(icon_name)
        # Calculate position
        # ... positioning logic
        # Blend icon with grid
        # ... blending logic
        return grid
```

### 7. Batch Rendering Script

```bash
#!/bin/bash
# render_icons.sh - Batch render all icons

# Render all icons in source directory
for img in icons/source/**/*.{png,svg}; do
    name=$(basename "$img" | cut -d. -f1)
    
    # Render static
    python icon_renderer.py "$img" \
        --output "icons/rendered/$name/static.json" \
        --levels 4
    
    # Render animations
    python icon_renderer.py "$img" \
        --output "icons/rendered/$name" \
        --animations fade pulse slide \
        --frames 15
done

echo "Icon rendering complete!"
```

### 8. Automatic Icon Detection

```python
def discover_app_icons():
    """Auto-discover icons for running applications"""
    # Check common icon locations
    icon_paths = [
        "/usr/share/pixmaps",
        "/usr/share/icons",
        "~/.local/share/icons",
    ]
    
    # Map running processes to icons
    # Pre-render discovered icons
    # Update manifest automatically
```

### 9. Example Use Cases

#### App Launcher Display
```yaml
top-left:
  - app:
    name: app_switcher
    icon:
      name: firefox
      animation: fade
      duration: 2
  - app:
    name: app_switcher  
    icon:
      name: vscode
      animation: slide_right
```

#### System Status with Icons
```yaml
bottom-left:
  - app:
    name: mem-bat
    icons:
      - name: memory
        position: top-left
      - name: battery
        position: bottom-left
```

#### Notification System
```yaml
notifications:
  - icon: email
    animation: pulse
    urgent: true
  - icon: calendar
    animation: fade
```

### 10. Benefits

**Performance:**
- Pre-rendered animations eliminate runtime compute
- JSON format is fast to load and cache
- No image processing during display

**Quality:**
- Precise control over intensity quantization
- Optimized for LED matrix constraints
- Consistent appearance across animations

**Flexibility:**
- Easy to add new icons (drop PNG in source/)
- Run batch render script
- Automatic manifest updates

**User Experience:**
- Visual identification of apps/functions
- Professional appearance
- Smooth animations without lag

### 11. Implementation Phases

**Phase 1: Core System**
- [ ] Create icon_renderer.py with basic rendering
- [ ] Implement static icon rendering
- [ ] Create manifest format
- [ ] Add icon_manager.py for runtime loading

**Phase 2: Animation Support**
- [ ] Implement fade animation pre-rendering
- [ ] Add slide animation
- [ ] Add pulse animation
- [ ] Create batch rendering script

**Phase 3: Integration**
- [ ] Integrate with yaml config system
- [ ] Add icon overlay to drawing functions
- [ ] Implement icon cache management
- [ ] Add position/sizing logic

**Phase 4: Advanced Features**
- [ ] Auto-discovery of system icons
- [ ] SVG support via cairosvg
- [ ] Icon editor/preview tool
- [ ] Dynamic icon generation

### 12. File Format Details

**Static Icon JSON:**
```json
[
  [0, 64, 128, 192, 255, 192, 128, 64, 0],
  [64, 128, 192, 255, 255, 255, 192, 128, 64],
  ...
]
```

**Animation Metadata:**
```json
{
  "name": "firefox_fade",
  "frames": 15,
  "fps": 10,
  "loop": false,
  "frame_files": ["frame_00.json", "frame_01.json", ...]
}
```

This system would work perfectly with the maintainer's existing animation infrastructure while adding a powerful icon/logo capability!
