# Built In Dependencies
import time
import math
import threading

# Internal Dependencies
from commands import Commands, send_command

# External Dependencies
import numpy as np
import serial # pyserial
from serial.tools import list_ports

from patterns import lightning_bolt, lookup_table, id_cpu, id_mem, id_disk, id_net, id_fan, id_temp


# Correct table orientation for visual orientation when drawn
for i in range(lookup_table.shape[0]):
    lookup_table[i] = lookup_table[i].T


def spiral_index(fill_ratio):
    return int(round(fill_ratio * 9.999999 - 0.5))

# Takes up 15 rows, 7 columns, starting at 1,1
def draw_cpu(grid, cpu_values, fill_value):
    for i, v in enumerate(cpu_values):
        column_number = i % 2
        row_number = i // 2
        fill_grid = lookup_table[spiral_index(v)]
        grid[1+column_number*4:4+column_number*4, 1+row_number*4:4+row_number*4] = fill_grid * fill_value
        
# Takes up 15 rows, 7 columns, starting at 1,1
def draw_temps(grid, temp_values, fill_value):
    for i, v in enumerate(temp_values):
        column_number = i % 2
        row_number = i // 2
        fill_grid = lookup_table[spiral_index(v)]
        grid[1+column_number*4:4+column_number*4, 1+row_number*4:4+row_number*4] = fill_grid * fill_value


# Takes up 2 rows, 7 columns, starting at 17,1
def draw_memory(grid, memory_ratio, fill_value):
    lit_pixels = 7 * 2 * memory_ratio
    pixels_bottom = int(round(lit_pixels / 2))
    pixels_top = int(round((lit_pixels - 0.49) / 2))
    grid[1:1+pixels_top,17] = fill_value
    grid[1:1+pixels_bottom,18] = fill_value

# Takes up 13 rows, 7 columns, starting at 21,1
def draw_battery(grid, battery_ratio, battery_plugged, fill_value, battery_low_thresh = 0.07, battery_low_flash_time = 2, charging_pulse_time = 3):
    lit_pixels = int(round(13 * 7 * battery_ratio))
    pixels_base = lit_pixels // 7
    remainder = lit_pixels % 7
    if battery_ratio <= battery_low_thresh and not battery_plugged:
        if time.time() % battery_low_flash_time * 2 < battery_low_flash_time: # This will flash the battery indicator if too low
            return
    for i in range(7):
        pixels_col = pixels_base
        if i < remainder:
            pixels_col += 1
        grid[i+1,33-pixels_col:33] = fill_value
    if battery_plugged:
        pulse_amount = math.sin(time.time() / charging_pulse_time)
        grid[1:8,20:33][lightning_bolt] -= np.rint(fill_value + 10 * pulse_amount).astype(int)
        indices = grid[1:8,20:33] < 0
        grid[1:8,20:33][indices] = -grid[1:8,20:33][indices]
    

def draw_borders_left(grid, border_value):
    # Fill in the borders
    # Cpu vertical partitions
    grid[4, :16] = border_value
    # Cpu horizontal partitions
    grid[:, 4] = border_value
    grid[:, 8] = border_value
    grid[:, 12] = border_value
    grid[:, 16] = border_value
    # Memory bottom partition
    grid[:, 19] = border_value
    # Outer Edge borders
    grid[:, 0] = border_value # Top
    grid[0, :] = border_value # Left
    grid[8, :] = border_value # Right
    grid[:, 33] = border_value # Bottom


def draw_borders_right(grid, border_value):
    # Fill in the borders
    # Middle Partition borders
    grid[:, 16] = border_value
    grid[4, :] = border_value
    # Outer Edge borders
    grid[:, 0] = border_value # Top
    grid[0, :] = border_value # Left
    grid[8, :] = border_value # Right
    grid[:, 33] = border_value # Bottom
    
def draw_borders_right2(grid, border_value):
    # Fill in the borders
    # Vertical partition
    grid[4, :] = border_value
    # Temps horizontal partitions
    grid[:, 4] = border_value
    grid[:, 8] = border_value
    grid[:, 12] = border_value
    grid[:, 16] = border_value
    # Outer Edge borders
    grid[:, 0] = border_value # Top
    grid[0, :] = border_value # Left
    grid[8, :] = border_value # Right
    grid[:, 33] = border_value # Bottom


def draw_bar(grid, bar_ratio, bar_value, bar_x_offset = 1,draw_at_bottom = True):
    bar_width = 3
    bar_height = 16
    lit_pixels = int(round(bar_height * bar_width * bar_ratio))
    pixels_base = lit_pixels // bar_width
    remainder = lit_pixels % bar_width
    for i in range(bar_width):
        pixels_col = pixels_base
        if i < remainder:
            pixels_col += 1
        if draw_at_bottom:
            grid[bar_x_offset+i,33-pixels_col:33] = bar_value
        else:
            grid[bar_x_offset+i,1:1+pixels_col] = bar_value
            
def draw_ids_left(grid, top_left, bot_left, top_right, bot_right, fill_value):
    if top_left == 'cpu':
        fill_grid_top = id_cpu
    if bot_left == 'mem/bat':
        fill_grid_bot = id_mem
    grid[:, :17] = fill_grid_top * fill_value
    grid[:, 17:] = fill_grid_bot * fill_value
    
def draw_ids_right(grid, top_left, bot_left, top_right, bot_right, fill_value):
    if top_right == 'disk':
        fill_grid_top = id_disk
    elif top_right == 'temps':
        fill_grid_top = id_temp
    if bot_right == 'network':
        fill_grid_bot = id_net
    elif bot_right == 'fans':
        fill_grid_bot = id_fan
    grid[:, :17] = fill_grid_top * fill_value
    grid[:, 17:] = fill_grid_bot * fill_value

def draw_to_LEDs(s, grid):
    for i in range(grid.shape[0]):
        params = bytearray([i]) + bytearray(grid[i, :].tolist())
        send_command(s, Commands.StageCol, parameters=params)
    send_command(s, Commands.FlushCols)


def init_device(location = "1-4.2"):
    try:
        # VID = 1234
        # PID = 5678
        device_list = list_ports.comports()
        for device in device_list:
            if device.location and device.location.startswith(location):
                s = serial.Serial(device.device, 115200)
                return s
    except Exception as e:
        print(e)


class DrawingThread(threading.Thread):
    def __init__(self, port_location, input_queue):
        super().__init__()
        self.daemon = True
        self.port_location = port_location
        self.serial_port = init_device(self.port_location)
        self.input_queue = input_queue
    
    def run(self):
        while True:
            try:
                grid = self.input_queue.get()
                draw_to_LEDs(self.serial_port, grid)
            except Exception as e:
                print(f"Error in DrawingThread: {e}")
                del self.serial_port
                time.sleep(1.0)
                self.serial_port = init_device(self.port_location)

