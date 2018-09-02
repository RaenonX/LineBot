import numpy

class array_1d_statistics(object):
    def __init__(self, arr):
        self._arr = arr

        self._min_index, self._min_value = min(enumerate(self._arr), key=lambda p: p[1])
        self._max_index, self._max_value = max(enumerate(self._arr), key=lambda p: p[1])

        self._count = len(self._arr)

        if self._count % 2 == 0:
            self._median = self._arr[self._count / 2]
        else:
            self._median = (self._arr[self._count / 2] + self._arr[self._count / 2 + 1]) / 2.0

        self._sum = sum(self._arr)
        self._avg = self._sum / float(self._count)
        self._std = numpy.std(numpy.array(self._arr))

    @property
    def array(self):
        return self._arr
    
    @property
    def min_index(self):
        return self._min_index
    
    @property
    def min_value(self):
        return self._min_value
    
    @property
    def max_index(self):
        return self._max_index
    
    @property
    def max_value(self):
        return self._max_value

    @property
    def count(self):
        return self._count

    @property
    def median(self):
        return self._median

    @property
    def sum(self):
        return self._sum

    @property
    def avg(self):
        return self._avg

    @property
    def std(self):
        return self._std