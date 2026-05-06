import argparse
import logging

from chessboard_app.leds import DisabledLedController, DotStarLedController
from chessboard_app.sensors import McpSensorReader, StaticSensorReader, UnavailableSensorReader
from chessboard_app.server import create_app


def build_hardware_sensor_reader():
    try:
        return McpSensorReader.create()
    except Exception as exc:
        logging.exception("Sensor hardware unavailable; starting with disabled sensors")
        return UnavailableSensorReader(str(exc))


def build_hardware_led_controller():
    try:
        return DotStarLedController.create()
    except Exception:
        logging.exception("LED hardware unavailable; starting with disabled LEDs")
        return DisabledLedController()


def build_app(use_hardware=False):
    sensor_reader = build_hardware_sensor_reader() if use_hardware else StaticSensorReader()
    led_controller = build_hardware_led_controller() if use_hardware else DisabledLedController()
    return create_app(sensor_reader=sensor_reader, led_controller=led_controller)


app = build_app(use_hardware=False)

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the local chessboard web app.")
    parser.add_argument("--hardware", action="store_true", help="Read real MCP23017 sensors.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = build_app(use_hardware=args.hardware)
    uvicorn.run(app, host=args.host, port=args.port)
