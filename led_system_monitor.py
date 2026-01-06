# Built In Dependencies
import time
import queue
import sys
import re
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import importlib.util
import sys
import os
from collections import defaultdict


# Internal Dependencies
from drawing import draw_outline_border, draw_ids, draw_id, draw_app, draw_app_border, DrawingThread
from monitors import CPUMonitor, MemoryMonitor, BatteryMonitor, DiskMonitor, NetworkMonitor, get_monitor_brightness

# External Dependencies
import numpy as np
import evdev
from yaml import safe_load
try:
    from pynput.keyboard import Key, Listener
except:
    print("Unable to use pynput key listener, defaulting to evdev (if supported)")
from serial.tools import list_ports

KEY_I = ('KEY_I', 23)
MODIFIER_KEYS = [('KEY_RIGHTALT', 100), ('KEY_LEFTALT', 56)]

def get_config(config_file):
    with open(config_file, 'r') as f:
       return safe_load(f)

def discover_led_devices():
    locations = []
    try:
        device_list = list_ports.comports()
        for device in device_list:
            if 'LED Matrix Input Module' in str(device):
                locations.append((device.location, device.device))
        #location is of form: <bus>-<port>[-<port>]  (port is of form x.y:n.m)
        # Example: 1-3.3:1.0 (right device) , 1-3.2:1.0 (left device)
        # Sort by y:n.m to get the devices in left-right order
        return sorted(locations, key = lambda x: re.sub(r'^\d+\-\d+\.', '', x[0]))
    except Exception as e:
        print(f"An Exception occured while tring to locate LED Matrix devices. {e}")

def list_apps(base_apps, plugin_apps, quads):
    max_len = max(map(lambda x: len(x), base_apps + plugin_apps))
    print("Installed Apps:")
    print("   " + "Name".ljust(max_len+3, ' ') + "Source".ljust(12, " ") + "Configuration")
    configured_apps = {}
    for quad in quads.values():
        for app in quad:
            del app["app"] # Just the list name in the yaml file, value will be set to None
            configured_apps[app["name"]] = app
    for app in [*base_apps , *plugin_apps]:
        print(f"   {app.ljust(max_len+3, ' ')}", end='')
        print(f"{'plugin app'.ljust(12, ' ')if app in plugin_apps else 'base app'.ljust(12, ' ')}", end='')
        print(f"{configured_apps[app]}" if app in configured_apps.keys() else "No Configuration")
        
device = None
def main(args, base_apps, plugin_apps):    
    # Initialize evdev device for key listening if not disabled
    global device
    if not args.no_key_listener:
        try:
            device = evdev.InputDevice('/dev/input/event9')
        except (PermissionError, FileNotFoundError, OSError) as e:
            print(f"Warning: Cannot access keyboard device for key listening: {e}")
            print("Key listener will be disabled. Use --no-key-listener to suppress this warning.")
            args.no_key_listener = True
            device = None
    else:
        device = None

    ################################################################################
    ### Parse config file to enable control of apps by quadrant and by time slice ##
    ################################################################################
    config = get_config(args.config_file)
    duration = config['duration'] #Default config to be applied if not set in an app
    quads = config['quadrants']
    top_left,  bottom_left, top_right, bottom_right, = \
        quads['top-left'], quads['bottom-left'], quads['top-right'], quads['bottom-right']
    
    # Track index of active app, for cycling through apps in a quadrant by time slice
    app_idx = defaultdict(int)
    for quad in quads:
        app_idx[quad] = 0
        
    # Each app optionally specifes how long it stays active before cycling to the next one
    app_duration = defaultdict(int)
    for quad in quads.items():
        for app in quad[1]:
            app_duration[app["name"]] = int(app.get("duration", duration))

    if args.list_apps:
        list_apps(base_apps, plugin_apps, quads)
        sys.exit()

    led_devices = discover_led_devices()
    if not len(led_devices):
        print("No LED devices found")
        sys.exit(0)
    elif len(led_devices) == 1:
        print(f"Only one LED device found ({led_devices[0]}). Right panel args will be ignored")
    else:
        print(f"Found LED devices: Left: {led_devices[0]}, Right: {led_devices[1]}")
    locations = list(map(lambda x: x[0], led_devices))
    drawing_queues = []
    
    # Track key presses to reveal app ID in each quadrant or panel
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

    # Setup left panel drawing queue
    left_drawing_queue = queue.Queue(2)
    left_drawing_thread = DrawingThread(locations[0], left_drawing_queue)
    left_drawing_thread.set_animate(False)
    left_drawing_thread.start()    
    drawing_queues.append(left_drawing_queue)

    # Setup right panel drawing queue (if panel is present)
    if len(locations) == 2:
        right_drawing_queue = queue.Queue(2)
        right_drawing_thread = DrawingThread(locations[1], right_drawing_queue)
        right_drawing_thread.set_animate(False)
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
        
    def draw_snap(arg, grid, foreground_value, idx, file, snap_path, panel):
        draw_app(arg, grid, foreground_value, file, snap_path, panel)
        
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
    #################################################
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


    # Use pynput Listener for cross-platform compatibility, but fallback to evdev if available
    # Pynput stopped working on linux for unknonwn reason. Perhaps because wayland
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    # Track last draw time, to enable cycling through them for each quadrannt
    base_time_map = {
        # Each dict stores last draw time for each app
        'top-left': defaultdict(lambda: time.monotonic()),
        'bottom-left': defaultdict(lambda: time.monotonic()),
        'top-right': defaultdict(lambda: time.monotonic()),
        'bottom-right': defaultdict(lambda: time.monotonic()),
    }

    # Used to detect that the key listener was activated, for restoring anination mode after ID display
    latch_key_combo = False
    # Main loop: Displays selected apps per quadrant and applies animation as configured
    while True:
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
            evdev_key_pressed = True if (MODIFIER_KEYS[0] in active_keys or MODIFIER_KEYS[1] in active_keys) and KEY_I in active_keys and device else False
            pynput_key_pressed = i_pressed and alt_pressed
            key_combo_active = (evdev_key_pressed or pynput_key_pressed) and not args.no_key_listener

            # Track when an app is changed in either panel, used to manage animation state
            idx_changed = {
                left_drawing_queue: False,
                right_drawing_queue: False
            }
            for quadrant,apps in quads.items():
                    app = apps[app_idx[quadrant]]
                    if time.monotonic() - base_time_map[quadrant][app['name']] >= int(app_duration[app['name']]):
                        if 'left' in quadrant:
                            idx_changed[left_drawing_queue] = True
                        else:
                            idx_changed[right_drawing_queue] = True
                        app_idx[quadrant] = (app_idx[quadrant] + 1) % len(quads[quadrant])
                        app = apps[app_idx[quadrant]]
                        base_time_map[quadrant][app['name']] = time.monotonic()

            left_args = [
                top_left[app_idx['top-left']],
                bottom_left[app_idx['bottom-left']],
            ]

            right_args = [
                top_right[app_idx['top-right']],
                bottom_right[app_idx['bottom-right']]
            ]

            # Capture animating state so we can restart it if necessary after stopping it for ID display
            animating_left = left_args[0].get("animate", False) or left_args[1].get("animate", False)
            animating_right = right_args[0].get("animate", False) or right_args[1].get("animate", False)
            
            if key_combo_active:
                # Show app IDs for each quadrant or panel
                draw_outline_border(grid, background_value)
                #If app takes up entire panel, we draw the ID border differently
                if left_args[0].get("scope", None) == "panel":
                    draw_id(grid, left_args[0]['name'], foreground_value)
                else:
                    draw_ids(grid, left_args[0]['name'], left_args[1]['name'], foreground_value)
                left_drawing_queue.put((grid, False))
                
                if len(drawing_queues) > 1:  # Right panel exists
                    grid = np.zeros((9,34), dtype = int)
                    draw_outline_border(grid, background_value)
                    if right_args[0].get("scope", None) == "panel":
                        draw_id(grid, right_args[0]['name'], foreground_value)
                    else:
                        draw_ids(grid, right_args[0]['name'], right_args[1]['name'], foreground_value)
                    right_drawing_queue.put((grid, False))
                time.sleep(0.1)
                latch_key_combo = True
                continue
            
            for i, draw_queue in enumerate(drawing_queues):
                grid = np.zeros((9,34), dtype = int)
                if i == 0:
                    panel = 'left'
                    _args = left_args
                else:
                    panel = 'right'
                    _args = right_args
                for j, arg in enumerate(_args):
                    arg_name = arg['name']
                    if arg_name == "none": continue
                    if j == 0:
                        idx = 0
                        loc = 'top'
                    else:
                        idx = 16
                        loc = 'bottom'
                    try:
                        func = app_functions[arg_name]
                        func_args = [arg_name, grid, foreground_value, idx]
                        if 'args' in arg:
                            func_args.extend(arg.get("args", None))
                        func(*func_args)
                        animate = arg.get("animate", False)
                    except KeyError:
                        print(f"Unrecognized display option {arg_name} for {loc} {panel}")
                    # Single border draw for mem and bat together
                    if arg_name == 'mem-bat': arg_name = 'mem'
                    draw_app_border(arg_name, grid, background_value, idx)
                do_animate = None
                if idx_changed[draw_queue]:
                    do_animate = animate
                    idx_changed[draw_queue] = False
                # Restart animation if it was stopped for ID display
                if latch_key_combo:
                    if (animating_left and panel == 'left') or (animating_right and panel == 'right'):
                        do_animate = True
                draw_queue.put((grid, do_animate))
            latch_key_combo = False
                
                
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
    base_apps = ["cpu", "net", "disk", "mem-bat", "none"]
    plugin_apps = []
    ###############################################################
    ###  Load additional app names from plugins for listing insalled apps  ###
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
                plugin_apps += map(lambda o: o["name"], module.app_funcs)
    #################################################################
    parser = ArgumentParser(prog="FW LED System Monitor", add_help=False,
                            description="Displays system performance metrics in the Framework 16 LED Matrix input module",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    mode_group = parser.add_argument_group()
    mode_group.add_argument("--help", "-h", action="help",
                         help="Show this help message and exit")
    
    mode_group.add_argument("-config-file", "-cf", type=str, default="./config.yaml", help="File that specifiees which apps to run in each panel quadrant")
    mode_group.add_argument("--no-key-listener", "-nkl", action="store_true", help="Do not listen for key presses")
    mode_group.add_argument("--disable-plugins", "-dp", action="store_true", help="Do not load any plugin code")
    mode_group.add_argument("--list-apps", "-la", action="store_true", help="List the installed apps, and exit")
    
    args = parser.parse_args()
    if args.no_key_listener: print("Key listener disabled")
    print(f"Using config file {args.config_file}")
    
    main(args, base_apps, plugin_apps)

