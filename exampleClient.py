#!/usr/bin/python3
from time import sleep
from transmitter.general import Client
from transmitter.Message import Message

class AMessage(Message):
    msgID = 1
    msgReliable = True
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
    
    def onMessage(msg, peer):
        print(msg, peer)
        if msg == 'AMessage':
            print('It is an AMessage! :)')
    client.onMessage.attach(onMessage)
    
    def onConnect(peer):
        print('Connected:', peer)
    client.onConnect.attach(onConnect)
    
    def onDisconnect(peer):
        print('Disconnected', peer)
    client.onDisconnect.attach(onDisconnect)
    
    client.connect(('127.0.0.1', 55555))
    client.start()
    
    msg = client.messageFactory.getByName('AMessage')()
    
    client.send(msg)
    
    while True:
        sleep(0.01)
        client.update()
