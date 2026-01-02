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
from yaml import safe_load
from pynput.keyboard import Key, Listener
from serial.tools import list_ports


KEY_I = ('KEY_I', 23)
MODIFIER_KEYS = [('KEY_RIGHTALT', 100), ('KEY_LEFTALT', 56)]

def get_config():
    with open('./config.yaml', 'r') as f:
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
        
# Global device variable - will be initialized in main() if key listener enabled
device = None
def main(args):    
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

    config = get_config()
    interval = config['interval']
    quads = config['quadrants']
    top_left, top_right, bottom_right, bottom_left = \
        quads['top-left'], quads['top-right'], quads['bottom-right'], quads['bottom-left']
    app_intervals = [
        top_left.get('interval', interval),
        bottom_left.get('interval', interval),
        top_right.get('interval', interval),
        bottom_right.get('interval', interval)
    ]
    app_indices = [0, 0, 0, 0] #[top-left, bottom-left, top-right, bottom-right]
    
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
    
    # Track key presses to reveal metrics ID in each panel sectionListener
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
        print("key pressed")
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
    
    # Use pynput Listener for cross-platform compatibility, but fallback to evdev if available
    # Pynput stopped working on linux for unknonwn reason. Perhaps because wayland
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    base_time = [time.monotonic(), time.monotonic(), time.monotonic(), time.monotonic()]
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
            # print(active_keys)
            evdev_key_pressed = True if (MODIFIER_KEYS[0] in active_keys or MODIFIER_KEYS[1] in active_keys) and KEY_I in active_keys and device else False
            pynput_key_pressed = i_pressed and alt_pressed
            key_combo_active = (evdev_key_pressed or pynput_key_pressed) and not args.no_key_listener

            # Draw by half or whole panel, depending on program args
            if time.monotonic() - base_time[0] >= app_intervals[0]:
                app_indices[0] = (app_indices[0] + 1) % len(top_left['apps'])
                base_time[0] = time.monotonic()
            if time.monotonic() - base_time[1] >= app_intervals[1]:
                app_indices[1] = (app_indices[1] + 1) % len(bottom_left['apps'])
                base_time[1] = time.monotonic()
            if time.monotonic() - base_time[2] >= app_intervals[2]:
                app_indices[2] = (app_indices[2] + 1) % len(top_right['apps'])
                base_time[2] = time.monotonic()
            if time.monotonic() - base_time[3] >= app_intervals[3]:
                app_indices[3] = (app_indices[3] + 1) % len(bottom_right['apps'])
                base_time[3] = time.monotonic()

            left_args = [
                top_left['apps'][app_indices[0]],
                bottom_left['apps'][app_indices[1]],
            ]

            right_args = [
                top_right['apps'][app_indices[2]],
                bottom_right['apps'][app_indices[3]]
            ]
            
            if key_combo_active:
                # Show app IDs for both panels
                draw_outline_border(grid, background_value)
                if type(left_args[0]) is dict:
                    draw_id(grid, left_args[0].get("app-with-args", {}).get("name", None), foreground_value)
                else:
                    draw_ids(grid, left_args[0], left_args[1], foreground_value)
                left_drawing_queue.put(grid)
                
                if len(drawing_queues) > 1:  # Right panel exists
                    grid = np.zeros((9,34), dtype = int)
                    draw_outline_border(grid, background_value)
                    if type(right_args[0]) is dict:
                        draw_id(grid, right_args[0].get("app-with-args", {}).get("name", None), foreground_value)
                    else:
                        draw_ids(grid, right_args[0], right_args[1], foreground_value)
                    right_drawing_queue.put(grid)
                time.sleep(0.1)
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
                    arg_name = arg['app-with-args']['name'] if type(arg) is dict else arg
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
                        if type(arg) is dict:
                            func_args.extend(arg.get("app-with-args", {}).get("args", None))
                        func(*func_args)
                    except KeyError:
                        print(f"Unrecognized display option {arg_name} for {loc} {panel}")
                    if arg_name == 'mem-bat': arg_name = 'mem' # Single border draw for mem and bat together
                    draw_app_border(arg_name, grid, background_value, idx)
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
    
    mode_group.add_argument("--no-key-listener", "-nkl", action="store_true", help="Do not listen for key presses")
    mode_group.add_argument("--disable-plugins", "-dp", action="store_true", help="Do not load any plugin code")
    
    args = parser.parse_args()
    if args.no_key_listener: print("Key listener disabled")
    
    main(args)
