import unittest

from transmitter.general import Server, Client
from transmitter.messages import *

from time import sleep, time
def wait(func):
    end = time() + 2
    while not func():
        if time() >= end:
            return False
        sleep(0.01)
    return True

class TestMessage(Message):
    msgID = 1
    msgData = {
        'a': ('str', 'Test String abc'),
        'b': ('bytes', b'Binary Data'),
        'c': ('int', 1234567890),
        'd': ('float', 3.14159265358979323846)
    }

class Tcp(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.server.messageFactory.add(TestMessage)
        self.server.bind('', 55555)
        self.server.start()
        self.client = Client()
        self.client.messageFactory.add(TestMessage)
        self.client.connect('localhost', 55555)
        self.client.start()
    
    def tearDown(self):
        self.client.stop()
        self.client = None
        self.server.stop()
        self.server = None
    
    def test_MessageTransmission(self):
        origMsg = TestMessage()
        def handler(msg, peer):
            self.assertIsInstance(msg, TestMessage)
            self.assertEqual(msg.msgData, origMsg.msgData)
            self.assertEqual(msg.msgID, origMsg.msgID)
            self.ok = True
        self.server.onMessage.attach(handler)
        self.ok = False
        self.client.send(origMsg)
        wait(lambda: self.server.update() or self.ok)
        self.assertTrue(self.ok, 'There was no message received!')
