import unittest
from unittest.mock import patch

from chessboard_app.sensors import UnavailableSensorReader
from run_server import build_hardware_sensor_reader


class RunServerTest(unittest.TestCase):
    def test_hardware_sensor_reader_falls_back_when_i2c_expander_is_missing(self):
        with patch("run_server.McpSensorReader.create", side_effect=ValueError("No I2C device at address: 0x20")), \
             patch("run_server.logging.exception"):
            reader = build_hardware_sensor_reader()

        self.assertIsInstance(reader, UnavailableSensorReader)
        self.assertIn("0x20", reader.error)


if __name__ == "__main__":
    unittest.main()
