import time


class Scheduler(object):
    def __init__(self, terminal, time_to_run=None, day=0, hour=0, min=0, sec=0):
        self.terminal = terminal
        self.day = day
        self.hour = hour
        self.min = min
        self.sec = sec
        self.time_to_run = time_to_run
        self.total_time = max(0.1, self.sec + 60 * self.min + 60 * 60 * self.hour + 60 * 60 * 24 * self.day)

    def run(self):
        if self.time_to_run is None:
            while True:
                self.terminal.run()
                time.sleep(self.total_time)
        else:
            for _ in range(self.time_to_run):
                self.terminal.run()
                time.sleep(self.total_time)