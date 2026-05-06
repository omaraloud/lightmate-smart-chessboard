import unittest

from calibrate_sensors import single_added_sensor


class CalibrateSensorsTest(unittest.TestCase):
    def test_single_added_sensor_returns_one_new_active_sensor(self):
        baseline = {("U66", 1)}
        active = {("U66", 1), ("U66", 2)}

        self.assertEqual(single_added_sensor(baseline, active), ("U66", 2))

    def test_single_added_sensor_ignores_removed_sensor(self):
        baseline = {("U66", 1)}
        active = set()

        self.assertIsNone(single_added_sensor(baseline, active))

    def test_single_added_sensor_rejects_multiple_added_sensors(self):
        baseline = set()
        active = {("U66", 1), ("U66", 2)}

        self.assertIsNone(single_added_sensor(baseline, active))


if __name__ == "__main__":
    unittest.main()
