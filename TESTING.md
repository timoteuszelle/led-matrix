# Quick Testing Guide - Screen Lock Feature

## Test Without Hardware

All tests can be run without LED panels connected. The infrastructure is fully functional.

### Quick Test Commands

```bash
# Enter nix-shell with dependencies
nix-shell -p python311Packages.numpy python311Packages.psutil

# Test 1: Icon loading (should show ✓ for both icons)
python test_screen_lock.py icons

# Test 2: Icon overlay with ASCII preview
python test_screen_lock.py overlay

# Test 3: Simulate LOCKED state (fake lock event)
python test_screen_lock.py monitor locked

# Test 4: Simulate UNLOCKED state  
python test_screen_lock.py monitor unlocked

# Test 5: Real lock detection (requires loginctl)
python test_screen_lock.py monitor

# Test 6: Full simulation with both panels
python test_screen_lock.py combined
```

### Expected Results

#### Test 1 - Icon Loading
```
✓ Loaded: shape=(7, 15), dtype=uint8
✓ Loaded: shape=(9, 34), dtype=uint8
✓ Cached load took 0.00ms
```

#### Test 2 - Icon Overlay
Shows ASCII art of the lock icon centered on a 9x34 grid:
```
             @@@@@@@@@@           
               @@@===@@           
               @@====@@           
               @@@===@@           
             @@@@@@@@@@           
```

#### Test 3 - Simulated Lock
```
[11:36:49] State changed: 🔒 LOCKED
[11:36:50] Status: 🔒 Locked
...
```

#### Test 4 - Simulated Unlock
```
[11:37:13] State changed: 🔓 UNLOCKED
[11:37:14] Status: 🔓 Unlocked
...
```

#### Test 6 - Combined Simulation
Simulates dual-panel setup:
```
🔒 LOCKED - Displaying lock icon
  → Left panel: 44 pixels lit
  → Right panel: 44 pixels lit

🔓 UNLOCKED - Resuming normal display
  → Panels would show normal content
```

## Test With Real Lock Events

If you want to test actual lock detection (without simulating):

```bash
# Terminal 1: Run the monitor
nix-shell -p python311Packages.numpy python311Packages.psutil
python test_screen_lock.py monitor

# Terminal 2: Lock/unlock your session
loginctl lock-session
# Watch Terminal 1 - should show 🔒 LOCKED

loginctl unlock-session  
# Watch Terminal 1 - should show 🔓 UNLOCKED
```

## What's Working

✅ **IconManager** - Loads icons from JSON, caches them  
✅ **ScreenLockMonitor** - Detects lock state via loginctl  
✅ **Icon Overlay** - Positions icons on grid  
✅ **Force State** - Can simulate lock/unlock without actual locking  
✅ **Multi-Panel Logic** - Ready for dual-panel setups

## What's Next

The components work perfectly! Next step is integrating into the main rendering loop in `led_system_monitor.py`. See `SCREEN_LOCK_MVP.md` for integration details.

## Troubleshooting

**"ModuleNotFoundError: No module named 'psutil'"**
- Make sure you're in nix-shell: `nix-shell -p python311Packages.numpy python311Packages.psutil`

**"Icon 'lock_small' not found"**
- Make sure you're running from the repo root directory
- Check that `icons/rendered/lock_small/static.json` exists

**"loginctl: command not found"**
- You're not on a systemd-based system
- Use `force_state` parameter to simulate: `python test_screen_lock.py monitor locked`

## One-Liner Tests

```bash
# Test everything is working
nix-shell -p python311Packages.numpy python311Packages.psutil --run "python test_screen_lock.py icons && python test_screen_lock.py overlay"

# Quick simulation of lock event
nix-shell -p python311Packages.numpy python311Packages.psutil --run "timeout 5 python test_screen_lock.py monitor locked"
```

