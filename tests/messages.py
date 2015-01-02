import unittest

from transmitter.messages import Message
from transmitter.bytebuffer import ByteBuffer
from transmitter.error import InvalidMessageID

class TestMessage(Message):
    msgID = 1
    msgData = {
        'a': ('str', 'Test String abc'),
        'b': ('bytes', b'Binary Data'),
        'c': ('int', 1234567890),
        'd': ('float', 3.14159265358979323846)
    }

data = b'\x00\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0fTest String abcI\x96\x02\xd2\x00\x00\x00\x0bBinary Data@\t!\xfbTD-\x18\x00\x00\x00\x00\xff\xff\xff\xff\x00'

class Messages(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_Bytes(self):
        msg = TestMessage()
        self.assertEqual(msg.getBytes(), data)
    
    def test_Parsing(self):
        normalMsg = TestMessage()
        bbuffer = ByteBuffer()
        bbuffer.append(data)
        msg = TestMessage()
        msg.a = ''
        msg.b = ''
        msg.c = ''
        msg.d = ''
        bbuffer.read(len(Message.boundaries[0]))
        bbuffer.readStruct('l')
        msg.readFromByteBuffer(bbuffer)
        bbuffer.read(len(Message.boundaries[1]))
        self.assertEqual(len(bbuffer), 0)
        self.assertEqual(msg.msgID, normalMsg.msgID)
        self.assertEqual(msg.msgData, normalMsg.msgData)
    
    def test_0NotAllowedAsId(self):
        class OtherMessage(TestMessage):
            msgID = 0
        self.assertRaises(InvalidMessageID, OtherMessage)
