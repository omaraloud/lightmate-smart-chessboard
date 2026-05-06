import unittest

from chessboard_app.setup_qr import setup_url_qr_svg, setup_wifi_payload, setup_wifi_qr_svg


class SetupQrTest(unittest.TestCase):
    def test_setup_wifi_payload_uses_wifi_qr_format(self):
        self.assertEqual(
            setup_wifi_payload("ChessBoard-Setup", "chessboard"),
            "WIFI:T:WPA;S:ChessBoard-Setup;P:chessboard;;",
        )

    def test_setup_wifi_qr_svg_returns_svg(self):
        svg = setup_wifi_qr_svg("ChessBoard-Setup", "chessboard")

        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)

    def test_setup_url_qr_svg_returns_svg(self):
        svg = setup_url_qr_svg("https://lichess.org/account/oauth/token/create?scopes[]=board:play")

        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)


if __name__ == "__main__":
    unittest.main()
