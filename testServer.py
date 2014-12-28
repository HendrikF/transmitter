#!/usr/bin/python3
from time import sleep
from transmitter.general import Server

from testClient import AMessage

if __name__ == '__main__':
    
    server = Server()
    
    server.messageFactory.add(AMessage)
    
    def onMessage(msg, peer):
        print(msg, peer)
    server.onMessage.attach(onMessage)
    
    server.bind('', 55555)
    server.start()
    
    while True:
        sleep(0.01)
        server.update()
