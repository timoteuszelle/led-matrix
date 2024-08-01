import time
import psutil
import threading
import time
import queue


class DiskMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 5, update_interval = 0.25):
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
            disk_io = psutil.disk_io_counters()
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

            time.sleep(self.update_interval)

class NetworkMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 5, update_interval = 0.25):
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
            net_io = psutil.net_io_counters()
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

            time.sleep(self.update_interval)

class CPUMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 5, update_interval = 0.25):
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
            cpu_usage = psutil.cpu_percent(percpu=True)
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
            time.sleep(self.update_interval)

class MemoryMonitorThread(threading.Thread):
    def __init__(self, output_queue, hysterisis_time = 5, update_interval = 0.25):
        super().__init__()
        self.daemon = True
        self.memory_usage_history = []
        self.history_times = []
        self.max_history_size = int(round(hysterisis_time / update_interval))
        self.update_interval = update_interval
        self.output_queue = output_queue

    def run(self):
        while True:
            memory_usage = psutil.virtual_memory().percent / 100.0
            self.memory_usage_history.append(memory_usage)
            self.history_times.append(time.time())
            if len(self.memory_usage_history) > self.max_history_size:
                self.memory_usage_history = self.memory_usage_history[-self.max_history_size:]
                self.history_times = self.history_times[-self.max_history_size:]
            if len(self.memory_usage_history) == self.max_history_size:
                avg_memory_usage = sum(self.memory_usage_history) / self.max_history_size
                self.output_queue.put(avg_memory_usage)
            time.sleep(self.update_interval)


if __name__ == "__main__":
    disk_queue = queue.Queue()
    network_queue = queue.Queue()
    cpu_queue = queue.Queue()
    memory_queue = queue.Queue()

    disk_monitor = DiskMonitorThread(disk_queue)
    network_monitor = NetworkMonitorThread(network_queue)
    cpu_monitor = CPUMonitorThread(cpu_queue)
    memory_monitor = MemoryMonitorThread(memory_queue)

    disk_monitor.start()
    network_monitor.start()
    cpu_monitor.start()
    memory_monitor.start()

    while True:
        if not disk_queue.empty():
            read_percent, write_percent = disk_queue.get()
            print(f"Disk Usage: Read {read_percent:.2%}, Write {write_percent:.2%}")
        
        if not network_queue.empty():
            sent_percent, recv_percent = network_queue.get()
            print(f"Network Usage: Sent {sent_percent:.2%}, Received {recv_percent:.2%}")

        if not cpu_queue.empty():
            cpu_percentages = cpu_queue.get()
            print(f"CPU Usage: {cpu_percentages}")

        if not memory_queue.empty():
            memory_usage = memory_queue.get()
            print(f"Memory Usage: {memory_usage:.2%}")

        time.sleep(0.5)