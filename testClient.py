#!/usr/bin/python3
from transmitter.general import Client
from transmitter.messages import Message

class AMessage(Message):
    msgID = 1
    msgData = {
        'name': ('str', 'Hallo')
    }

client = Client()

client.messageFactory.add(AMessage)

client.connect('localhost', 55555)
client.start()

msg = client.messageFactory.getByName('AMessage')()

client.send(msg)

#client.peers[0].thread.join()
client.stop()
