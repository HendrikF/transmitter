#!/usr/bin/python3
from time import sleep
from transmitter.general import Server

from exampleClient import AMessage

if __name__ == '__main__':
    
    server = Server()
    
    server.messageFactory.add(AMessage)
    
    def onMessage(msg, peer):
        print(msg, peer)
        if msg == 'AMessage':
            print('It is an AMessage! :)')
    server.onMessage.attach(onMessage)
    
    def onConnect(peer):
        print('Connected:', peer)
    server.onConnect.attach(onConnect)
    
    def onDisconnect(peer):
        print('Disconnected', peer)
    server.onDisconnect.attach(onDisconnect)
    
    def onTimeout(peer):
        print('Timed out', peer)
    server.onTimeout.attach(onTimeout)
    
    server.bind(('', 55555))
    server.start()
    
    while True:
        sleep(0.01)
        server.update()
