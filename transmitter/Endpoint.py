import socket
from threading import Thread
import queue
from collections import deque
from time import time
from transmitter.Event import Event
from transmitter.Message import Message, MessageFactory, TransportMessage
from transmitter.ByteBuffer import ByteBuffer
from transmitter.Measurement import Measurement
from transmitter.PingSampler import PingSampler
from transmitter.BitField import BitField

import logging
logger = logging.getLogger(__name__)

PROTOCOL = 1

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
        self.accepting = False
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.peers = {}
        # we have one temporary peer at client to send connect request
        self._lastPeerID = -1 if self.isClient else 0
        self.addr = None
        
        self._receivingThread = None
        
        self.state = self.DISCONNECTED
        self.mtu = 1400
        self.timeout = 10
        self.pingInterval = 2
        
        self.pendingDisconnect = False
        
        self.bytesIn    = Measurement()
        self.bytesOut   = Measurement()
        self.packetsIn  = Measurement()
        self.packetsOut = Measurement()
        self.messagesIn = Measurement()
        self.messagesOut= Measurement()
        
        self.messageFactory = MessageFactory()
        # NO TransportMessages
        self.receivedMessages = queue.Queue()
        self.onMessage = Event()
        self.onConnect = Event()
        self.onDisconnect = Event()
        self.onTimeout = Event()
        
        self.lastOutgoingSequenceNumber = 0
        
        # TransportMessages
        self.bufferedMessages = deque()
    
    @property
    def active(self):
        return self.state in [self.LISTENING, self.CONNECTED]
    
    @property
    def latency(self):
        # Makes only sense at client!
        try:
            # SHOULD be the server connection
            return self.peers[self._lastPeerID].latency
        except KeyError:
            return 0
    
    def bind(self, addr):
        self.addr = addr
        self._socket.bind(addr)
        self.accepting = True
        self.state = self.LISTENING
    
    def connect(self, addr):
        self.addr = addr
        self._socket.bind(('', 0))
        self.accepting = True
        self.state = self.CONNECTING
        # we need a peer to send data, but we remove it as soon as possible
        peer = self._newPeer(self.addr)
        peer.send(self.messageFactory.getByName('TConnectRequest')(protocol=PROTOCOL), reliable=True)
        peer.pendingDisconnect = True
    
    def start(self):
        if not self.addr:
            raise RuntimeError('The socket must be bound to an address - Call bind or connect')
        self._receivingThread = Thread(target=self._receive)
        self._receivingThread.daemon = True
        self._receivingThread.start()
    
    def disconnect(self):
        self.accepting = False
        for peer in list(self.peers.values())[:]:
            peer.disconnect()
        self.pendingDisconnect = True
    
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
            msg, peer = next
            if msg.msgID >= 0:
                self.onMessage(msg, peer)
            else:
                if msg == 'TConnect':
                    self.onConnect(peer)
                elif msg == 'TDisconnect':
                    self.onDisconnect(peer)
                elif msg == 'TTimeout':
                    self.onTimeout(peer)
        self.removeDeadPeers()
        self.updatePeers()
        self.sendOutgoingMessages()
        if self.pendingDisconnect and not self.peers:
            self._socket.close()
    
    def send(self, msg, exclude=[], **flags):
        tmsg = TransportMessage(msg, self.nextOutgoingSequenceNumber, **flags)
        if self.active:
            for _id, peer in list(self.peers.items())[:]:
                if _id not in exclude:
                    peer._send(tmsg)
        else:
            # we buffer the reliable messages until we have a connection
            if tmsg.reliable:
                self.bufferedMessages.append(tmsg)
    
    def _send(self, data, addr):
        self.bytesOut += self._socket.sendto(data, addr)
        self.packetsOut += 1
    
    def _read(self):
        result = self._socket.recvfrom(self.mtu)
        # result -> (data, addr)
        self.bytesIn += len(result[0])
        self.packetsIn += 1
        return result
    
    def _putMessage(self, msg, peer):
        self.receivedMessages.put((msg, peer), False)
    
    def _newPeer(self, addr):
        peer = Peer(self, addr, self.nextPeerID)
        self.peers[peer.id] = peer
        return peer
    
    def sendOutgoingMessages(self):
        for peer in list(self.peers.values())[:]:
            for packet in peer.outgoingPackets:
                self._send(packet, peer.addr)
    
    def updatePeers(self):
        for peer in list(self.peers.values())[:]:
            peer.update()
    
    def _receive(self):
        while True:
            data, addr = self._read()
            peer = self.getPeerByAddr(addr)
            if not peer:
                if not self.accepting:
                    continue
                peer = self._newPeer(addr)
            self._processData(data, peer)
    
    def _processData(self, data, peer):
        byteBuffer = ByteBuffer(data)
        while len(byteBuffer):
            self.messagesIn += 1
            
            sequenceNumber = byteBuffer.readStruct('Q')[0]
            flags = BitField(byteBuffer.readStruct('B')[0])
            msgID = byteBuffer.readStruct('l')[0]
            msg = self.messageFactory.getByID(msgID)()
            msg._readFromByteBuffer(byteBuffer)
            tmsg = TransportMessage(msg, sequenceNumber)
            tmsg.flags = flags
            
            self._processMessage(tmsg, peer)
    
    def _processMessage(self, tmsg, peer):
        if peer.processIncommingMessage(tmsg) == self.MESSAGE_UNHANDLED:
            self._putMessage(tmsg.msg, peer)
    
    def removeDeadPeers(self):
        dead = []
        for _id, peer in self.peers.items():
            if peer.pendingDisconnect and not peer.outgoingMessages:
                dead.append(_id)
        for _id in dead:
            self.peers.pop(_id)
    
    def processConnectRequest(self, msg, peer):
        if self.isServer and self.state == self.LISTENING:
            logger.debug('Received ConnectRequest: %s %s', msg, peer)
            if msg.protocol == PROTOCOL:
                peer.send(self.messageFactory.getByName('TConnectRequestAccepted')(), reliable=True)
                logger.info('Accepting Request')
                self._putMessage(self.messageFactory.getByName('TConnect')(), peer)
            else:
                peer.send(self.messageFactory.getByName('TConnectRequestRejected')(), reliable=True)
                logger.info('Rejecting Request: msg: %s our: %s', msg.protocol, PROTOCOL)
                peer.pendingDisconnect = True
    
    def processConnectRequestAccepted(self, peer):
        if self.isClient and self.state == self.CONNECTING:
            logger.info('Server accepted connection')
            self.accepting = False
            try:
                self.peers[self._lastPeerID-1].outgoingMessages.clear()
            except KeyError:
                pass
            self.state = self.CONNECTED
            self._putMessage(self.messageFactory.getByName('TConnect')(), peer)
            # we have a connection, so we send the buffered messages
            for tmsg in self.bufferedMessages:
                peer._send(tmsg)
    
    def processConnectRequestRejected(self):
        if self.isClient and self.state == self.CONNECTING:
            logger.info('Server rejected connection')
            self.accepting = False
            try:
                self.peers[self._lastPeerID].pendingDisconnect = True
                self.peers[self._lastPeerID-1].outgoingMessages.clear()
            except KeyError:
                pass
            self.state = self.DISCONNECTED
            self._putMessage(self.messageFactory.getByName('TDisconnect')(), None)
    
    def _peerTimeout(self, peer):
        self._putMessage(self.messageFactory.getByName('TTimeout')(), peer)
    
    def _peerDisconnect(self, peer):
        self._putMessage(self.messageFactory.getByName('TDisconnect')(), peer)
    
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
    
    @property
    def nextOutgoingSequenceNumber(self):
        self.lastOutgoingSequenceNumber += 1
        return self.lastOutgoingSequenceNumber

class Peer(object):
    def __init__(self, endpoint, addr, _id):
        self.endpoint = endpoint
        self.addr = addr
        self.id = _id
        
        self.pendingDisconnect = False
        
        self.pingSampler = PingSampler(0.2)
        self.lastPingTime = 0
        self.lastPingNumber = 0
        
        # TransportMessages
        self.outgoingMessages = deque()
        
        self.lastIncommingSequenceNumber = 0
        self.recentIncommingSequenceNumbers = []
        
        self.lastReceiveTime = 0
    
    @property
    def latency(self):
        return self.pingSampler.average
    
    def send(self, msg, **flags):
        tmsg = TransportMessage(msg, self.endpoint.nextOutgoingSequenceNumber, **flags)
        self._send(tmsg)
    
    def _send(self, tmsg):
        if not self.pendingDisconnect:
            self.outgoingMessages.append(tmsg)
    
    def disconnect(self):
        self.send(self.endpoint.messageFactory.getByName('TDisconnect')())
        self.pendingDisconnect = True
        self.endpoint._peerDisconnect(self)
    
    def processIncommingMessage(self, tmsg):
        self.lastReceiveTime = time()
        
        if tmsg.reliable:
            # message requires acknowledgement
            logger.debug('Acking: %s', tmsg)
            self.send(self.endpoint.messageFactory.getByName(
                'TAcknowledgement')(sequenceNumber=tmsg.sequenceNumber))
        
        self.recentIncommingSequenceNumbers = \
            self.recentIncommingSequenceNumbers[-1000:]
        if tmsg.sequenceNumber in self.recentIncommingSequenceNumbers:
            # message received twice, discard it
            logger.info('Message received twice - discarding it: %s', tmsg)
            return self.endpoint.MESSAGE_HANDLED
        self.recentIncommingSequenceNumbers.append(tmsg.sequenceNumber)
        
        if tmsg.ordered and tmsg.sequenceNumber < self.lastIncommingSequenceNumber:
            # newer message was received, discard it
            # nevertheless, the acknownledgement might be sent
            logger.info('Discarding late ordered message: %s', tmsg)
            return self.endpoint.MESSAGE_HANDLED
        
        msg = tmsg.msg
        
        if msg == 'TAcknowledgement':
            if self._processAcknowledgement(msg.sequenceNumber):
                logger.debug('Received correct Ack: %s', tmsg)
            else:
                logger.debug('Could not process Ack: %s', tmsg)
        
        elif msg == 'TConnectRequest':
            self.endpoint.processConnectRequest(msg, self)
        elif msg == 'TConnectRequestAccepted':
            self.endpoint.processConnectRequestAccepted(self)
        elif msg == 'TConnectRequestRejected':
            self.endpoint.processConnectRequestRejected()
        
        elif msg == 'TPing':
            self.send(self.endpoint.messageFactory.getByName('TPong')(pingNumber=msg.pingNumber))
        elif msg == 'TPong':
            if msg.pingNumber == self.lastPingNumber:
                self.pingSampler += time() - self.lastPingTime
        
        elif msg == 'TDisconnect':
            self.pendingDisconnect = True
            self.outgoingMessages.clear()
            self.endpoint._peerDisconnect(self)
        
        else:
            return self.endpoint.MESSAGE_UNHANDLED
        
        return self.endpoint.MESSAGE_HANDLED
    
    def _processAcknowledgement(self, sequenceNumber):
        for tmsg in self.outgoingMessages:
            if tmsg.sequenceNumber == sequenceNumber:
                self.outgoingMessages.remove(tmsg)
                return True
        return False
    
    @property
    def outgoingPackets(self):
        buf = b''
        size = 0
        sentMessages = []
        t = time()
        for tmsg in self.outgoingMessages:
            if tmsg.lastSendAttempt + self.pingSampler.average >= t:
                # msg cant be sent, we are waiting for acknowledgement
                continue
            tmsg.lastSendAttempt = t
            l = len(tmsg.bytes)
            if l > self.endpoint.mtu:
                logger.error('Message bigger than MTU! -- discarding')
                sentMessages.append(tmsg)
                continue
            elif size + l >= self.endpoint.mtu:
                # message doesnt fit in packet
                # send the packet
                yield buf
                # make new buffer
                buf = b''
                size = 0
            # append message to buffer
            buf += tmsg.bytes
            size += l
            self.endpoint.messagesOut += 1
            if not tmsg.reliable:
                sentMessages.append(tmsg)
        
        if buf:
            yield buf
        
        for tmsg in sentMessages:
            self.outgoingMessages.remove(tmsg)
    
    def update(self):
        if self.pendingDisconnect:
            return
        t = time()
        if t > self.lastPingTime + self.endpoint.pingInterval:
            self.lastPingNumber += 1
            self.lastPingTime = t
            self.send(self.endpoint.messageFactory.getByName('TPing')(pingNumber=self.lastPingNumber))
        
        if self.lastReceiveTime == 0:
            self.lastReceiveTime = t
        elif t > self.lastReceiveTime + self.endpoint.timeout:
            self.pendingDisconnect = True
            # reliable messages will not get acknowledged, so remove all
            self.outgoingMessages.clear()
            self.endpoint._peerTimeout(self)
    
    def __repr__(self):
        return '<Peer id={} addr={}>'.format(self.id, self.addr)
