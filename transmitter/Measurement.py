from time import time

class Measurement(object):
    def __init__(self, interval=1, intervalCount=6):
        if interval <= 0:
            raise ValueError('interval must be a positive value')
        if intervalCount <= 0:
            raise ValueError('intervalCount must be a positive integer')
        self.interval = interval
        self.intervalCount = int(intervalCount)
        # each entry equals the amount of data added during this interval
        self.samples = []
        # data during current interval
        self.currentInterval = 0
        self.totalSampleCount = 0
        self.totalData = 0
        self.beginning = 0
    
    def __len__(self):
        return len(self.samples)
    
    def __iadd__(self, value):
        if not self.running:
            # we start the time, when 1st sample is added
            self.beginning = time()
        self.update()
        self.currentInterval += value
        self.totalData += value
        return self
    
    def update(self):
        if not self.running:
            return
        # time since last sample
        dt = time() - self.beginning - self.totalSampleCount * self.interval
        # number of FULL intervals, which passed
        n = int(dt // self.interval)
        if n > 0:
            # the numbers of zeros we add depends on the number of intervals, which passed since last sample
            self.samples.extend([self.currentInterval]+([0]*(n-1)))
            self.currentInterval = 0
            self.samples = self.samples[-self.intervalCount:]
            self.totalSampleCount += n
    
    @property
    def average(self):
        try:
            return self.totalData / (time() - self.beginning)
        except ZeroDivisionError:
            return self.totalData
    
    @property
    def current(self):
        self.update()
        try:
            return sum(self.samples) / (len(self.samples) * self.interval)
        except ZeroDivisionError:
            return 0
    
    @property
    def total(self):
        return self.totalData
    
    @property
    def running(self):
        return self.beginning != 0
    
    def __repr__(self):
        return '<Measurement interval={} count={}>'.format(self.interval, self.intervalCount)
