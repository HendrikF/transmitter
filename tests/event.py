import unittest

from transmitter.event import Event

class Events(unittest.TestCase):
    def setUp(self):
        self.e = Event()
        self.count = 0
    
    def tearDown(self):
        self.e = None
    
    def test_MultipleHandlers(self):
        def handler(x):
            self.count += x
        self.e.attach(handler)
        self.e.attach(handler)
        self.e(1)
        self.assertEqual(self.count, 2, 'Handler didnt fire twice')
    
    def test_SingleHandler(self):
        def handler(x):
            self.count += x
        self.e.attach(handler)
        self.e(1)
        self.assertEqual(self.count, 1, 'Handler didnt fire')
    
    def test_InvalidHandler(self):
        self.e.attach(42)
        self.assertRaises(TypeError, self.e)
