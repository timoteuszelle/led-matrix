import time
import math

import numpy as np

import serial

from commands import Commands, send_command

# This table represents the 3x3 grid of LEDs to be drawn for each fill ratio
lookup_table = np.array(
    [
        [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]
        ],
        [
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0]
        ],
        [
            [0, 1, 0],
            [0, 1, 0],
            [0, 0, 0]
        ],
        [
            [0, 1, 1],
            [0, 1, 0],
            [0, 0, 0]
        ],
        [
            [0, 1, 1],
            [0, 1, 1],
            [0, 0, 0]
        ],
        [
            [0, 1, 1],
            [0, 1, 1],
            [0, 0, 1]
        ],
        [
            [0, 1, 1],
            [0, 1, 1],
            [0, 1, 1]
        ],
        [
            [0, 1, 1],
            [0, 1, 1],
            [1, 1, 1]
        ],
        [
            [0, 1, 1],
            [1, 1, 1],
            [1, 1, 1]
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 1]
        ]
    ]
)

lightning_bolt = np.array( [[0,0,0,0,0,0,0], # 0
                            [0,0,0,0,0,1,0], # 1
                            [0,0,0,0,1,1,0], # 2
                            [0,0,0,1,1,0,0], # 3
                            [0,0,1,1,1,0,0], # 4
                            [0,1,1,1,0,0,0], # 5
                            [0,1,1,1,1,1,0], # 6
                            [0,0,0,1,1,1,0], # 7
                            [0,0,1,1,1,0,0], # 8
                            [0,0,1,1,0,0,0], # 9
                            [0,1,1,0,0,0,0], #10
                            [0,1,0,0,0,0,0], #11
                            [0,0,0,0,0,0,0]],#12
                            dtype=bool).T 


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
        if i <= remainder:
            pixels_col += 1
        grid[i+1,33-pixels_col:33] = fill_value
    if battery_plugged:
        pulse_amount = math.sin(time.time() / charging_pulse_time)
        grid[1:8,20:33][lightning_bolt] -= np.rint(fill_value + 10 * pulse_amount).astype(int)
        indices = grid[1:8,20:33] < 0
        grid[1:8,20:33][indices] = -grid[1:8,20:33][indices]
    

def draw_borders(grid, border_value):
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

def draw_to_LEDs(s, grid):
    for i in range(grid.shape[0]):
        params = bytearray([i]) + bytearray(grid[i, :].tolist())
        send_command(s, Commands.StageCol, parameters=params)
    send_command(s, Commands.FlushCols)


if __name__ == "__main__":
    # LED array is 34x9, and is indexed left to right top to bottom
    port = "COM3"
    with serial.Serial(port, 115200) as s:
        while True:
            grid = np.zeros((9,34), dtype = int)
            draw_cpu(grid, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], 30)   
            draw_memory(grid, 0.3, 30)
            draw_battery(grid, 0.75, True, 30)
            draw_borders(grid, 10)
            print(grid.T)
            draw_to_LEDs(s, grid)
            time.sleep(0.05)