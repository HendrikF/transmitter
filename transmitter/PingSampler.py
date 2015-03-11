class PingSampler(object):
    def __init__(self, numSamples=5):
        if numSamples <= 0:
            raise ValueError('numSamples must be a positive integer')
        self.numSamples = int(numSamples)
        self.samples = []
    
    def __len__(self):
        return len(self.samples)
    
    def __iadd__(self, value):
        self.samples = (self.samples + [value])[-self.numSamples:]
        return self
    
    @property
    def average(self):
        try:
            return sum(self.samples) / len(self.samples)
        except ZeroDivisionError:
            return None
    
    def __repr__(self):
        return '<PingSampler num={}>'.format(self.numSamples)
