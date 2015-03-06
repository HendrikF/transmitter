import socket
from threading import Thread
import queue
from collections import deque
from transmitter.Event import Event
from transmitter.Message import Message, MessageFactory
from transmitter.ByteBuffer import ByteBuffer
from transmitter.Measurement import Measurement

import logging
logger = logging.getLogger(__name__)

class Endpoint(object):
    """A NetworkEndpoint is a flexible interface for a Server and Client."""
    DISCONNECTED = 0
    LISTENING = 1
    CONNECTING = 2
    CONNECTED = 3
    
    MESSAGE_HANDLED = True
    MESSAGE_UNHANDLED = False
    
    isServer = False
    isClient = False
    
    def __init__(self):
        self.accepting = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.peers = {}
        self._lastPeerID = 0
        self.addr = None
        
        self.receivingThread = None
        
        self.state = self.DISCONNECTED
        self.mtu = 1400
        
        self.bytesIn = Measurement()
        self.bytesOut = Measurement()
        self.packetsIn = Measurement()
        self.packetsOut = Measurement()
        self.messagesIn = Measurement()
        self.messagesOut = Measurement()
        
        self.messageFactory = MessageFactory()
        self.receivedMessages = queue.Queue()
        self.onMessage = Event()
        self.onConnect = Event()
        self.onDisconnect = Event()
    
    @property
    def active(self):
        return self.state in [self.LISTENING, self.CONNECTING, self.CONNECTED]
    
    def bind(self, addr):
        if self.isServer:
            self.addr = addr
            self.socket.bind(addr)
            self.state = self.LISTENING
    
    def connect(self, addr):
        if self.isClient:
            self.addr = addr
            self.socket.bind(('', 0))
            self.state = self.CONNECTING
    
    def start(self):
        if not self.addr:
            raise RuntimeError('The socket must be bound to an address - Call bind or connect')
        self.receivingThread = Thread(target=self._receive)
        self.receivingThread.daemon = True
        self.receivingThread.start()
    
    def disconnect(self):
        self.accepting = False
        for peer in list(self.peers.values())[:]:
            peer.disconnect(pop=False)
        self.peers = {}
        self.socket.close()
    
    @property
    def _nextMessage(self):
        try:
            return self.receivedMessages.get(False)
        except queue.Empty:
            return None
    
    def update(self):
        """Call this method regularly"""
        while True:
            next = self._nextMessage
            if not next:
                break
            else:
                msg, peer = next
                if msg.msgID >= 0:
                    self.onMessage(msg, peer)
                else:
                    if msg == 'TConnectMessage':
                        self.onConnect(peer)
                    elif msg == 'TDisconnectMessage':
                        self.onDisconnect(peer)
        self.sendOutgoingMessages()
    
    def send(self, message, exclude=[]):
        if self.isClient:
            self._newPeer(self.addr)
        for _id, peer in list(self.peers.items())[:]:
            if _id not in exclude:
                peer.send(message)
    
    def _send(self, data, addr):
        self.bytesOut += self.socket.sendto(data, addr)
        self.packetsOut += 1
    
    def _read(self):
        result = self.socket.recvfrom(self.mtu)
        # result -> (data, addr)
        self.bytesIn += len(result[0])
        self.packetsIn += 1
        return result
    
    def _putMessage(self, msg, peer):
        self.receivedMessages.put((msg, peer), False)
    
    def _newPeer(self, addr):
        peer = Peer(self, addr, self.nextPeerID)
        self.peers[peer.id] = peer
        msg = self.messageFactory.getByName('TConnectMessage')()
        self._putMessage(msg, peer)
        return peer
    
    def _peerDisconnected(self, peer, pop=True):
        if pop:
            self.peers.pop(peer.id)
        msg = self.messageFactory.getByName('TDisconnectMessage')()
        self._putMessage(msg, peer)
    
    def sendOutgoingMessages(self):
        for peer in list(self.peers.values())[:]:
            for packet in peer.outgoingPackets:
                self._send(packet, peer.addr)
    
    def _receive(self):
        while True:
            data, addr = self._read()
            peer = self.getPeerByAddr(addr)
            if not peer:
                peer = self._newPeer(addr)
            self.processData(data, peer)
    
    def processData(self, data, peer):
        byteBuffer = ByteBuffer(data)
        while len(byteBuffer):
            msg = self.messageFactory.readMessage(byteBuffer)
            self.messagesIn += 1
            self.processMessage(msg, peer)
    
    def processMessage(self, msg, peer):
        if peer.processIncommingMessage(msg) == self.MESSAGE_UNHANDLED:
            self._putMessage(msg, peer)
    
    def getPeerByAddr(self, addr):
        for peer in self.peers.values():
            if peer.addr == addr:
                return peer
        return None
    
    def __repr__(self):
        x = ''
        if self.isServer:
            x += ' (server mode, {} peers{})'.format(len(self.peers), ', accepting' if self.accepting else '')
        if self.isClient:
            x += ' (client mode)'
        x += ' ({}, {})'.format(self.host, self.port)
        return '<Endpoint{}>'.format(x)
    
    @property
    def nextPeerID(self):
        self._lastPeerID += 1
        return self._lastPeerID

class Peer(object):
    def __init__(self, endpoint, addr, _id):
        self.endpoint = endpoint
        self.addr = addr
        self.id = _id
        self.active = True
        
        self.outgoingMessages = deque()
    
    def send(self, message):
        if self.active:
            self.outgoingMessages.append(message)
    
    def disconnect(self, pop=True):
        self.active = False
        self.endpoint._peerDisconnected(self, pop)
    
    @property
    def outgoingPackets(self):
        buf = b''
        size = 0
        sentMessages = []
        for msg in self.outgoingMessages:
            l = len(msg)
            if l > self.endpoint.mtu:
                logger.error('Message bigger than MTU! -- discarding')
            elif size + l >= self.endpoint.mtu:
                # send the packet
                yield buf
                # 'append' message to new buffer
                buf = msg._bytes
                size = l
            else:
                # append message to buffer
                buf += msg._bytes
                size += l
            sentMessages.append(msg)
        
        if buf:
            yield buf
        
        for msg in sentMessages:
            self.outgoingMessages.remove(msg)
            self.endpoint.messagesOut += 1
    
    def processIncommingMessage(self, msg):
        return self.endpoint.MESSAGE_UNHANDLED
    
    def __repr__(self):
        return '<Peer id={} addr={} act={}>'.format(self.id, self.addr, self.active)
