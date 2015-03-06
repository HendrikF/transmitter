""""
bitfield manipulation
(store bools in bytes)

by Sébastien Keim
http://code.activestate.com/recipes/113799/
PSF License

Removed support for slices
Added conversion to bool

Usage:
>> b = BitField()
>> b[0] = 1
>> b[1] = 1
>> int(b)
3
>> b
<BitField 0b11>
>> bin(int(b))
'0b11'
"""

class BitField(object):
    def __init__(self, value=0):
        self._d = value
    
    def __getitem__(self, index):
        return True if (self._d >> index) & 1 else False
    
    def __setitem__(self, index, value):
        value = (value & 1) << index
        mask = 1 << index
        self._d = (self._d & ~mask) | value
    
    def __int__(self):
        return self._d
    
    def __index__(self):
        return self._d
    
    def __repr__(self):
        return '<BitField {}>'.format(bin(self._d))
