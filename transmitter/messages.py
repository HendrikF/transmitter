import struct
from collections import OrderedDict
from .error import *

class Message(object):
    """A Message is a packet of data which can be sent over the network.
    Every Message has a unique msgID and usually some fields of data of a special type and a default value.
    Custom Messages have a msgID greater than 0."""
    msgID = 0
    msgData = {
        #'name': ('type', '(default)value')
    }
    
    def __init__(self):
        # make ordered dict to have keys in a defined order, dict would be 'random'
        msgData = OrderedDict(sorted(self.msgData.items()))
        if self.msgID == 0:
            raise InvalidMessageID
    
    def __getattr__(self, name):
        try:
            return self.msgData[name][1]
        except KeyError:
            raise InvalidMessageField
    
    def __setattr__(self, name, value):
        try:
            t, v = self.msgData[name]
            self.msgData[name] = (t, value)
        except KeyError:
            raise InvalidMessageField
    
    def getBytes(self):
        format = '!i'
        values = [self.msgID]
        for k, v in self.msgData.items():
            t = v[0]
            v = v[1]
            if t == 'int':      format += 'i'
            elif t == 'float':  format += 'f'
            elif t in ('str', 'bytes'):
                if t == 'str':
                    v = v.encode()
                format += 'i'
                values.append(len(v))
                format += str(len(v)) + 's'
            else:
                raise InvalidFieldFormat
            values.append(v)
        return struct.pack(format, *values)

class MessageFactory(object):
    """A class that holds all the Message classes which can be received from the network"""
    def __init__(self):
        self.messagesByID = {}
        self.messagesByName = {}
    
    def add(self, *classes):
        for clas in classes:
            if not issubclass(clas, Message):
                raise TypeError
            if (clas.msgID in self.messagesByID) ^ (clas.__name__ in self.messagesByName):
                raise DuplicateMessageID
            self.messagesByID[clas.msgID] = clas
            self.messagesByName[clas.__name__] = clas
    
    def getByID(self, _id):
        try:
            return self.messagesByID[_id]
        except KeyError:
            raise MessageNotFound
    
    def getByName(self, name):
        try:
            return self.messagesByName[name]
        except KeyError:
            raise MessageNotFound
    
    def is_a(self, message, name):
        return isinstance(message, self.getByName(name))