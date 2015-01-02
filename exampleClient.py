#!/usr/bin/python3
from transmitter.general import Client
from transmitter.messages import Message

class AMessage(Message):
    msgID = 1
    msgData = {
        'str': ('str', 'This is a string'),
        'bytes': ('bytes', b'this could be a binary file'),
        'int': ('int', 78),
        'float': ('float', 9.76)
    }

if __name__ == '__main__':
    
    client = Client()
    
    client.messageFactory.add(AMessage)
    
    client.connect('localhost', 55555)
    client.start()
    
    msg = client.messageFactory.getByName('AMessage')()
    
    client.send(msg)
    
    client.stop()
