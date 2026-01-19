#!/usr/bin/env python3
"""
Test script for screen lock detection and icon loading
Run this to verify the infrastructure works before full integration
"""

import time
import numpy as np
from monitors import ScreenLockMonitor
from icon_manager import IconManager, overlay_icon

def test_lock_monitor(duration=10, force_state=None):
    """Test the screen lock monitor"""
    print("=" * 60)
    print("Testing ScreenLockMonitor")
    print("=" * 60)
    
    if force_state:
        print(f"Force state: {force_state} (simulating without actual lock)")
        monitor = ScreenLockMonitor(poll_interval=1.0, force_state=force_state)
    else:
        print("Monitoring real lock state from loginctl")
        print("Try running: loginctl lock-session / loginctl unlock-session")
        monitor = ScreenLockMonitor(poll_interval=1.0)
    
    monitor.start()
    print(f"Monitoring for {duration} seconds...\n")
    
    last_state = None
    try:
        for i in range(duration):
            locked = monitor.is_locked()
            if locked != last_state:
                state_str = "🔒 LOCKED" if locked else "🔓 UNLOCKED"
                print(f"[{time.strftime('%H:%M:%S')}] State changed: {state_str}")
                last_state = locked
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Status: {'🔒 Locked' if locked else '🔓 Unlocked'}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    finally:
        monitor.stop()
        print("\nMonitor stopped\n")

def test_icon_manager():
    """Test icon loading and display"""
    print("=" * 60)
    print("Testing IconManager")
    print("=" * 60)
    
    mgr = IconManager()
    
    # Load small icon
    print("\nLoading lock_small icon...")
    try:
        icon_small = mgr.load_icon('lock_small')
        print(f"✓ Loaded: shape={icon_small.shape}, dtype={icon_small.dtype}")
        print(f"  Value range: {icon_small.min()}-{icon_small.max()}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Load large icon
    print("\nLoading lock_large icon...")
    try:
        icon_large = mgr.load_icon('lock_large')
        print(f"✓ Loaded: shape={icon_large.shape}, dtype={icon_large.dtype}")
        print(f"  Value range: {icon_large.min()}-{icon_large.max()}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test caching
    print("\nTesting cache (should be instant)...")
    start = time.time()
    icon_small_cached = mgr.load_icon('lock_small')
    elapsed = time.time() - start
    print(f"✓ Cached load took {elapsed*1000:.2f}ms")
    print(f"  Same object: {icon_small is icon_small_cached}")
    
    print("\n")

def test_icon_overlay():
    """Test icon overlay on a grid"""
    print("=" * 60)
    print("Testing Icon Overlay")
    print("=" * 60)
    
    mgr = IconManager()
    icon = mgr.load_icon('lock_small')
    
    # Create a blank 9x34 grid (single LED panel size)
    grid = np.zeros((9, 34), dtype=np.uint8)
    
    print(f"\nGrid shape: {grid.shape}")
    print(f"Icon shape: {icon.shape}")
    
    # Overlay icon in center
    print("\nOverlaying icon (center position, opacity=1.0)...")
    overlay_icon(grid, icon, position='center', opacity=1.0)
    
    # Check if icon was placed
    non_zero = np.count_nonzero(grid)
    print(f"✓ Non-zero pixels in grid: {non_zero}")
    print(f"  Icon placed successfully: {non_zero > 0}")
    
    # Show ASCII representation
    print("\nASCII preview of overlaid grid:")
    print("-" * 36)
    chars = ' .:-=+*#%@'
    for row in grid:
        line = ''
        for pixel in row:
            idx = int((pixel / 255) * (len(chars) - 1))
            line += chars[idx]
        print(line)
    print("-" * 36)
    print()

def test_combined():
    """Combined test: simulate lock event with icon display"""
    print("=" * 60)
    print("Combined Test: Lock Event Simulation")
    print("=" * 60)
    print("\nSimulating screen lock scenario...\n")
    
    # Setup
    mgr = IconManager()
    icon = mgr.load_icon('lock_small')
    monitor = ScreenLockMonitor(poll_interval=0.5, force_state='auto')
    monitor.start()
    
    # Create grids for left and right panels (dual panel simulation)
    grid_left = np.zeros((9, 34), dtype=np.uint8)
    grid_right = np.zeros((9, 34), dtype=np.uint8)
    
    print("Scenario: System has 2 panels detected")
    print("Behavior: When locked, show icon on both panels")
    print("\nMonitoring for 15 seconds (try locking/unlocking)...\n")
    
    last_locked = None
    try:
        for i in range(30):  # 15 seconds at 0.5s intervals
            locked = monitor.is_locked()
            
            if locked != last_locked:
                if locked:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔒 LOCKED - Displaying lock icon")
                    # Clear grids and overlay icon
                    grid_left.fill(0)
                    grid_right.fill(0)
                    overlay_icon(grid_left, icon, position='center', opacity=1.0)
                    overlay_icon(grid_right, icon, position='center', opacity=1.0)
                    print(f"  → Left panel: {np.count_nonzero(grid_left)} pixels lit")
                    print(f"  → Right panel: {np.count_nonzero(grid_right)} pixels lit")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔓 UNLOCKED - Resuming normal display")
                    print(f"  → Panels would show normal content")
                
                last_locked = locked
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    finally:
        monitor.stop()
        print("\nTest complete\n")

def main():
    """Run all tests"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'monitor':
            force = sys.argv[2] if len(sys.argv) > 2 else None
            test_lock_monitor(duration=15, force_state=force)
        elif mode == 'icons':
            test_icon_manager()
        elif mode == 'overlay':
            test_icon_overlay()
        elif mode == 'combined':
            test_combined()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python test_screen_lock.py [monitor|icons|overlay|combined]")
    else:
        # Run all tests
        test_icon_manager()
        test_icon_overlay()
        print("\nNow testing lock monitor (Ctrl+C to skip)...")
        time.sleep(2)
        test_lock_monitor(duration=10)
        print("\nRunning combined simulation...")
        time.sleep(2)
        test_combined()

if __name__ == '__main__':
    main()

