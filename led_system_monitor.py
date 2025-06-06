# Built In Dependencies
import time
import queue
import sys
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


# Internal Dependencies
from drawing import draw_cpu, draw_memory, draw_battery, draw_temps, draw_borders_left, draw_bar, draw_borders_right, \
    draw_borders_right2, draw_ids_left, draw_ids_right, DrawingThread
from monitors import CPUMonitor, MemoryMonitor, BatteryMonitor, DiskMonitor, NetworkMonitor, \
    TemperatureMonitor, FanSpeedMonitor, get_monitor_brightness

# External Dependencies
import numpy as np
from pynput import keyboard
from pynput.keyboard import Key, Listener


def main(args):    
    # Left LED Matrix location: "1-3.2"
    # Right LED Matrix location: "1-3.3"
    global alt_pressed
    alt_pressed = False
    global i_pressed
    i_pressed = False
    # Number of main loop iterations with key pressed before keypress is recognized
    
    if len(sys.argv) > 1 and sys.argv[1] == 'io':
        show_network_disk_io = True
    else:
        show_network_disk_io = None
    print(f"Right panel shows {'Disk and Network I/o' if show_network_disk_io is not None else 'Temps and fan speeds'}")
    

    # Set up monitors and serial for left LED Matrix
    min_background_brightness = 12
    max_background_brightness = 35
    min_foreground_brightness = 24
    max_foreground_brightness = 160

    cpu_monitor = CPUMonitor()
    memory_monitor = MemoryMonitor()
    battery_monitor = BatteryMonitor()
    temperature_monitor = TemperatureMonitor()
    fan_speed_monitor = FanSpeedMonitor()

    left_drawing_queue = queue.Queue(2)
    left_drawing_thread = DrawingThread("1-3.2", left_drawing_queue)
    left_drawing_thread.start()


    # Set up monitors and serial for right LED Matrix
    disk_monitor = DiskMonitor()
    network_monitor = NetworkMonitor()

    right_drawing_queue = queue.Queue(2)
    right_drawing_thread = DrawingThread("1-3.3", right_drawing_queue)
    right_drawing_thread.start()
        
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

    with Listener(
        on_press=on_press,
        on_release=on_release) as listener:
        while True:
            try:
                screen_brightness = get_monitor_brightness()
                background_value = int(screen_brightness * (max_background_brightness - min_background_brightness) + min_background_brightness)
                foreground_value = int(screen_brightness * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)
                grid = np.zeros((9,34), dtype = int)
                if i_pressed and alt_pressed:
                    draw_ids_left(grid, args.top_left, args.bottom_left, args.top_right, args.bottom_right, foreground_value)
                    left_drawing_queue.put(grid)
                    grid = np.zeros((9,34), dtype = int)
                    draw_ids_right(grid, args.top_left, args.bottom_left, args.top_right, args.bottom_right, foreground_value)
                    right_drawing_queue.put(grid)
                    grid = np.zeros((9,34), dtype = int)
                    time.sleep(0.1)
                    continue

                # Draw to left LED Matrix
                if args.top_left == 'cpu': 
                    last_cpu_values = cpu_monitor.get()
                    draw_cpu(grid, last_cpu_values, foreground_value)
                else:
                    print(f"Unrecognized display option for top left matrix: {args.top_left}")
                    
                if args.bottom_left == 'mem/bat': 
                    last_memory_values = memory_monitor.get()
                    last_battery_values = battery_monitor.get()
                    draw_memory(grid, last_memory_values, foreground_value)
                    draw_battery(grid, last_battery_values[0], last_battery_values[1], foreground_value)
                else:
                    print("Unrecognized display option for bottom left matrix: {args.bottom_left}")
                draw_borders_left(grid, background_value)
                left_drawing_queue.put(grid)
                
                # Draw to right LED Matrix
                grid = np.zeros((9,34), dtype = int)
                if args.top_right == 'disk':
                    last_disk_read, last_disk_write = disk_monitor.get()
                    draw_bar(grid, last_disk_read, foreground_value, bar_x_offset=1, draw_at_bottom=False) # Read
                    draw_bar(grid, last_disk_write, foreground_value, bar_x_offset=5, draw_at_bottom=False) # Write
                    draw_borders_right(grid, background_value)
                elif args.top_right == 'temps':
                    temp_values = temperature_monitor.get()
                    draw_temps(grid, temp_values, foreground_value)
                    draw_borders_right2(grid, background_value)
                else:
                    print("Unrecognized display option for top right matrix: {args.top_right}")
                    
                if args.bottom_right == 'network':
                    last_network_upload, last_network_download = network_monitor.get()
                    draw_bar(grid, last_network_upload, foreground_value, bar_x_offset=1, draw_at_bottom=True) # Upload
                    draw_bar(grid, last_network_download, foreground_value, bar_x_offset=5, draw_at_bottom=True) # Download
                    
                elif args.bottom_right == 'fans':
                    fan_speeds = fan_speed_monitor.get()
                    draw_bar(grid, fan_speeds[0], foreground_value, bar_x_offset=1, draw_at_bottom=True)
                    draw_bar(grid, fan_speeds[1], foreground_value, bar_x_offset=5, draw_at_bottom=True)
                else:
                    print("Unrecognized display option for bottom right matrix: {args.bottom_right}")
                
                right_drawing_queue.put(grid)
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
    parser = ArgumentParser(prog="FW LED System Monitor", add_help=False,
                            description="Displays system performance metrics in the Framework 16 LED Matrix input module",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-h", "--help", action="help",
                         help="Show this help message and exit")
    
    addGroup = parser.add_argument_group(title = "Metrics Display Options")
    addGroup.add_argument("-tl", "--top-left", type=str, default="cpu", metavar="No additoinal options available yet",
                         help="Metrics to display in the top section of the left matrix device")
    addGroup.add_argument("-bl", "--bottom-left", type=str, default="mem/bat", metavar="No additional options available yet",
                         help="Metrics to display in the bottom section of the left matrix device")
    addGroup.add_argument("-tr", "--top-right", type=str, default="disk", metavar="disk | temps",
                         help="Metrics to display in the top section of the right matrix device")
    addGroup.add_argument("-br", "--bottom-right", type=str, default="network", metavar="network | fans",
                         help="Metrics to display in the bottom section of the right matrix device")
    
    args = parser.parse_args()
    print(f"top left {args.top_left}")
    print(f"bottom left {args.bottom_left}")
    print(f"top right {args.top_right}")
    print(f"bottom right {args.bottom_right}")
    
    main(args)