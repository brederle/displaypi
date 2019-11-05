import unittest
import time

from displaypi.wifidisplay.p2p import P2pWifi


class TestConnect(unittest.TestCase):

    def setUp(self):
        pass



    def tearDown(self):
        pass



    def test_setup(self):
        self.p2pwifi = P2pWifi()
        self.p2pwifi.open("test")
        while True:
            time.sleep(2)
        self.addCleanup(lambda: self.p2pwifi.close())

if __name__ == '__main__':
    unittest.main()