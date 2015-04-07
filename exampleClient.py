#!/usr/bin/python3
from time import sleep, time
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

lastPrint = time()
def _print(*x):
    global lastPrint
    if lastPrint + 0.5 < time():
        lastPrint = time()
        print('\r', end='')
        print(*x, end='')

if __name__ == '__main__':
    
    client = Client()
    
    client.messageFactory.add(AMessage)
    
    def onMessage(msg, peer):
        print(msg, peer)
    client.onMessage.attach(onMessage)
    
    def onConnect(peer):
        print('Connected:', peer)
    client.onConnect.attach(onConnect)
    
    def onDisconnect(peer):
        print('Disconnected', peer)
    client.onDisconnect.attach(onDisconnect)
    
    def onTimeout(peer):
        print('Timed out', peer)
    client.onTimeout.attach(onTimeout)
    
    client.connect(('localhost', 55555))
    client.start()
    
    msg = client.messageFactory.getByName('AMessage')()
    
    client.send(msg)
    
    try:
        while True:
            sleep(0.01)
            client.update()
            _print('Latency:', client.latency)
    except KeyboardInterrupt:
        client.disconnect()
        client.update()
        raise
