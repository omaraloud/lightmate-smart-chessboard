import unittest

from setup_portal import portal_response


class SetupPortalTest(unittest.TestCase):
    def test_captive_probe_redirects_to_setup_page(self):
        status, headers, body = portal_response("/hotspot-detect.html")

        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "http://10.42.0.1:8000")
        self.assertIn("ChessBoard setup", body)

    def test_any_path_redirects_to_setup_page(self):
        status, headers, body = portal_response("/anything")

        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "http://10.42.0.1:8000")
        self.assertIn("ChessBoard setup", body)


if __name__ == "__main__":
    unittest.main()
