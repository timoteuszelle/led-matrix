# Icon Renderer Tool

A pre-rendering tool for LED matrix icons with animation support.

## Features

- **Static Icon Rendering**: Convert images to LED matrix format with intensity quantization
- **Animation Pre-rendering**: Fade, pulse, and slide animations
- **Configurable Output**: Adjustable size and intensity levels (2-8 tones)
- **ASCII Preview**: View rendered icons in terminal before output
- **Multiple Formats**: Supports PNG, JPG, and other PIL-compatible formats

## Installation

### Dependencies
```bash
# On NixOS (recommended)
nix-shell -p python311Packages.pillow python311Packages.numpy

# Or with pip
pip install pillow numpy
```

## Usage

### Basic Usage

```bash
# Render static icon with default settings (7x15, 5 intensity levels)
./icon_renderer.py input.png -o output.json

# Preview in terminal
./icon_renderer.py input.png -o output.json --preview
```

### Custom Sizes

```bash
# Quadrant icon (7x15)
./icon_renderer.py icon.png -o cpu_icon.json --size 7x15

# Full panel icon (9x34)
./icon_renderer.py logo.png -o logo.json --size 9x34

# Small icon (5x5)
./icon_renderer.py badge.png -o badge.json --size 5x5
```

### Intensity Levels

```bash
# 2-tone (binary)
./icon_renderer.py icon.png -o output.json --levels 2

# 3-tone (low, mid, high)
./icon_renderer.py icon.png -o output.json --levels 3

# 5-tone (default, good balance)
./icon_renderer.py icon.png -o output.json --levels 5
```

### Animations

```bash
# Render all animations
./icon_renderer.py icon.png -o icons/firefox --animations static fade pulse slide

# Just fade animation (15 frames)
./icon_renderer.py icon.png -o icons/firefox/fade --animations fade --frames 15

# Pulse with 2 cycles (breathing effect)
./icon_renderer.py icon.png -o icons/firefox/pulse --animations pulse --pulse-cycles 2

# Slide from specific direction
./icon_renderer.py icon.png -o icons/firefox/slide_right \\
    --animations slide --slide-direction right
```

### Complete Example

```bash
# Render Firefox icon with all features
./icon_renderer.py firefox_logo.png \\
    -o icons/rendered/firefox \\
    --size 7x15 \\
    --levels 4 \\
    --animations static fade pulse slide \\
    --frames 20 \\
    --pulse-cycles 1 \\
    --preview
```

## Output Format

### Static Icon (JSON)
```json
[
  [0, 64, 128, 192, 255],
  [64, 128, 192, 255, 255],
  ...
]
```

### Directory Structure
```
icons/rendered/firefox/
├── static.json
├── fade/
│   ├── frame_00.json
│   ├── frame_01.json
│   └── ...
├── pulse/
│   └── ...
└── slide_left/
    └── ...
```

## Testing

### Create Test Icons

On NixOS:
```bash
nix-shell -p python311Packages.pillow --run "python3 << 'EOF'
from PIL import Image, ImageDraw

img = Image.new('L', (7, 15), 0)
draw = ImageDraw.Draw(img)
draw.rectangle([1, 2, 5, 12], fill=200)
draw.rectangle([2, 4, 4, 10], fill=100)
for y in [3, 6, 9]:
    draw.point((0, y), fill=150)
    draw.point((6, y), fill=150)
img.save('test_cpu.png')
print('Created test_cpu.png')
EOF
"
```

Then render:
```bash
nix-shell -p python311Packages.pillow python311Packages.numpy --run \\
    "./icon_renderer.py test_cpu.png -o test_output.json --preview"
```

### Verify Output

```bash
# Check JSON structure
cat test_output.json | head -20

# Verify dimensions
python3 -c "import json; data = json.load(open('test_output.json')); \\
    print(f'Dimensions: {len(data)}x{len(data[0])}')"
```

## Integration with LED Matrix

The output JSON format is compatible with the existing snapshot system:

```python
import json
import numpy as np

# Load rendered icon
with open('icons/rendered/cpu/static.json') as f:
    icon = np.array(json.load(f))

# Use in drawing code
grid[:icon.shape[0], :icon.shape[1]] = icon
```

## Tips

### Icon Design
- Keep designs simple - complex details are lost at low resolution
- Use high contrast for better visibility
- Test with 3-5 intensity levels
- Consider the LED matrix's grayscale range

### Optimization
- Pre-render animations once, use many times
- Cache rendered icons for fast loading
- Use static icons for better performance
- Animations are great for transitions and notifications

### Recommended Sizes
- **Quadrant icons**: 7x14 or 7x15
- **Panel icons**: 9x32 (with border) or 9x34 (full)
- **Small badges**: 5x5 to 7x7
- **App icons**: 7x15 (standard)

## Troubleshooting

### "ModuleNotFoundError: No module named 'PIL'"
Install Pillow: `nix-shell -p python311Packages.pillow` or `pip install pillow`

### "Output looks wrong"
- Check if image needs transpose (LED matrix orientation)
- Verify intensity levels are appropriate
- Try `--preview` to see ASCII representation

### "Animation frames are too large"
- Reduce `--frames` count (10-15 is usually sufficient)
- Use fewer intensity levels
- Consider static icon instead

## Examples Gallery

See `ICON_SYSTEM_PROPOSAL.md` for complete system design and integration examples.

## Future Enhancements

- SVG support via cairosvg
- Batch rendering script
- Icon manifest generator
- GUI preview tool
- Auto-detection of system icons
- Dithering support for better gradients
