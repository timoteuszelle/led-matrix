# Built In Dependencies
import time
import psutil
import threading


class DiskMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 3, update_interval = 0.5):
        super().__init__()
        self.daemon = True
        self.read_usage_history = []
        self.write_usage_history = []
        self.history_times = []
        self.highest_read_rate = 0.00001
        self.highest_write_rate = 0.00001
        self.max_history_size = int(round(hysterisis_time / update_interval))
        self.update_interval = update_interval
        self.output_queue = output_queue

    def run(self):
        while True:
            try:
                if not self.output_queue.full():
                    disk_io = psutil.disk_io_counters()
                else:
                    print("Disk monitor queue is full")
                read_usage = disk_io.read_bytes
                write_usage = disk_io.write_bytes
                self.read_usage_history.append(read_usage)
                self.write_usage_history.append(write_usage)
                self.history_times.append(time.time())
                if len(self.read_usage_history) > self.max_history_size:
                    self.read_usage_history = self.read_usage_history[-self.max_history_size:]
                    self.write_usage_history = self.write_usage_history[-self.max_history_size:]
                    self.history_times = self.history_times[-self.max_history_size:]

                if len(self.read_usage_history) == self.max_history_size:
                    read_diff = self.read_usage_history[-1] - self.read_usage_history[0]
                    write_diff = self.write_usage_history[-1] - self.write_usage_history[0]
                    time_diff = self.history_times[-1] - self.history_times[0]
                    read_rate = read_diff / time_diff
                    write_rate = write_diff / time_diff
                    self.highest_read_rate = max(self.highest_read_rate, read_rate)
                    self.highest_write_rate = max(self.highest_write_rate, write_rate)
                    read_percent = min(1.0, read_rate / self.highest_read_rate)
                    write_percent = min(1.0, write_rate / self.highest_write_rate)
                    self.output_queue.put((read_percent, write_percent))
            except Exception as e:
                print(f"Error in DiskMonitorThread: {e}")
            time.sleep(self.update_interval)

class NetworkMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 3, update_interval = 0.5):
        super().__init__()
        self.daemon = True
        self.sent_usage_history = []
        self.recv_usage_history = []
        self.history_times = []
        self.highest_sent_rate = 0.00001
        self.highest_recv_rate = 0.00001
        self.max_history_size = int(round(hysterisis_time / update_interval))
        self.update_interval = update_interval
        self.output_queue = output_queue

    def run(self):
        while True:
            try:
                if not self.output_queue.full():
                    net_io = psutil.net_io_counters()
                else:
                    print("Network monitor queue is full")
                sent_usage = net_io.bytes_sent
                recv_usage = net_io.bytes_recv
                self.sent_usage_history.append(sent_usage)
                self.recv_usage_history.append(recv_usage)
                self.history_times.append(time.time())
                if len(self.sent_usage_history) > self.max_history_size:
                    self.sent_usage_history = self.sent_usage_history[-self.max_history_size:]
                    self.recv_usage_history = self.recv_usage_history[-self.max_history_size:]
                    self.history_times = self.history_times[-self.max_history_size:]

                if len(self.sent_usage_history) == self.max_history_size:
                    sent_diff = self.sent_usage_history[-1] - self.sent_usage_history[0]
                    recv_diff = self.recv_usage_history[-1] - self.recv_usage_history[0]
                    time_diff = self.history_times[-1] - self.history_times[0]
                    sent_rate = sent_diff / time_diff
                    recv_rate = recv_diff / time_diff
                    self.highest_sent_rate = max(self.highest_sent_rate, sent_rate)
                    self.highest_recv_rate = max(self.highest_recv_rate, recv_rate)
                    sent_percent = min(1.0, sent_rate / self.highest_sent_rate)
                    recv_percent = min(1.0, recv_rate / self.highest_recv_rate)
                    self.output_queue.put((sent_percent, recv_percent))
            except Exception as e:
                print(f"Error in NetworkMonitorThread: {e}")
            time.sleep(self.update_interval)

class CPUMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 3, update_interval = 0.5):
        super().__init__()
        self.daemon = True
        self.cpu_count = psutil.cpu_count() // 2 # 2 logical cores per physical core
        self.cpu_usage_history = [[] for _ in range(self.cpu_count)]
        self.history_times = []
        self.max_history_size = int(round(hysterisis_time / update_interval))
        self.update_interval = update_interval
        self.output_queue = output_queue

    def run(self):
        while True:
            try:
                if not self.output_queue.full():
                    cpu_usage = psutil.cpu_percent(percpu=True)
                else:
                    print("CPU monitor queue is full")
                for i in range(self.cpu_count):
                    useage = 2 * max(cpu_usage[2*i], cpu_usage[2*i+1]) # Combine logical cores
                    if useage > 100:
                        useage = 100
                    self.cpu_usage_history[i].append(useage / 100.0)
                self.history_times.append(time.time())
                if len(self.cpu_usage_history[0]) > self.max_history_size:
                    for i in range(self.cpu_count):
                        self.cpu_usage_history[i] = self.cpu_usage_history[i][-self.max_history_size:]
                    self.history_times = self.history_times[-self.max_history_size:]
                if len(self.cpu_usage_history[0]) == self.max_history_size:
                    cpu_percentages = [sum(core_history) / self.max_history_size for core_history in self.cpu_usage_history]
                    self.output_queue.put(cpu_percentages)
            except Exception as e:
                print(f"Error in CPUMonitorThread: {e}")
            time.sleep(self.update_interval)

class MemoryMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 5, update_interval = 1.0):
        super().__init__()
        self.daemon = True
        self.memory_usage_history = []
        self.history_times = []
        self.max_history_size = int(round(hysterisis_time / update_interval))
        self.update_interval = update_interval
        self.output_queue = output_queue

    def run(self):
        while True:
            try:
                if not self.output_queue.full():
                    memory_usage = psutil.virtual_memory().percent / 100.0
                else:
                    print("Memory monitor queue is full")
                self.memory_usage_history.append(memory_usage)
                self.history_times.append(time.time())
                if len(self.memory_usage_history) > self.max_history_size:
                    self.memory_usage_history = self.memory_usage_history[-self.max_history_size:]
                    self.history_times = self.history_times[-self.max_history_size:]
                if len(self.memory_usage_history) == self.max_history_size:
                    avg_memory_usage = sum(self.memory_usage_history) / self.max_history_size
                    self.output_queue.put(avg_memory_usage)
            except Exception as e:
                print(f"Error in MemoryMonitorThread: {e}")
            time.sleep(self.update_interval)

class BatteryMonitorThread(threading.Thread):
    def __init__(self, output_queue, update_interval = 1):
        super().__init__()
        self.daemon = True
        self.update_interval = update_interval
        self.output_queue = output_queue

    def run(self):
        while True:
            try:
                if not self.output_queue.full():
                    battery = psutil.sensors_battery()
                    if battery is not None:
                        battery_percentage = battery.percent / 100.0
                        battery_plugged = battery.power_plugged
                        self.output_queue.put((battery_percentage, battery_plugged))
                else:
                    print("Battery monitor queue is full")
            except Exception as e:
                print(f"Error in BatteryMonitorThread: {e}")
            time.sleep(self.update_interval)