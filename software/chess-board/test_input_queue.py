import unittest

from chessboard_app.input_queue import InputQueue


class InputQueueTest(unittest.TestCase):
    def test_push_and_drain_commands(self):
        queue = InputQueue()

        queue.push("up")
        queue.push("select")

        self.assertEqual(queue.drain(), ["up", "select"])
        self.assertEqual(queue.drain(), [])

    def test_rejects_unknown_commands(self):
        queue = InputQueue()

        with self.assertRaises(ValueError):
            queue.push("bad")


if __name__ == "__main__":
    unittest.main()
