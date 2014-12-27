from threading import Thread
import socket
from .event import Event

class NetworkEndpoint(object):
    
    isServer = False
    isClient = False
    
    def __init__(self):
        self.accepting = False
        self.thread = None
        self.onMessage = Event()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.peers = []
        self.host = ''
        self.port = None
    
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
            peer.close()
        self.socket.close()
    
    def update(self):
        pass
    
    def send(self, data):
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
    
    def _dataReceived(self, data, peer):
        print(peer, data)
    
    def _peerDisconnected(self, peer):
        self.peers.remove(peer)
        print('disconnected', peer)
    
    def __repr__(self):
        x = ''
        if self.isServer:
            x += ' (server mode, {} peers{})'.format(len(self.peers), ', accepting' if self.accepting else '')
        if self.isClient:
            x += ' (client mode)'
        x += ' ({}, {})'.format(self.host, self.port)
        return '<NetworkEndpoint{}>'.format(x)

class NetworkPeer(object):
    def __init__(self, endpoint, sock, addr=None):
        self.endpoint = endpoint
        self.socket = sock
        self.addr = addr
        self.thread = None
        self.active = False
    
    def start(self):
        self.thread = Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()
        self.active = True
    
    def send(self, data):
        if self.active:
            return self.socket.send(data)
    
    def close(self):
        self.active = False
        self.endpoint._peerDisconnected(self)
        self.socket.close()
    
    def _listen(self):
        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            self.endpoint._dataReceived(data, self)
        self.close()
    
    def __repr__(self):
        return '<NetworkPeer {}{}>'.format(self.addr, ' active' if self.active else '')
