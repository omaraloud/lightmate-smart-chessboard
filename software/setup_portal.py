from http.server import BaseHTTPRequestHandler, HTTPServer


SETUP_URL = "http://10.42.0.1:8000"


def portal_response(path):
    body = (
        "<!doctype html><html><head><title>ChessBoard setup</title></head>"
        f'<body><h1>ChessBoard setup</h1><p><a href="{SETUP_URL}">Open setup</a></p></body></html>'
    )
    return 302, {"Location": SETUP_URL, "Content-Type": "text/html; charset=utf-8"}, body


class PortalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send()

    def do_HEAD(self):
        self._send(include_body=False)

    def _send(self, include_body=True):
        status, headers, body = portal_response(self.path)
        encoded = body.encode("utf-8")
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if include_body:
            self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


def main():
    HTTPServer(("0.0.0.0", 80), PortalHandler).serve_forever()


if __name__ == "__main__":
    main()
