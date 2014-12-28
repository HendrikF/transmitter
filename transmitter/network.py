from threading import Thread
import socket
from collections import deque
from .event import Event
from .messages import Message, MessageFactory
from .error import *
from .bytebuffer import ByteBuffer

class NetworkEndpoint(object):
    """A NetworkEndpoint is a flexible interface for a Server and Client."""
    
    isServer = False
    isClient = False
    
    def __init__(self, async=False):
        self.async = async
        self.accepting = False
        self.thread = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.peers = []
        self.host = ''
        self.port = None
        self.messageFactory = MessageFactory()
        self.receivedMessages = deque()
        self.onMessage = Event()
        self.onConnect = Event()
        self.onDisconnect = Event()
    
    def bind(self, host, port):
        if self.isServer:
            self.host = host
            self.port = port
            self.socket.bind((host, port))
            self.socket.listen(0)
    
    def connect(self, host, port):
        if self.isClient:
            self.host = host
            self.port = port
            self.socket.connect((host, port))
    
    def start(self):
        if self.isServer:
            self.thread = Thread(target=self._accept)
            self.thread.daemon = True
            self.thread.start()
        elif self.isClient:
            self._newPeer(self.socket)
    
    def stop(self):
        self.accepting = False
        for peer in self.peers:
            peer.stop()
        self.socket.close()
    
    def update(self):
        """Call this method regularly in sync mode"""
        while len(self.receivedMessages) > 0:
            msg, peer = self.receivedMessages.popleft()
            self.onMessage(msg, peer)
    
    def send(self, message):
        data = message.getBytes()
        for peer in self.peers:
            peer.send(data)
    
    def _accept(self):
        self.accepting = True
        while self.accepting:
            conn, addr = self.socket.accept()
            self._newPeer(conn, addr)
    
    def _newPeer(self, sock, addr=None):
        peer = NetworkPeer(self, sock, addr)
        peer.start()
        self.peers.append(peer)
        self.onConnect(peer)
    
    def msgReceived(self, msg, peer):
        if msg.msgID > 0:
            if self.async:
                self.onMessage(msg, peer)
            else:
                self.receivedMessages.append((msg, peer))
    
    def _peerDisconnected(self, peer):
        self.peers.remove(peer)
        self.onDisconnect(peer)
    
    def __repr__(self):
        x = ''
        if self.isServer:
            x += ' (server mode, {} peers{})'.format(len(self.peers), ', accepting' if self.accepting else '')
        if self.isClient:
            x += ' (client mode)'
        x += ' ({}, {})'.format(self.host, self.port)
        return '<NetworkEndpoint{}>'.format(x)

class NetworkPeer(object):
    """A NetworkPeer provides the ability to write and listen on sockets.
    The Server has one NetworkPeer for each connected Client.
    A Client has only one NetworkPeer for the Server."""
    def __init__(self, endpoint, sock, addr=None):
        self.endpoint = endpoint
        self.socket = sock
        self.addr = addr
        self.thread = None
        self.active = False
        self.buffer = ByteBuffer()
    
    def start(self):
        self.thread = Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()
        self.active = True
    
    def send(self, data):
        if self.active:
            return self.socket.send(data)
    
    def stop(self):
        self.active = False
        self.endpoint._peerDisconnected(self)
        self.socket.close()
    
    def _listen(self):
        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            self.buffer.append(data)
            self._parseMessages()
        self.stop()
    
    def _parseMessages(self):
        while self.buffer.contains(Message.boundaries[0]) and self.buffer.contains(Message.boundaries[1]):
            self.buffer.read(len(Message.boundaries[0]))
            msgID = self.buffer.readStruct('l')[0]
            msg = self.endpoint.messageFactory.getByID(msgID)()
            msg.readFromByteBuffer(self.buffer)
            self.buffer.read(len(Message.boundaries[1]))
            self.endpoint.msgReceived(msg, self)
    
    def __repr__(self):
        return '<NetworkPeer {}{}>'.format(self.addr, ' active' if self.active else '')
