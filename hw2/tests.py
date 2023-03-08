# This code has no "unit" functionality of note, but whatever

from unittest import TestCase, main

from model import Clock


class TestClock(TestCase):
    def test_init(self):
        clock = Clock()
        self.assertEqual(clock.ctr, 0)

    def test_increment(self):
        clock = Clock()
        clock.increment()
        self.assertEqual(clock.ctr, 1)

    def test_msgRecUpdate(self):
        clock = Clock()
        clock.msgRecUpdate(5)
        self.assertEqual(clock.ctr, 6)

        clock.msgRecUpdate(3)
        self.assertEqual(clock.ctr, 7)

        clock.msgRecUpdate(8)
        self.assertEqual(clock.ctr, 9)


if __name__ == "__main__":
    main()
