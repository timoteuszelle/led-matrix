#!/usr/bin/env python3
"""
Hardware Demo: Display lock icon on LED matrix panels
Shows simulated lock/unlock on both left and right panels

This is a standalone demo - doesn't interfere with normal operation
"""

import time
import numpy as np
from serial.tools import list_ports
import serial
import sys

# Import our components
from icon_manager import IconManager, overlay_icon
from drawing import draw_to_LEDs, init_device
from commands import set_display_on

def discover_led_devices():
    """Find connected LED matrix panels"""
    locations = []
    try:
        device_list = list_ports.comports()
        for device in device_list:
            if 'LED Matrix Input Module' in str(device):
                locations.append((device.location, device.device))
        # Sort by location to get left-right order
        import re
        return sorted(locations, key=lambda x: re.sub(r'^\d+\-\d+\.', '', x[0]))
    except Exception as e:
        print(f"Error finding LED devices: {e}")
        return []

def demo_lock_display(duration=10, cycle_time=3):
    """
    Demo lock icon display on hardware
    
    Args:
        duration: Total demo duration in seconds
        cycle_time: Time between lock/unlock in seconds
    """
    print("=" * 60)
    print("LED Matrix Lock Icon Demo")
    print("=" * 60)
    
    # Discover panels
    print("\nDiscovering LED panels...")
    led_devices = discover_led_devices()
    
    if not len(led_devices):
        print("❌ No LED panels found!")
        print("Make sure panels are connected and recognized by the system")
        return
    
    print(f"✓ Found {len(led_devices)} panel(s)")
    for i, (loc, dev) in enumerate(led_devices):
        side = "LEFT" if i == 0 else "RIGHT"
        print(f"  {side}: {dev} (location: {loc})")
    
    # Initialize serial connections
    print("\nInitializing serial connections...")
    serials = []
    for location, device_path in led_devices:
        try:
            s = init_device(location)
            if s:
                serials.append((location, s))
                print(f"✓ Connected to {location}")
            else:
                print(f"❌ Failed to connect to {location}")
        except Exception as e:
            print(f"❌ Error connecting to {location}: {e}")
    
    if not serials:
        print("\n❌ Could not connect to any panels")
        return
    
    # Load lock icon
    print("\nLoading lock icon...")
    try:
        icon_mgr = IconManager()
        lock_icon = icon_mgr.load_icon('lock_small')
        print(f"✓ Loaded lock icon: {lock_icon.shape}")
    except Exception as e:
        print(f"❌ Error loading icon: {e}")
        for _, s in serials:
            s.close()
        return
    
    print("\n" + "=" * 60)
    print("Starting Demo - Watch your LED panels!")
    print("=" * 60)
    print(f"\nCycling lock/unlock every {cycle_time} seconds for {duration} seconds")
    print("Press Ctrl+C to stop\n")
    
    # Demo loop
    start_time = time.time()
    locked = False
    last_toggle = start_time
    
    try:
        while (time.time() - start_time) < duration:
            current_time = time.time()
            
            # Toggle lock state every cycle_time seconds
            if current_time - last_toggle >= cycle_time:
                locked = not locked
                last_toggle = current_time
                
                if locked:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔒 SIMULATED LOCK - Displaying icon on both panels")
                    
                    # Create blank grids
                    grid_left = np.zeros((9, 34), dtype=np.uint8)
                    grid_right = np.zeros((9, 34), dtype=np.uint8)
                    
                    # Overlay lock icon centered on both
                    overlay_icon(grid_left, lock_icon, position='center', opacity=1.0)
                    overlay_icon(grid_right, lock_icon, position='center', opacity=1.0)
                    
                    # Send to panels
                    for idx, (location, s) in enumerate(serials):
                        grid = grid_left if idx == 0 else grid_right
                        draw_to_LEDs(s, grid)
                        side = "LEFT" if idx == 0 else "RIGHT"
                        print(f"  → {side} panel: Lock icon displayed ({np.count_nonzero(grid)} pixels)")
                
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔓 SIMULATED UNLOCK - Clearing panels")
                    
                    # Clear both panels
                    blank_grid = np.zeros((9, 34), dtype=np.uint8)
                    
                    for idx, (location, s) in enumerate(serials):
                        draw_to_LEDs(s, blank_grid)
                        side = "LEFT" if idx == 0 else "RIGHT"
                        print(f"  → {side} panel: Cleared")
            
            time.sleep(0.1)  # Small delay to prevent CPU spinning
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo stopped by user")
    
    finally:
        # Clean up: clear panels
        print("\nCleaning up...")
        blank_grid = np.zeros((9, 34), dtype=np.uint8)
        for idx, (location, s) in enumerate(serials):
            try:
                draw_to_LEDs(s, blank_grid)
                s.close()
                side = "LEFT" if idx == 0 else "RIGHT"
                print(f"✓ {side} panel cleared and closed")
            except Exception as e:
                print(f"❌ Error during cleanup: {e}")
        
        print("\n✓ Demo complete!")

def demo_display_off(duration=5):
    """
    Demo display on/off functionality
    
    Args:
        duration: How long to keep displays off (seconds)
    """
    print("=" * 60)
    print("LED Matrix Display On/Off Demo")
    print("=" * 60)
    
    # Discover and connect
    print("\nDiscovering LED panels...")
    led_devices = discover_led_devices()
    
    if not len(led_devices):
        print("❌ No LED panels found!")
        return
    
    print(f"✓ Found {len(led_devices)} panel(s)")
    
    serials = []
    for location, device_path in led_devices:
        try:
            s = init_device(location)
            if s:
                serials.append(s)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if not serials:
        print("❌ Could not connect to any panels")
        return
    
    print(f"\n✓ Connected to {len(serials)} panel(s)")
    
    try:
        print("\n⚫ Turning displays OFF...")
        for s in serials:
            set_display_on(s, False)
        print(f"   Displays off for {duration} seconds")
        
        time.sleep(duration)
        
        print("\n⚪ Turning displays ON...")
        for s in serials:
            set_display_on(s, True)
        print("   Displays restored")
        
    finally:
        for s in serials:
            s.close()
        print("\n✓ Demo complete!")

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'off':
            demo_display_off(duration=5)
        elif mode == 'icon':
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 15
            cycle = int(sys.argv[3]) if len(sys.argv) > 3 else 3
            demo_lock_display(duration=duration, cycle_time=cycle)
        else:
            print(f"Unknown mode: {mode}")
            print("Usage:")
            print("  python demo_hardware_lock.py icon [duration] [cycle_time]")
            print("  python demo_hardware_lock.py off")
    else:
        # Default: run lock icon demo
        demo_lock_display(duration=15, cycle_time=3)

if __name__ == '__main__':
    main()

