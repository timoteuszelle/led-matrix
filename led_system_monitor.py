# Built In Dependencies
import sys
import glob
import time
import queue

# Internal Dependencies
from commands import Commands, send_command
from drawing import make_cpu_grid, draw_to_LEDs
from monitors import CPUMonitorThread

# External Dependencies
import serial # pyserial

def get_ports():
        """Returns a list of all available serial ports on the system.

        Raises:
            EnvironmentError: Will be returned if the platform is not Windows, Linux, Cygwin, or Darwin.

        Returns:
            [list(str)]: A list of valid serial ports on the system.
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i+1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = reversed(glob.glob('/dev/ttyUSB*'))
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result
    
    
if __name__ == "__main__":


    # print(get_ports())
    port = "COM3"

    cpu_queue = queue.Queue()
    cpu_monitor = CPUMonitorThread(cpu_queue)
    cpu_monitor.start()

    s = serial.Serial(port, 115200)

    while True:
        if not cpu_queue.empty():
            cpu_values = cpu_queue.get()
            grid = make_cpu_grid(cpu_values, 10, 30)
            draw_to_LEDs(s, grid)
        time.sleep(0.1)



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