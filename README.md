# Transmitter

Transmitter is a python library to send discrete packets of data over TCP/IP.

It is intended to be extended to also support UDP in both unicast and multicast mode.

## Usage examples

Server:

```python
#!/usr/bin/python3
from time import sleep
from transmitter.general import Server
from transmitter.messages import Message

# Must also be known by the client
# Better import it from a shared module...
class AMessage(Message):
    # ID must be unique, because it identifies all the messages
    msgID = 1
    # here you define all the attributes of a message
    # the key should only contain characters
    # the type can be one of int,float,str,bytes
    msgData = {
        'name': ('str', 'default value'),
        'bytes': ('bytes', b''),
        'int': ('int', 0),
        'float': ('float', 0)
    }

if __name__ == '__main__':
    
    # initialize server in sync mode, so you have to call server.update() (see last lines)
    server = Server()
    
    # make message available to server
    server.messageFactory.add(AMessage)
    
    # attach an event handler
    # possible events are onConnect(peer), onMessage(msg, peer), onDisconnect(peer)
    def onMessage(msg, peer):
        print(msg, peer)
    server.onMessage.attach(onMessage)
    
    server.bind('', 55555)
    # start listening for incomming connections
    server.start()
    
    while True:
        sleep(0.01)
        # in sync mode, update() calls the onMessage event on the server
        # so the events run on the same thread
        # the on(Dis)Connect events are always called on the listening thread
        server.update()
```

Client:

```python
#!/usr/bin/python3
from transmitter.general import Client
from transmitter.messages import Message

# Must also be known by the server
class AMessage(Message):
    msgID = 1
    msgData = {
        'name': ('str', 'This is a string'),
        'bytes': ('bytes', b''),
        'int': ('int', 78),
        'float': ('float', 9.76)
    }

if __name__ == '__main__':
    
    client = Client()
    
    client.messageFactory.add(AMessage)
    
    client.connect('localhost', 55555)
    client.start()
    
    msg = client.messageFactory.getByName('AMessage')()
    msg.bytes = b'All message data can be assigned that way'
    
    client.send(msg)
    
    # Call client.update() regularly to recieve Messages from the server
    client.stop()
```

## License

Transmitter is released under the 3-clause BSD license.

See `LICENSE` for details.
