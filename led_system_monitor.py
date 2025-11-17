# Built In Dependencies
import time
import queue
import sys
import re
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import importlib.util
import sys
import os


# Internal Dependencies
from drawing import draw_outline_border, draw_ids, draw_id, draw_app, draw_app_border, DrawingThread
from monitors import CPUMonitor, MemoryMonitor, BatteryMonitor, DiskMonitor, NetworkMonitor, get_monitor_brightness

# External Dependencies
import numpy as np
import evdev
from pynput.keyboard import Key, Listener
from serial.tools import list_ports


KEY_I = ('KEY_I', 23)
MODIFIER_KEYS = [('KEY_RIGHTALT', 100), ('KEY_LEFTALT', 56)]

def discover_led_devices():
    locations = []
    try:
        device_list = list_ports.comports()
        for device in device_list:
            if 'LED Matrix Input Module' in str(device):
                locations.append((device.location, device.device))
        #location is of form: <bus>-<port>[-<port>]… port is of form x.y:n.m
        # Sort by y:n.m to get the devices in left-right order
        return sorted(locations, key = lambda x: re.sub(r'^\d+\-\d+\.', '', x[0]))
    except Exception as e:
        print(f"An Exception occured while tring to locate LED Matrix devices. {e}")
        
# Global device variable - will be initialized in main() if key listener enabled
device = None
def main(args):    
    # Initialize evdev device for key listening if not disabled
    global device
    if not args.no_key_listener:
        try:
            device = evdev.InputDevice('/dev/input/event7')
        except (PermissionError, FileNotFoundError, OSError) as e:
            print(f"Warning: Cannot access keyboard device for key listening: {e}")
            print("Key listener will be disabled. Use --no-key-listener to suppress this warning.")
            args.no_key_listener = True
            device = None
    else:
        device = None
    
    led_devices = discover_led_devices()
    if not len(led_devices):
        print("No LED devices found")
        sys.exit(0)
    elif len(led_devices) == 1:
        print(f"Only one LED device found ({led_devices[0]}). Right panel args will be ignored")
        args.top_right = args.bottom_right = "none"
    else:
        print(f"Found LED devices: Left: {led_devices[0]}, Right: {led_devices[1]}")
    locations = list(map(lambda x: x[0], led_devices))
    drawing_queues = []
    
    # Track key presses to reveal metrics ID in each panel section
    global alt_pressed
    alt_pressed = False
    global i_pressed
    i_pressed = False
    
    # Set up monitors and brightness parameters
    min_background_brightness = 12
    max_background_brightness = 35
    min_foreground_brightness = 24
    max_foreground_brightness = 160

    cpu_monitor = CPUMonitor()
    memory_monitor = MemoryMonitor()
    battery_monitor = BatteryMonitor()
    disk_monitor = DiskMonitor()
    network_monitor = NetworkMonitor()

    # Setuop left panel drawing queue
    left_drawing_queue = queue.Queue(2)
    left_drawing_thread = DrawingThread(locations[0], left_drawing_queue)
    left_drawing_thread.start()    
    drawing_queues.append(left_drawing_queue)

    # Setup right panel drawing queue (if present)
    if len(locations) == 2:
        right_drawing_queue = queue.Queue(2)
        right_drawing_thread = DrawingThread(locations[1], right_drawing_queue)
        right_drawing_thread.start()
        drawing_queues.append(right_drawing_queue)
    
    def draw_cpu(arg, grid, foreground_value, idx):
        last_cpu_values = cpu_monitor.get()
        draw_app(arg, grid, last_cpu_values, foreground_value, idx)
        
    def draw_mem_bat(arg, grid, foreground_value, idx):
        last_memory_values = memory_monitor.get()
        last_battery_values = battery_monitor.get()
        draw_app("mem", grid, last_memory_values, foreground_value, idx)
        draw_app("bat", grid, last_battery_values[0], last_battery_values[1], foreground_value, idx+3)
        
    def draw_disk(arg, grid, foreground_value, idx):
        last_disk_read, last_disk_write = disk_monitor.get()
        draw_app(arg, grid, last_disk_read, foreground_value, bar_x_offset=1, y=idx) # Read
        draw_app(arg, grid, last_disk_write, foreground_value, bar_x_offset=5, y=idx) # Write
        
    def draw_net(arg, grid, foreground_value, idx):
        last_network_upload, last_network_download = network_monitor.get()
        draw_app(arg, grid, last_network_upload, foreground_value, bar_x_offset=1, y=idx)
        draw_app(arg, grid, last_network_download, foreground_value, bar_x_offset=5, y=idx)
        
    def draw_snap(grid, foreground_value, file, snap_path, panel):
        draw_app("snap", grid, foreground_value, file, snap_path, panel)    
        
    app_functions = {
        "cpu": draw_cpu,
        "mem-bat": draw_mem_bat,
        "disk": draw_disk,
        "net": draw_net,
        "snap": draw_snap,
        "none": lambda *x: x # noop
    }
    
    def on_press(key):
        global alt_pressed
        global i_pressed
        if type(key).__name__ == 'KeyCode':
            if key.char == 'i':
                i_pressed = True
        elif key == Key.alt:
            alt_pressed = True

    def on_release(key):
        global alt_pressed
        global i_pressed
        if type(key).__name__ == 'KeyCode':
            if key.char == 'i':
                i_pressed = False
        elif key == Key.alt:
            alt_pressed = False
        if key == Key.esc:
            # Stop listener
            return False
        
    #################################################
        ###      Load app functions from plugins      ###
    if not re.search(r"--disable-plugins|-dp", str(sys.argv)):
        # Try to find plugins directory - either in current dir or installed location
        import os.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_dir = os.path.join(current_dir, 'plugins')
        if not os.path.exists(plugins_dir):
            plugins_dir = './plugins/'
        for file in os.listdir(plugins_dir):
            if file.endswith('_plugin.py'):
                module_name = re.sub("_plugin.py", "", file)
                file_path = os.path.join(plugins_dir, file)
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                for obj in module.app_funcs:
                    app_functions[obj["name"]] = obj["fn"]
    #################################################
    
    # Snapshot duration validation
    if hasattr(args, 'snapshot_duration') and hasattr(args, 'snapshot_interval'):
        if args.snapshot_duration > args.snapshot_interval:
            print("Snapshot duration must be less than snapshot interval. Exiting...")
            sys.exit(0)
    
    # Use pynput Listener for cross-platform compatibility, but fallback to evdev if available
    with Listener(
        on_press=on_press,
        on_release=on_release):
        while True:
            elapsed_time = time.time()
            show_snapshot = True if not hasattr(args, 'snapshot_interval') or args.snapshot_interval == 0 or elapsed_time % args.snapshot_interval <= getattr(args, 'snapshot_duration', 0) else False
            try:
                screen_brightness = get_monitor_brightness()
                background_value = int(screen_brightness * (max_background_brightness - min_background_brightness) + min_background_brightness)
                foreground_value = int(screen_brightness * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)

                # Clamp brightness values to the valid byte range
                background_value = max(0, min(255, background_value))
                foreground_value = max(0, min(255, foreground_value))

                grid = np.zeros((9,34), dtype = int)
                
                # Check for key combo using both evdev (if available) and pynput
                active_keys = device.active_keys(verbose=True) if device else []
                evdev_key_pressed = (MODIFIER_KEYS[0] in active_keys or MODIFIER_KEYS[1] in active_keys) and KEY_I in active_keys if device else False
                pynput_key_pressed = i_pressed and alt_pressed
                key_combo_active = (evdev_key_pressed or pynput_key_pressed) and not args.no_key_listener
                
                if key_combo_active:
                    # Show app IDs for both panels
                    if hasattr(args, 'left_snap') and args.left_snap and show_snapshot:
                        draw_id(grid, "snap", foreground_value)
                    else:
                        draw_outline_border(grid, background_value)
                        draw_ids(grid, args.top_left, args.bottom_left, foreground_value)
                    left_drawing_queue.put(grid)
                    
                    if len(drawing_queues) > 1:  # Right panel exists
                        grid = np.zeros((9,34), dtype = int)
                        if hasattr(args, 'right_snap') and args.right_snap and show_snapshot:
                            draw_id(grid, "snap", foreground_value)
                        else:
                            draw_outline_border(grid, background_value)
                            draw_ids(grid, args.top_right, args.bottom_right, foreground_value)
                        right_drawing_queue.put(grid)
                    time.sleep(0.1)
                    continue

                # Draw by half or whole panel, depending on program args
                for i, draw_queue in enumerate(drawing_queues):
                    grid = np.zeros((9,34), dtype = int)
                    if i == 0:
                        panel = 'left'
                        if hasattr(args, 'left_snap') and args.left_snap is not None and show_snapshot:
                            app_functions["snap"](grid, foreground_value, args.left_snap, getattr(args, 'snapshot_path', 'snapshot_files'), 'left')
                            draw_queue.put(grid)
                            continue
                        else:
                            _args = [args.top_left, args.bottom_left]
                    else:
                        panel = 'right'
                        if hasattr(args, 'right_snap') and args.right_snap is not None and show_snapshot:
                            app_functions["snap"](grid, foreground_value, args.right_snap, getattr(args, 'snapshot_path', 'snapshot_files'), 'right')
                            draw_queue.put(grid)
                            continue
                        _args = [args.top_right, args.bottom_right]
                    
                    for j, arg in enumerate(_args):
                        if j == 0:
                            idx = 0
                            loc = 'top'
                        else:
                            idx = 16
                            loc = 'bottom'
                        try:
                            func = app_functions[arg]
                            func(arg, grid, foreground_value, idx)
                        except KeyError:
                            print(f"Unrecognized display option {arg} for {loc} {panel}")
                        if arg == 'mem-bat': arg = 'mem' # Single border draw for mem and bat together
                        draw_app_border(arg, grid, background_value, idx)
                    draw_queue.put(grid)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                print(f"Error in main loop: {e}")
                traceback.print_exc()
                time.sleep(1.0)
            time.sleep(0.1)
            
        print("Exiting")
        
if __name__ == "__main__":
    app_names = ["cpu", "net", "disk", "mem-bat", "none"]
    ###############################################################
    ###  Load additional app names from plugins for arg parser  ###
    if not re.search(r"--disable-plugins|-dp", str(sys.argv)):
        # Try to find plugins directory - either in current dir or installed location
        import os.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_dir = os.path.join(current_dir, 'plugins')
        if not os.path.exists(plugins_dir):
            plugins_dir = './plugins/'
        for file in os.listdir(plugins_dir):
            if file.endswith('_plugin.py'):
                module_name = re.sub("_plugin.py", "", file)
                file_path = os.path.join(plugins_dir, file)
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                app_names += map(lambda o: o["name"], module.app_funcs)
    #################################################################
    parser = ArgumentParser(prog="FW LED System Monitor", add_help=False,
                            description="Displays system performance metrics in the Framework 16 LED Matrix input module",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    mode_group = parser.add_argument_group()
    mode_group.add_argument("--help", "-h", action="help",
                         help="Show this help message and exit")
    
    addGroup = parser.add_argument_group(title = "Metrics Display Options")
    addGroup.add_argument("--top-left", "-tl", type=str, default="cpu", choices=app_names,
                         help="Metrics to display in the top section of the left matrix panel")
    addGroup.add_argument("--bottom-left", "-bl", type=str, default="mem-bat", choices=app_names,
                         help="Metrics to display in the bottom section of the left matrix panel")
    addGroup.add_argument("--top-right", "-tr", type=str, default="disk", choices=app_names,
                         help="Metrics to display in the top section of the right matrix panel")
    addGroup.add_argument("--bottom-right", "-br", type=str, default="disk", choices=app_names,
                         help="Metrics to display in the top section of the right matrix panel")
    addGroup.add_argument("--left-snap", "-ls", type=str, default=None,
                         help="Snapshot file to display on the left panel. Specify * to cycle through all files in the snapshot dir")
    addGroup.add_argument("--right-snap", "-rs", type=str, default=None,
                         help="Snapshot file to display on the right panel. Specify * to cycle through all files in the snapshot dir")
    addGroup.add_argument("--snapshot-path", "-sp", type=str, default="snapshot_files",
                          help="The file path that contains either the snapshot files that may be displayed on either panel or " +
                          "'left' and 'right' directories that contain files that may be displayed on the respective panel")
    addGroup.add_argument("--snapshot-interval", "-si", type=int, default=0,
                          help="The interval (in seconds) at which the selected snapshot files will be rendered. A value " +
                          "of zero means the snapshots should be rendered continuously")
    addGroup.add_argument("--snapshot-duration", "-sd", type=int, default=0,
                          help="The number of seconds that the snapshot file will be rendered at the specified interval. Must be " +
                          "less than the value of --snapshot-interval")
    
    addGroup.add_argument("--no-key-listener", "-nkl", action="store_true", help="Do not listen for key presses")
    addGroup.add_argument("--disable-plugins", "-dp", action="store_true", help="Do not load any plugin code")
    
    args = parser.parse_args()
    print(f"top left {args.top_left}")
    print(f"bottom left {args.bottom_left}")
    print(f"top right {args.top_right}")
    print(f"bottom right {args.bottom_right}")
    print(f"left snap {args.left_snap}")
    print(f"right snap {args.right_snap}")
    if args.no_key_listener: print("Key listener disabled")
    
    main(args)
