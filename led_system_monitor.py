# Built In Dependencies
import sys
import glob
import time
import queue

# Internal Dependencies
from commands import Commands, send_command
from drawing import draw_cpu, draw_memory, draw_battery, draw_borders, draw_to_LEDs
from monitors import CPUMonitorThread, MemoryMonitorThread, BatteryMonitorThread

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

    cpu_queue = queue.Queue(2)
    cpu_monitor = CPUMonitorThread(cpu_queue)
    cpu_monitor.start()

    memory_queue = queue.Queue(2)
    memory_monitor = MemoryMonitorThread(memory_queue)
    memory_monitor.start()

    battery_queue = queue.Queue(2)
    battery_monitor = BatteryMonitorThread(battery_queue)
    battery_monitor.start()

    min_background_brightness = 8
    max_background_brightness = 20
    min_foreground_brightness = 30
    max_foreground_brightness = 110

    last_cpu_values = cpu_queue.get()
    last_memory_values = memory_queue.get()
    last_battery_values = battery_queue.get()

    s = init_device()

    while True:
        try:
            if not cpu_queue.empty():
                last_cpu_values = cpu_queue.get()
            if not memory_queue.empty():
                last_memory_values = memory_queue.get()
            if not battery_queue.empty():
                last_battery_values = battery_queue.get()
            
            screen_brightness = sbc.get_brightness()[0]
            background_value = int(screen_brightness / 100 * (max_background_brightness - min_background_brightness) + min_background_brightness)
            foreground_value = int(screen_brightness / 100 * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)
            grid = np.zeros((9,34), dtype = int)
            draw_cpu(grid, last_cpu_values, foreground_value)
            draw_memory(grid, last_memory_values, foreground_value)
            draw_battery(grid, last_battery_values[0], last_battery_values[1], foreground_value)
            draw_borders(grid, background_value)
            draw_to_LEDs(s, grid)
        except Exception as e:
            print(f"Error in main loop: {e}")
            s = init_device()
            time.sleep(1.0)
        time.sleep(0.05)



    # # print(send_command(port, Commands.Version, with_response=True))
    # with serial.Serial(port, 115200) as s:
    #     for cval in range(16):
    #         for column_number in range(9):
    #             column_values = [cval] * 34
    #             params = bytearray([column_number]) + bytearray(column_values)
    #             send_command(s, Commands.StageCol, parameters=params)
    #         print(f"Flushing cval: {cval}")
    #         send_command(s, Commands.FlushCols)

    # Columns are filled left to right top to bottom
    # with serial.Serial(port, 115200) as s:
    #     column_number = 0
    #     column_values = [50] * 17 + [0] * 17
    #     params = bytearray([column_number]) + bytearray(column_values)
    #     send_command(s, Commands.StageCol, parameters=params)
    #     send_command(s, Commands.FlushCols)