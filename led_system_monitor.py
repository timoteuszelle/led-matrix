# Built In Dependencies
import time
import queue

# Internal Dependencies
from drawing import draw_cpu, draw_memory, draw_battery, draw_borders_left, draw_bar, draw_borders_right, DrawingThread
from monitors import CPUMonitor, MemoryMonitor, BatteryMonitor, DiskMonitor, NetworkMonitor, get_monitor_brightness

# External Dependencies
import numpy as np
    
    
if __name__ == "__main__":
    # Left LED Matrix location: "1-4.2"
    # Right LED Matrix location: "1-3.3"

    # Set up monitors and serial for left LED Matrix
    min_background_brightness = 12
    max_background_brightness = 35
    min_foreground_brightness = 24
    max_foreground_brightness = 160

    cpu_monitor = CPUMonitor()
    memory_monitor = MemoryMonitor()
    battery_monitor = BatteryMonitor()

    left_drawing_queue = queue.Queue(2)
    left_drawing_thread = DrawingThread("1-4.2", left_drawing_queue)
    left_drawing_thread.start()


    # Set up monitors and serial for right LED Matrix
    disk_monitor = DiskMonitor()
    network_monitor = NetworkMonitor()

    right_drawing_queue = queue.Queue(2)
    right_drawing_thread = DrawingThread("1-3.3", right_drawing_queue)
    right_drawing_thread.start()

    while True:
        try:
            screen_brightness = get_monitor_brightness()
            background_value = int(screen_brightness * (max_background_brightness - min_background_brightness) + min_background_brightness)
            foreground_value = int(screen_brightness * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)

            left_start_time = time.time()
            # Draw to left LED Matrix
            last_cpu_values = cpu_monitor.get()
            last_memory_values = memory_monitor.get()
            last_battery_values = battery_monitor.get()

            grid = np.zeros((9,34), dtype = int)
            draw_cpu(grid, last_cpu_values, foreground_value)
            draw_memory(grid, last_memory_values, foreground_value)
            draw_battery(grid, last_battery_values[0], last_battery_values[1], foreground_value)
            draw_borders_left(grid, background_value)
            left_drawing_queue.put(grid)

            # Draw to right LED Matrix
            last_disk_read, last_disk_write = disk_monitor.get()
            last_network_upload, last_network_download = network_monitor.get()

            grid = np.zeros((9,34), dtype = int)
            draw_bar(grid, last_disk_read, foreground_value, bar_x_offset=1, draw_at_bottom=False) # Read
            draw_bar(grid, last_disk_write, foreground_value, bar_x_offset=1, draw_at_bottom=True) # Write
            draw_bar(grid, last_network_upload, foreground_value, bar_x_offset=5, draw_at_bottom=False) # Upload
            draw_bar(grid, last_network_download, foreground_value, bar_x_offset=5, draw_at_bottom=True) # Download
            draw_borders_right(grid, background_value)
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