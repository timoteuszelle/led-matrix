# Icon Creation Guide

Multiple ways to create custom icons for your LED matrix display.

## Option 1: Use Our Icon Editor (Recommended - Works Now!)

### Quick Start

Open `icon_editor.html` in your browser:

```bash
# From the repo directory
firefox icon_editor.html
# or
chromium icon_editor.html
```

### Features

- ✅ **Visual Editor** - Draw directly, see what you get
- ✅ **Multiple Sizes** - 7x15 (small), 9x34 (full panel), 9x68 (dual panel)
- ✅ **Grayscale Support** - 256 intensity levels (0-255)
- ✅ **Preset Intensities** - Quick buttons for common values
- ✅ **One-Click Export** - Download JSON or copy to clipboard
- ✅ **Drawing Tools** - Clear, fill, invert
- ✅ **Works Offline** - No internet required

### Workflow

1. **Open** `icon_editor.html` in browser
2. **Select Size** - Choose canvas dimensions
3. **Draw** - Left click to draw, right click to erase, drag to paint
4. **Adjust Intensity** - Use slider or preset buttons
5. **Export** - Click "Download JSON"
6. **Save** - Place in `icons/rendered/your_icon_name/static.json`

### Using Your Icon

```bash
# Place the downloaded JSON file
mkdir -p icons/rendered/my_icon
mv ~/Downloads/icon_7x15_*.json icons/rendered/my_icon/static.json

# Test it
python3 -c "from icon_manager import IconManager; m = IconManager(); print(m.load_icon('my_icon').shape)"
```

---

## Option 2: Framework dotmatrixtool (Future - Needs Enhancement)

### Current Status

The official Framework tool at https://inputmodule.dotmatrixtool.com/ is great for drawing but **lacks save/export functionality**.

### What's Missing

- ❌ No "Download JSON" button
- ❌ No "Save" feature
- ❌ Must manually copy-paste code from browser

### Upstream Contribution Plan

We should contribute this feature back to Framework!

#### What to Add

1. **Export Button** - Download as JSON
2. **Multiple Formats** - JSON, hex array, Python code
3. **Clipboard Copy** - One-click copy
4. **Import** - Load existing patterns

#### Implementation Steps

**1. Fork the Repository**

```bash
# Fork https://github.com/FrameworkComputer/dotmatrixtool on GitHub
git clone https://github.com/YOUR_USERNAME/dotmatrixtool
cd dotmatrixtool
```

**2. Add Export Functionality**

The tool uses the `custom-display` branch. Key files:
- `app.js` - Main application logic
- `index.html` - UI structure

Add export buttons and functions:

```javascript
// In app.js - add export function
function exportJSON() {
    const width = matrix[0].length;
    const height = matrix.length;
    
    // Transpose for icon format
    const transposed = [];
    for (let x = 0; x < width; x++) {
        const column = [];
        for (let y = 0; y < height; y++) {
            column.push(matrix[y][x] ? 255 : 0);  // Convert to grayscale
        }
        transposed.push(column);
    }
    
    const json = JSON.stringify(transposed, null, 2);
    
    // Download
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `led_matrix_icon_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function copyToClipboard() {
    // Similar to exportJSON but uses navigator.clipboard
}
```

**3. Add UI Buttons**

```html
<!-- In index.html -->
<div class="export-controls">
    <button onclick="exportJSON()">⬇️ Download JSON</button>
    <button onclick="copyToClipboard()">📋 Copy JSON</button>
</div>
```

**4. Test**

- Draw a pattern
- Click "Download JSON"
- Verify format matches our icon system
- Test with IconManager

**5. Submit PR**

```bash
git checkout -b feature/json-export
git add app.js index.html
git commit -m "feat: Add JSON export functionality

- Add Download JSON button
- Add Copy to Clipboard button  
- Export in transposed format compatible with LED matrix apps
- Includes grayscale intensity support

This allows users to easily save their designs and use them
in custom LED matrix applications."
git push origin feature/json-export
```

Then open a Pull Request to Framework's repo with:
- Clear description of the feature
- Screenshots of the new buttons
- Example use case (our LED matrix monitoring app!)

#### Benefits for Framework

- ✅ Makes their tool more useful
- ✅ Enables custom application development
- ✅ Community contribution
- ✅ Better developer experience

---

## Option 3: PNG to Icon Renderer (Existing)

For converting existing images:

```bash
# From PNG/JPG to JSON
./icon_renderer.py image.png -o icons/rendered/my_icon --size 7x15 --levels 5 --animations static
```

See `ICON_RENDERER_README.md` for full details.

---

## Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **icon_editor.html** | Works now, offline, easy | Basic features | Quick custom icons |
| **dotmatrixtool** | Official, polished UI | No export (yet) | When PR is merged |
| **icon_renderer.py** | Batch processing, automation | Requires source images | Converting existing art |

## Recommended Workflow

1. **Quick custom icons**: Use `icon_editor.html`
2. **Complex designs**: Use image editor → `icon_renderer.py`
3. **Future**: Use dotmatrixtool once export feature is added

---

## Contributing

Want to help add export to dotmatrixtool? 

1. Check if someone already submitted a PR
2. Follow the implementation steps above
3. Test thoroughly
4. Submit PR with clear description
5. Link to this project as use case

**Let's make the Framework ecosystem better for everyone!** 🚀

