# Icon Editor - Future Enhancements

## Current Implementation ✅

The `icon_editor.html` provides a visual tool for creating static LED matrix icons:

- Draw custom icons with grayscale intensities (0-255)
- Three canvas sizes: 7x15, 9x34, 18x34
- Export to JSON format compatible with IconManager
- Dual-panel visualization with split view
- Drawing tools: clear, fill, invert

## Design Philosophy

**The current implementation is intentionally simple and extensible:**
- Single HTML file, no build process
- Pure JavaScript, no dependencies
- Clean separation: drawing logic, export logic, UI
- JSON format matches existing icon system

## Planned Feature: Animation Support 🎬

### Vision

Allow users to create **animated icons** directly in the browser:

1. **Frame-based editing**: Draw up to 30 frames
2. **Timeline view**: Navigate between frames
3. **Playback preview**: See animation loop before export
4. **Batch export**: Output all frames in animation directory structure

### Use Cases

- **Breathing effects**: Fade in/out
- **Rotating icons**: Spinner/loading animations  
- **State transitions**: Lock/unlock, on/off
- **Notifications**: Blinking alerts, progress indicators
- **App-specific**: Custom animations per app (CPU spike, network activity)

### Technical Design

#### Frame Management

```javascript
// Current: Single grid state
let grid = [];  // 2D array

// Future: Frame array
let frames = [];  // Array of 2D arrays
let currentFrame = 0;
let frameCount = 1;  // Default to single frame (backward compatible)
```

#### UI Additions

**Timeline Bar** (below canvas)
```
[Frame 1] [Frame 2] [Frame 3] [+] [▶ Play] [⏸ Pause]
```

**Frame Controls**
- Add frame (duplicate current or blank)
- Delete frame
- Reorder frames (drag-drop)
- Copy/paste frames
- Set loop count (1, infinite, custom)

**Playback Controls**
- Play/pause preview
- Adjust FPS (5, 10, 15, 30)
- Loop toggle

#### Export Format

**Single Frame** (existing):
```
icons/rendered/my_icon/static.json
```

**Animation** (matches existing icon_renderer.py format):
```
icons/rendered/my_animated_icon/
├── frame_00.json
├── frame_01.json
├── frame_02.json
└── ...
```

**Metadata** (new):
```json
{
  "name": "my_animated_icon",
  "frames": 15,
  "fps": 10,
  "loop": true,
  "size": [9, 34]
}
```

### Compatibility with Existing System

The animation system **already supports** frame-based animations:

1. **icon_renderer.py** outputs animations:
   - `render_fade_animation()`
   - `render_pulse_animation()`
   - `render_slide_animation()`
   - All output as `frame_00.json`, `frame_01.json`, etc.

2. **IconManager** can be extended:
   ```python
   # Current
   icon = mgr.load_icon('my_icon')  # Loads static.json
   
   # Future
   animation = mgr.load_animation('my_icon')  # Loads all frames
   # Returns: list of numpy arrays or Animation object
   ```

3. **Drawing system** supports frame sequences:
   - Snapshot system already loads/displays frames
   - Main loop can cycle through frames at specified FPS

### Implementation Phases

#### Phase 1: Core Animation UI (Foundation)
- [ ] Frame array data structure
- [ ] Timeline bar with frame thumbnails
- [ ] Add/delete/navigate frames
- [ ] Current frame indicator

#### Phase 2: Playback (Preview)
- [ ] Play/pause controls
- [ ] FPS control (5-30 fps)
- [ ] Loop toggle
- [ ] Frame timing display

#### Phase 3: Frame Tools (Workflow)
- [ ] Duplicate frame
- [ ] Copy/paste frame
- [ ] Onion skinning (show previous frame faintly)
- [ ] Batch operations (fill all, clear all)

#### Phase 4: Export (Integration)
- [ ] Multi-frame JSON export
- [ ] Animation metadata file
- [ ] Preview GIF export (bonus)
- [ ] Import existing animations

#### Phase 5: Advanced (Polish)
- [ ] Frame reordering (drag-drop)
- [ ] Tweening (auto-generate frames between keyframes)
- [ ] Easing functions (linear, ease-in, ease-out)
- [ ] Animation presets (fade, pulse, slide templates)

### Backward Compatibility

**Critical**: All enhancements must preserve current functionality:

✅ **Single-frame mode remains default**
- No animation UI shown by default
- Export still works as-is for static icons
- No breaking changes to JSON format

✅ **Progressive disclosure**
- "Enable Animation Mode" checkbox
- Shows timeline/controls only when enabled
- Keeps UI simple for basic use cases

✅ **File format compatibility**
- Static icons: `static.json` (unchanged)
- Animations: `frame_*.json` (matches icon_renderer.py)
- IconManager handles both transparently

### Code Structure (Future)

```javascript
// animation.js (new module - can be separate file)
class AnimationEditor {
    constructor(canvas, grid) {
        this.frames = [grid];  // Start with current grid
        this.currentFrame = 0;
        this.isPlaying = false;
        this.fps = 10;
    }
    
    addFrame() { /* ... */ }
    deleteFrame(index) { /* ... */ }
    setFrame(index) { /* ... */ }
    play() { /* ... */ }
    stop() { /* ... */ }
    exportFrames() { /* ... */ }
}
```

### Benefits

**For Users:**
- No external tools needed for animations
- Instant preview of animation loops
- Full control over timing and frames
- Export ready-to-use in app

**For Developers:**
- Standardized animation format
- Easy integration with IconManager
- No dependencies on external animation tools
- Consistent with existing icon_renderer.py output

**For Project:**
- Complete icon workflow (static + animated)
- Self-contained tooling
- Encourages custom animations
- Community contributions (users share animated icons)

## Next Steps (When Ready)

1. **Validate use cases**: Confirm animation needs with users
2. **Prototype Phase 1**: Basic frame management
3. **Test integration**: Ensure IconManager can load frame sequences
4. **Iterate on UX**: Get feedback on timeline/playback UI
5. **Document workflow**: Update ICON_CREATION.md with animation guide

## Notes

- Keep editor **lightweight** - avoid heavy animation libraries
- Consider **localStorage** for saving work in progress
- Add **keyboard shortcuts** (space = play/pause, arrow keys = navigate frames)
- Export **spritesheet** option (single image grid) for sharing
- Think about **collaborative features** (share animations as URLs)

---

**Status**: 📝 Planning  
**Priority**: Low (feature request, not blocking)  
**Effort**: Medium (2-3 implementation phases)  
**Value**: High (completes icon creation workflow)

