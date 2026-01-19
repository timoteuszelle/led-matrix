# Screen Lock Feature - MVP Implementation Status

**Feature Request**: [Issue #22 - turn off or show lock symbol on screen lock](https://github.com/MidnightJava/led-matrix/issues/22)

**Branch**: `feature/animation-library`  
**Status**: Partial Implementation - Infrastructure Complete, Integration Pending

## What's Implemented

### ✅ Core Infrastructure

1. **IconManager** (`icon_manager.py`)
   - Loads and caches pre-rendered JSON icons
   - Search paths: repo-local → XDG_DATA_HOME → ~/.local/share
   - Includes `overlay_icon()` helper for positioning icons on grids

2. **ScreenLockMonitor** (`monitors.py`)
   - Polls `loginctl` for screen lock state
   - Configurable poll interval
   - Force state override for testing
   - No external dependencies beyond `loginctl`

3. **Display Control** (`commands.py`)
   - `set_display_on(serial, on=True|False)` for turning displays on/off

4. **Lock Icons**
   - `icons/rendered/lock_small/static.json` (7x15) - for single panel or dual-separate
   - `icons/rendered/lock_large/static.json` (9x34) - for dual-combined panel

## What's Needed (Integration)

### 🔨 Main Loop Integration

The screen lock logic needs to be integrated into `led_system_monitor.py` where the main rendering loop runs. This requires:

1. **Config Parsing**
   - Add `screen_lock` section to `config.yaml` (see Configuration below)
   - Parse config in `get_config()` or app startup
   - Supply sensible defaults when section is missing

2. **Monitor Lifecycle**
   - If `screen_lock.enabled == true`:
     - Create `IconManager` instance
     - Pre-load configured icon (fail-fast if missing)
     - Create and start `ScreenLockMonitor`
   - On shutdown: call `monitor.stop()`

3. **Lock State Handling** (in main rendering loop)
   - Track `last_locked_state` to detect transitions
   - On lock transition:
     - **behavior='off'**: Call `set_display_on(serial, False)` for each panel, skip rendering
     - **behavior='icon'**: Draw blank grid, overlay icon, flush to each panel
   - On unlock transition:
     - **If was 'off'**: Call `set_display_on(serial, True)` to restore displays
     - Resume normal rendering

4. **Panel-Aware Rendering**
   - Detect panel count at startup (already done via `discover_led_devices()`)
   - Choose icon based on panel config and behavior:
     - Single panel → use `lock_small`
     - Dual panels + separate → use `lock_small` on each
     - Dual panels + combined → use `lock_large` (future enhancement)

## Configuration

Add to `config.yaml`:

```yaml
# Screen Lock Feature (default: disabled)
screen_lock:
  enabled: false               # Set to true to enable
  behavior: icon               # 'icon' or 'off'
  method: auto                 # Detection method (currently only 'loginctl')
  poll_interval_ms: 1000       # How often to check lock state
  icon:
    name: lock_small           # Icon to display ('lock_small' or 'lock_large')
    position: center           # Position on grid
    opacity: 1.0               # Icon opacity (0.0-1.0)
  force_state: auto            # Testing override: 'auto', 'locked', or 'unlocked'
```

**Important**: When `enabled: false` or section is missing, the feature is completely inert.

## Panel Behavior Options (Future Enhancement)

For dual-panel setups, behavior could be extended:
- `icon` - Auto-select based on panel count
- `icon_left` - Show icon on left panel only, turn off right
- `icon_right` - Show icon on right panel only, turn off left
- `icon_both_separate` - Show small icon centered on each panel
- `icon_combined` - Treat as single wide display, show large icon
- `off` - Turn off all panels

For MVP, recommend starting with simple `icon` or `off` for all panels.

## Testing Instructions

### Prerequisites

```bash
# Runtime dependencies (already required by main app)
nix-shell -p python311Packages.numpy python311Packages.psutil python311Packages.pyserial python311Packages.pyyaml python311Packages.evdev

# For regenerating icons (optional)
nix-shell -p python311Packages.pillow python311Packages.numpy
```

### Test Lock Detection (without integration)

```python
# Test script
from monitors import ScreenLockMonitor
import time

monitor = ScreenLockMonitor(poll_interval=1.0)
monitor.start()

try:
    while True:
        print(f"Locked: {monitor.is_locked()}")
        time.sleep(1)
except KeyboardInterrupt:
    monitor.stop()
```

Test with:
```bash
loginctl lock-session      # Should show Locked: True
loginctl unlock-session    # Should show Locked: False
```

### Test Icon Loading

```python
from icon_manager import IconManager

mgr = IconManager()
icon_small = mgr.load_icon('lock_small')
icon_large = mgr.load_icon('lock_large')

print(f"Small icon shape: {icon_small.shape}")  # Should be (15, 7)
print(f"Large icon shape: {icon_large.shape}")  # Should be (34, 9)
```

### Full Integration Testing (after integration complete)

1. Enable in `config.yaml`:
   ```yaml
   screen_lock:
     enabled: true
     behavior: icon  # or 'off'
   ```

2. Run the LED matrix monitor:
   ```bash
   nix-shell -p python311Packages.numpy python311Packages.psutil python311Packages.pyserial python311Packages.pyyaml python311Packages.evdev
   python led_system_monitor.py
   ```

3. Lock/unlock to test:
   ```bash
   loginctl lock-session
   # Display should show lock icon (or turn off)
   
   loginctl unlock-session
   # Display should resume normal operation
   ```

4. Test force override (no actual locking required):
   ```yaml
   screen_lock:
     enabled: true
     force_state: locked  # Simulate locked state
   ```

## Implementation Notes

### Why Polling vs D-Bus Events?

- **MVP uses polling** for simplicity (no extra Python deps)
- Poll interval of 1 second is reasonable for lock detection
- D-Bus event listening can be added later if polling proves problematic

### Icon Orientation

- `icon_renderer.py` outputs transposed JSON (rows/cols swapped)
- `IconManager.load_icon()` loads as-is (already correct orientation for overlay)
- `overlay_icon()` handles positioning and opacity

### Panel Detection

- System auto-detects panels via `discover_led_devices()` in `led_system_monitor.py`
- Panels sorted left-to-right by USB port
- Each panel gets independent `DrawingThread` and queue

## Next Steps

1. **Complete Integration** (see "What's Needed" above)
2. **Test on Hardware** with actual LED panels
3. **Iterate on UX**:
   - Icon appearance/positioning
   - Transition smoothness
   - Multi-panel behavior
4. **Documentation**:
   - Update README with screen lock feature
   - Add to example configs
5. **Upstream Submission**:
   - After testing confirms value, open PR to upstream
   - Emphasize default-disabled, zero impact when not used

## Design Decisions

- **Default Disabled**: No behavior change unless explicitly enabled in config
- **Branch-Only**: Stays on `feature/animation-library` until maintainer approval
- **NixOS-Friendly**: Uses `loginctl`, works with home-folder configs
- **No External Deps**: Leverages existing psutil, numpy, etc.
- **Graceful Degradation**: If `loginctl` unavailable, monitor returns unlocked state

## Files Changed

- **New**: `icon_manager.py` - Icon loading/caching
- **Modified**: `monitors.py` - Added `ScreenLockMonitor` class
- **Modified**: `commands.py` - Added `set_display_on()` helper
- **New**: `icons/rendered/lock_small/static.json`
- **New**: `icons/rendered/lock_large/static.json`
- **Pending**: `led_system_monitor.py` - Main loop integration
- **Pending**: `config.yaml` - Add `screen_lock` section (example)

## Questions for Maintainer / Testers

1. **Icon Design**: Is the padlock icon suitable, or should it be redesigned?
2. **Behavior**: Should default be `icon` or `off`?
3. **Multi-Panel**: Which dual-panel behaviors are most useful?
4. **Polling Interval**: Is 1 second acceptable, or should it be configurable?
5. **Integration Point**: Best place in code to hook lock detection into render loop?

---

**MVP Goal**: Provide working screen lock detection + icon display for single panel, with clear path to multi-panel support.

