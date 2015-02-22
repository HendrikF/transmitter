# Transmitter

Transmitter is a python library to send discrete packets of data over UDP.

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
    # the type can be one of int,float,str,bytes,bool
    msgData = {
        'name': ('str', 'default value'),
        'bytes': ('bytes', b''),
        'int': ('int', 0),
        'float': ('float', 0),
        'boolean': ('bool', True)
    }

if __name__ == '__main__':
    
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
        # update() calls the onMessage, onConnect, onDisconnect events on the server
        # so the events run on the same (main) thread
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
        'float': ('float', 9.76),
        'boolean': ('bool', True)
    }

if __name__ == '__main__':
    
    client = Client()
    
    client.messageFactory.add(AMessage)
    
    client.connect('localhost', 55555)
    client.start()
    
    # The following is equivalent to
    # msg = AMessage()
    msg = client.messageFactory.getByName('AMessage')()
    msg.bytes = b'All message data can be assigned that way'
    
    # This internally buffers the messages
    client.send(msg)
    # You have to call client.update() to send them
    
    # Call client.update() regularly to recieve Messages from the server
    client.update()
    
    client.stop()
```

## License

Transmitter is released under the 3-clause BSD license.

See `LICENSE` for details.
