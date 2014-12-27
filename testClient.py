#!/usr/bin/python3
from transmitter.general import Client

client = Client()
client.connect('localhost', 55555)
client.start()

client.send(b'Hello')

client.peers[0].thread.join()
