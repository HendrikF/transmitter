#!/usr/bin/python3
from time import sleep
from transmitter.general import Client
from transmitter.Message import Message

class AMessage(Message):
    msgID = 1
    msgData = {
        'str': ('str', 'This is a string'),
        'bytes': ('bytes', b'this could be a binary file'),
        'int': ('int', 78),
        'float': ('float', 9.76),
        'boolean': ('bool', True)
    }

if __name__ == '__main__':
    
    client = Client()
    
    client.messageFactory.add(AMessage)
    
    client.connect(('localhost', 55555))
    client.start()
    
    msg = client.messageFactory.getByName('AMessage')()
    
    client.send(msg)
    
    client.update()
    
    client.disconnect()
