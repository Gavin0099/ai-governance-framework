import unittest

from src.calc import add, sub


class TestCalc(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        self.assertEqual(add(-4, 1), -3)

    def test_sub(self):
        self.assertEqual(sub(10, 4), 6)


if __name__ == "__main__":
    unittest.main()
