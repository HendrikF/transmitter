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
    
    boundaries = (
        b'\x00\xff\xff\xff\xff\x00\x00\x00\x00',
        b'\x00\x00\x00\x00\xff\xff\xff\xff\x00'
    )
    
    def __init__(self):
        # make ordered dict to have keys in a defined order, dict would be 'random'
        msgData = OrderedDict(sorted(self.msgData.items()))
        if self.msgID == 0:
            raise InvalidMessageID('msgID 0 is not allowed')
    
    def __getattr__(self, name):
        try:
            return self.msgData[name][1]
        except KeyError:
            raise InvalidMessageField("key '{}' not found".format(name))
    
    def __setattr__(self, name, value):
        try:
            t, v = self.msgData[name]
            self.msgData[name] = (t, value)
        except KeyError:
            raise InvalidMessageField("key '{}' not found".format(name))
    
    def getBytes(self):
        format = '!l'
        values = [self.msgID]
        for k, v in self.msgData.items():
            t = v[0]
            v = v[1]
            if t == 'int':      format += 'l'
            elif t == 'float':  format += 'd'
            elif t in ('str', 'bytes'):
                if t == 'str':
                    v = v.encode()
                format += 'l'
                values.append(len(v))
                format += str(len(v)) + 's'
            else:
                raise InvalidFieldFormat("type '{}' unknown".format(t))
            values.append(v)
        return  self.boundaries[0] + \
                struct.pack(format, *values) + \
                self.boundaries[1]
    
    def readFromByteBuffer(self, byteBuffer):
        for k, v in self.msgData.items():
            t = v[0]
            if t == 'int':      self.__setattr__(k, byteBuffer.readStruct('l')[0])
            elif t == 'float':  self.__setattr__(k, byteBuffer.readStruct('d')[0])
            elif t in ('str', 'bytes'):
                length = byteBuffer.readStruct('l')[0]
                data = byteBuffer.readStruct(str(length) + 's')[0]
                if t == 'str':
                    data = data.decode()
                self.__setattr__(k, data)
            else:
                raise InvalidFieldFormat("type '{}' unknown".format(t))
    
    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.msgData)

class MessageFactory(object):
    """A class that holds all the Message classes which can be received from the network"""
    def __init__(self):
        self.messagesByID = {}
        self.messagesByName = {}
        self.add(TConnectMessage, TDisconnectMessage)
    
    def add(self, *classes):
        for clas in classes:
            if not issubclass(clas, Message):
                raise TypeError('Classes must subclass Message')
            if (clas.msgID in self.messagesByID) ^ (clas.__name__ in self.messagesByName):
                raise DuplicateMessageID
            self.messagesByID[clas.msgID] = clas
            self.messagesByName[clas.__name__] = clas
    
    def getByID(self, _id):
        try:
            return self.messagesByID[_id]
        except KeyError:
            raise MessageNotFound("Message id '{}' not found".format(_id))
    
    def getByName(self, name):
        try:
            return self.messagesByName[name]
        except KeyError:
            raise MessageNotFound("Message name '{}' not found".format(name))
    
    def is_a(self, message, name):
        return isinstance(message, self.getByName(name))

# System messages
###################

class TSystemMessage(Message):
    """Not for sending over the network!
    These Messages are just inserted into the queue when special events happen"""
    def getBytes(self):
        return b''
    
    def readFromByteBuffer(self, byteBuffer):
        pass

class TConnectMessage(TSystemMessage):
    msgID = -1

class TDisconnectMessage(TSystemMessage):
    msgID = -2
