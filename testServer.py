#!/usr/bin/python3
from transmitter.general import Server

server = Server()
server.bind('', 55555)
server.start()

server.thread.join()
