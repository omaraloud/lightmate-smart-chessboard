import unittest
from unittest.mock import patch

from chessboard_app.wifi import WifiManager


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class WifiTest(unittest.TestCase):
    def test_status_parses_connected_network(self):
        runner = FakeRunner([
            "wlan0:wifi:connected:HomeWifi\n",
            "IP4.ADDRESS[1]:192.168.1.50/24\n",
            "*:HomeWifi:76\n",
        ])
        wifi = WifiManager(runner=runner)

        status = wifi.status()

        self.assertEqual(status["available"], True)
        self.assertEqual(status["connected"], True)
        self.assertEqual(status["ssid"], "HomeWifi")
        self.assertEqual(status["interface"], "wlan0")
        self.assertEqual(status["ip"], "192.168.1.50")
        self.assertEqual(status["mode"], "client")
        self.assertEqual(status["signal"], 76)

    def test_scan_parses_networks(self):
        runner = FakeRunner(["", "", "", "", "", "", "", "Home:80:WPA2\nCafe:40:WPA1 WPA2\n"])
        wifi = WifiManager(runner=runner)

        self.assertEqual(wifi.scan(), [
            {"ssid": "Home", "signal": 80, "security": "WPA2"},
            {"ssid": "Cafe", "signal": 40, "security": "WPA1 WPA2"},
        ])
        self.assertEqual(runner.calls[0], [
            "nmcli",
            "radio",
            "wifi",
            "on",
        ])
        self.assertEqual(runner.calls[1], ["rfkill", "unblock", "wifi"])
        self.assertEqual(runner.calls[2], [
            "nmcli",
            "connection",
            "down",
            "ChessBoard-Setup",
        ])
        self.assertEqual(runner.calls[6], [
            "nmcli",
            "dev",
            "wifi",
            "rescan",
            "ifname",
            "wlan0",
        ])
        self.assertEqual(runner.calls[7], [
            "nmcli",
            "-t",
            "-f",
            "ssid,signal,security",
            "dev",
            "wifi",
            "list",
            "ifname",
            "wlan0",
            "--rescan",
            "yes",
        ])

    def test_scan_falls_back_to_iw_when_nmcli_finds_nothing(self):
        runner = FakeRunner([
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "BSS aa:bb:cc(on wlan0)\n\tSSID: Home\n\tsignal: -45.00 dBm\n\tcapability: ESS Privacy\nBSS dd:ee:ff(on wlan0)\n\tSSID: Cafe\n\tsignal: -70.00 dBm\n\tcapability: ESS\n",
        ])
        wifi = WifiManager(runner=runner)

        self.assertEqual(wifi.scan(), [
            {"ssid": "Home", "signal": 100, "security": "WPA/WPA2"},
            {"ssid": "Cafe", "signal": 50, "security": ""},
        ])
        self.assertEqual(runner.calls[-1], ["iw", "dev", "wlan0", "scan"])

    def test_status_uses_wired_connection_as_network_ready(self):
        runner = FakeRunner([
            "wlan0:wifi:disconnected:\n",
            "eth0:ethernet:connected:Wired connection 1\nwlan0:wifi:disconnected:\n",
            "192.168.1.20/24\n",
        ])
        wifi = WifiManager(runner=runner)

        status = wifi.status()

        self.assertEqual(status["connected"], True)
        self.assertEqual(status["mode"], "wired")
        self.assertEqual(status["interface"], "eth0")
        self.assertEqual(status["ssid"], "Wired connection 1")
        self.assertEqual(status["ip"], "192.168.1.20")

    def test_wired_connection_overrides_setup_hotspot(self):
        runner = FakeRunner([
            "wlan0:wifi:connected:ChessBoard-Setup\n",
            "10.42.0.1/24\n",
            "*:ChessBoard-Setup:88\n",
            "eth0:ethernet:connected:Wired connection 1\nwlan0:wifi:connected:ChessBoard-Setup\n",
            "192.168.1.20/24\n",
        ])
        wifi = WifiManager(runner=runner)

        status = wifi.status()

        self.assertEqual(status["connected"], True)
        self.assertEqual(status["mode"], "wired")
        self.assertEqual(status["interface"], "eth0")

    def test_connect_uses_nmcli(self):
        runner = FakeRunner(["", "", "", "", "", "", ""])
        wifi = WifiManager(runner=runner)

        wifi.connect("Home", "password")

        self.assertEqual(runner.calls[0], ["nmcli", "radio", "wifi", "on"])
        self.assertEqual(runner.calls[1], ["rfkill", "unblock", "wifi"])
        self.assertEqual(runner.calls[2], ["nmcli", "connection", "down", "ChessBoard-Setup"])
        self.assertEqual(runner.calls[4], ["nmcli", "connection", "down", "Hotspot"])
        self.assertEqual(runner.calls[6], ["nmcli", "dev", "wifi", "connect", "Home", "password", "password", "ifname", "wlan0"])

    def test_connect_open_network_omits_password_argument(self):
        runner = FakeRunner(["", "", "", "", "", "", ""])
        wifi = WifiManager(runner=runner)

        wifi.connect("Guest", "")

        self.assertEqual(runner.calls[6], ["nmcli", "dev", "wifi", "connect", "Guest", "ifname", "wlan0"])

    def test_start_hotspot_uses_named_non_autoconnecting_nmcli_hotspot(self):
        runner = FakeRunner(["", "", "", ""])
        wifi = WifiManager(runner=runner)

        wifi.start_hotspot()

        self.assertEqual(runner.calls[0], [
            "nmcli",
            "dev",
            "wifi",
            "hotspot",
            "ifname",
            "wlan0",
            "con-name",
            "ChessBoard-Setup",
            "ssid",
            "ChessBoard-Setup",
            "password",
            "chessboard",
        ])
        self.assertEqual(runner.calls[1], [
            "nmcli",
            "connection",
            "modify",
            "ChessBoard-Setup",
            "connection.autoconnect",
            "no",
            "connection.autoconnect-priority",
            "-999",
        ])

    def test_stop_hotspot_disables_both_possible_hotspot_profiles(self):
        runner = FakeRunner(["", "", "", ""])
        wifi = WifiManager(runner=runner)

        wifi.stop_hotspot()

        self.assertEqual(runner.calls, [
            ["nmcli", "connection", "down", "ChessBoard-Setup"],
            ["nmcli", "connection", "modify", "ChessBoard-Setup", "connection.autoconnect", "no", "connection.autoconnect-priority", "-999"],
            ["nmcli", "connection", "down", "Hotspot"],
            ["nmcli", "connection", "modify", "Hotspot", "connection.autoconnect", "no", "connection.autoconnect-priority", "-999"],
        ])

    def test_setup_status_marks_setup_network(self):
        runner = FakeRunner([
            "wlan0:wifi:connected:ChessBoard-Setup\n",
            "10.42.0.1/24\n",
            "*:ChessBoard-Setup:88\n",
            "eth0:ethernet:unavailable:\nwlan0:wifi:connected:ChessBoard-Setup\n",
        ])
        wifi = WifiManager(runner=runner)

        status = wifi.status()

        self.assertEqual(status["mode"], "setup")
        self.assertEqual(status["setupUrl"], "http://10.42.0.1:8000")

    def test_saved_wifi_connections_excludes_setup_hotspot_profiles(self):
        runner = FakeRunner([
            "Home:802-11-wireless:yes\nChessBoard-Setup:802-11-wireless:no\nHotspot:802-11-wireless:no\nWired connection 1:802-3-ethernet:yes\nCafe:802-11-wireless:yes\n"
        ])
        wifi = WifiManager(runner=runner)

        self.assertEqual(wifi.saved_wifi_connections(), ["Home", "Cafe"])

    def test_reconnect_saved_wifi_stops_hotspot_and_tries_saved_profiles_before_hotspot(self):
        runner = FakeRunner([
            "",  # nmcli radio wifi on
            "",  # rfkill unblock wifi
            "",  # hotspot down
            "",  # hotspot autoconnect off
            "",  # Hotspot down
            "",  # Hotspot autoconnect off
            "",  # rescan
            "",  # device connect
            "Home:802-11-wireless:yes\nChessBoard-Setup:802-11-wireless:no\n",
            "",  # connection up Home
            "wlan0:wifi:connected:Home\n",
            "192.168.1.44/24\n",
            "*:Home:88\n",
        ])
        wifi = WifiManager(runner=runner)

        with patch("chessboard_app.wifi.time.sleep"):
            status = wifi.reconnect_saved_wifi(wait_seconds=5, poll_interval=1)

        self.assertEqual(status["mode"], "client")
        self.assertEqual(status["ssid"], "Home")
        self.assertNotIn(["nmcli", "dev", "wifi", "hotspot", "ifname", "wlan0", "con-name", "ChessBoard-Setup", "ssid", "ChessBoard-Setup", "password", "chessboard"], runner.calls)
        self.assertIn(["nmcli", "connection", "down", "ChessBoard-Setup"], runner.calls)
        self.assertIn(["nmcli", "connection", "up", "Home", "ifname", "wlan0"], runner.calls)

    def test_reconnect_saved_wifi_returns_disconnected_when_profiles_do_not_connect(self):
        runner = FakeRunner([
            "", "", "", "", "", "", "", "",
            "Home:802-11-wireless:yes\n",
            Exception("not visible"),
            "wlan0:wifi:disconnected:\n",
            "eth0:ethernet:unavailable:\nwlan0:wifi:disconnected:\n",
            "wlan0:wifi:disconnected:\n",
            "eth0:ethernet:unavailable:\nwlan0:wifi:disconnected:\n",
        ])
        wifi = WifiManager(runner=runner)

        with patch("chessboard_app.wifi.time.sleep"):
            status = wifi.reconnect_saved_wifi(wait_seconds=0, poll_interval=1)

        self.assertEqual(status["connected"], False)
        self.assertEqual(status["mode"], "disconnected")


if __name__ == "__main__":
    unittest.main()
