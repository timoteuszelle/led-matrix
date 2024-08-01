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
# Correct table orientation for visual orientation when drawn
for i in range(lookup_table.shape[0]):
    lookup_table[i] = lookup_table[i].T


def spiral_index(fill_ratio):
    return int(round(fill_ratio * 9.999999 - 0.5))

def make_cpu_grid(cpu_values, border_value, fill_value):
    grid = np.zeros((9,34), dtype = int)
    for i, v in enumerate(cpu_values):
        column_number = i % 2
        row_number = i // 2
        fill_grid = lookup_table[spiral_index(v)]
        grid[1+column_number*4:4+column_number*4, 1+row_number*4:4+row_number*4] = fill_grid * fill_value
    
    # Fill in the borders
    grid[0, :16] = border_value
    grid[4, :16] = border_value
    grid[8, :16] = border_value
    grid[:, 0] = border_value
    grid[:, 4] = border_value
    grid[:, 8] = border_value
    grid[:, 12] = border_value
    grid[:, 16] = border_value
    return grid

def draw_to_LEDs(s, grid):
    for i in range(grid.shape[0]):
        params = bytearray([i]) + bytearray(grid[i, :].tolist())
        send_command(s, Commands.StageCol, parameters=params)
    send_command(s, Commands.FlushCols)


if __name__ == "__main__":
    # LED array is 34x9, and is indexed left to right top to bottom
    grid = make_cpu_grid([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], 10, 30)
    port = "COM3"
    with serial.Serial(port, 115200) as s:
        draw_to_LEDs(s, grid)