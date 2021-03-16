import unittest
from src.engine.skalpit import Skalpit

class TestSkalpit(unittest.TestCase):
    def setUp(self):
        self.skalpit = Skalpit(testmode = True)


if __name__ == '__main__':
    unittest.main()
