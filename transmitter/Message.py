import struct

import logging
logger = logging.getLogger(__name__)

class Message(object):
    """A Message is a packet of data which can be sent over the network.
    Every Message has a unique msgID and usually some fields of data of a special type and a default value.
    Custom Messages have a msgID >= 0."""
    msgID = 0
    msgData = {
        #'name': ('type', '(default)value')
    }
    # cache bytes
    _bytes = b''
    
    _factory = None
    
    def __init__(self, **data):
        for key, value in data.items():
            self.__setattr__(key, value)
    
    def __getattr__(self, name):
        try:
            return self.msgData[name][1]
        except KeyError:
            return super().__getattr__(name)
    
    def __setattr__(self, name, value):
        try:
            t, v = self.msgData[name]
        except KeyError:
            super().__setattr__(name, value)
        else:
            # empty cache when changing value
            self._bytes = b''
            self.msgData[name] = (t, value)
    
    def __len__(self):
        return len(self.bytes)
    
    def _items(self):
        """Provides iterator access to msgData in sorted key order"""
        # data have to be accessed sorted, because dict's key order is undefined !!
        # But sender and receiver have to know the order of the keys
        for key in sorted(list(self.msgData.keys())):
            yield key, self.msgData[key]
    
    @property
    def bytes(self):
        if not self._bytes:
            self._bytes = self._getBytes()
        return self._bytes
    
    def _getBytes(self):
        format = '!l'
        values = [self.msgID]
        for k, v in self._items():
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
            elif t == 'bool':   format += '?'
            else:
                logger.error('Cant encode message key of unknown type', t)
                raise TypeError("type '{}' unknown".format(t))
            values.append(v)
        return struct.pack(format, *values)
    
    def _readFromByteBuffer(self, byteBuffer):
        for k, v in self._items():
            t = v[0]
            if t == 'int':      self.__setattr__(k, byteBuffer.readStruct('l')[0])
            elif t == 'float':  self.__setattr__(k, byteBuffer.readStruct('d')[0])
            elif t in ('str', 'bytes'):
                length = byteBuffer.readStruct('l')[0]
                data = byteBuffer.readStruct(str(length) + 's')[0]
                if t == 'str':
                    data = data.decode()
                self.__setattr__(k, data)
            elif t == 'bool':   self.__setattr__(k, byteBuffer.readStruct('?')[0])
            else:
                logger.error('Cant decode message key of unknown type %s', t)
                raise TypeError("type '{}' unknown".format(t))
    
    def __eq__(self, name):
        try:
            return self._factory.isA(self, name)
        except AttributeError:
            return self.__class__.__name__ == name
    
    def __repr__(self):
        data = [(k, v[1]) for k, v in self._items()]
        return '<{} {}>'.format(self.__class__.__name__, data)

class MessageFactory(object):
    """A class that holds all the Message classes which can be received from the network"""
    def __init__(self):
        self.messagesByID = {}
        self.messagesByName = {}
        self.add(TConnectMessage, TDisconnectMessage)
    
    def add(self, *classes):
        for clas in classes:
            if not issubclass(clas, Message):
                logger.error('Message classes must subclass Message')
                raise TypeError('Classes must subclass Message')
            if (clas.msgID in self.messagesByID) ^ (clas.__name__ in self.messagesByName):
                logger.error('Message classes cant have the same id')
                raise ValueError('class {} or id {} already exists!'.format(clas.__name__, clas.msgID))
            # give the class the factory, so the message can perform .isA()
            clas._factory = self
            self.messagesByID[clas.msgID] = clas
            self.messagesByName[clas.__name__] = clas
            logger.info('Added message type to factory (%s, %s)', clas.__name__, clas.msgID)
    
    def getByID(self, _id):
        try:
            return self.messagesByID[_id]
        except KeyError:
            logger.error('Cant find message with id %s', _id)
            raise KeyError("Message id '{}' not found".format(_id))
    
    def getByName(self, name):
        try:
            return self.messagesByName[name]
        except KeyError:
            logger.error('Cant find message with name %s', name)
            raise KeyError("Message name '{}' not found".format(name))
    
    def isA(self, message, name):
        return isinstance(message, self.getByName(name))
    
    def readMessage(self, byteBuffer):
        msgID = byteBuffer.readStruct('l')[0]
        msg = self.getByID(msgID)()
        msg._readFromByteBuffer(byteBuffer)
        return msg

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
