# Built In Dependencies
import time
import queue

# Internal Dependencies
from drawing import draw_cpu, draw_memory, draw_battery, draw_borders_left, draw_to_LEDs, draw_bar, draw_borders_right
from monitors import CPUMonitorThread, MemoryMonitorThread, BatteryMonitorThread, DiskMonitorThread, NetworkMonitorThread

# External Dependencies
try:
    import serial # pyserial
    from serial.tools import list_ports
    import numpy as np # This is used in a module and we import it here to fetch it if needed
    import screen_brightness_control as sbc
except ImportError:
    import pip
    for dependency in ["numpy", "pyserial", "screen-brightness-control"]:
        pip.main(['install', '--user', dependency])
    import serial
    from serial.tools import list_ports
    import screen_brightness_control as sbc

# print(sbc.get_brightness())

def init_device(location = "1-4.2"):
    try:
        # VID = 1234
        # PID = 5678
        device_list = list_ports.comports()
        for device in device_list:
            if device.location == location:
                s = serial.Serial(device.device, 115200)
                return s
    except Exception as e:
        print(e)
    
    
if __name__ == "__main__":
    # Left LED Matrix location: "1-4.2"
    # Right LED Matrix location: "1-3.3"

    # Set up monitors and serial for left LED Matrix
    min_background_brightness = 8
    max_background_brightness = 35
    min_foreground_brightness = 30
    max_foreground_brightness = 160

    cpu_queue = queue.Queue(2)
    cpu_monitor = CPUMonitorThread(cpu_queue)
    cpu_monitor.start()

    memory_queue = queue.Queue(2)
    memory_monitor = MemoryMonitorThread(memory_queue)
    memory_monitor.start()

    battery_queue = queue.Queue(2)
    battery_monitor = BatteryMonitorThread(battery_queue)
    battery_monitor.start()

    last_cpu_values = cpu_queue.get()
    last_memory_values = memory_queue.get()
    last_battery_values = battery_queue.get()

    s1 = init_device("1-4.2")


    # Set up monitors and serial for right LED Matrix
    disk_queue = queue.Queue(2)
    disk_monitor = DiskMonitorThread(disk_queue)
    disk_monitor.start()

    network_queue = queue.Queue(2)
    network_monitor = NetworkMonitorThread(network_queue)
    network_monitor.start()

    last_disk_read, last_disk_write = disk_queue.get()
    last_network_upload, last_network_download = network_queue.get()

    s2 = init_device("1-3.3")

    while True:
        try:
            screen_brightness = sbc.get_brightness()[0]
            background_value = int(screen_brightness / 100 * (max_background_brightness - min_background_brightness) + min_background_brightness)
            foreground_value = int(screen_brightness / 100 * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)

            # Draw to left LED Matrix
            if not cpu_queue.empty():
                last_cpu_values = cpu_queue.get()
            if not memory_queue.empty():
                last_memory_values = memory_queue.get()
            if not battery_queue.empty():
                last_battery_values = battery_queue.get()
            
            grid = np.zeros((9,34), dtype = int)
            draw_cpu(grid, last_cpu_values, foreground_value)
            draw_memory(grid, last_memory_values, foreground_value)
            draw_battery(grid, last_battery_values[0], last_battery_values[1], foreground_value)
            draw_borders_left(grid, background_value)
            draw_to_LEDs(s1, grid)

            # Draw to right LED Matrix
            if not disk_queue.empty():
                last_disk_read, last_disk_write = disk_queue.get()
            if not network_queue.empty():
                last_network_upload, last_network_download = network_queue.get()

            grid = np.zeros((9,34), dtype = int)
            draw_bar(grid, last_disk_read, foreground_value, bar_x_offset=1, draw_at_bottom=False) # Read
            draw_bar(grid, last_disk_write, foreground_value, bar_x_offset=1, draw_at_bottom=True) # Write
            draw_bar(grid, last_network_upload, foreground_value, bar_x_offset=5, draw_at_bottom=False) # Upload
            draw_bar(grid, last_network_download, foreground_value, bar_x_offset=5, draw_at_bottom=True) # Download
            draw_borders_right(grid, background_value)
            draw_to_LEDs(s2, grid)
            

        except Exception as e:
            print(f"Error in main loop: {e}")
            try:
                del s1
            except:
                pass
            try:
                del s2
            except:
                pass
            time.sleep(1.0)
            s1 = init_device("1-4.2")
            s2 = init_device("1-3.3")
        time.sleep(0.05)