from __future__ import annotations

import io


def _escape_wifi_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")


def setup_wifi_payload(ssid: str, password: str) -> str:
    return f"WIFI:T:WPA;S:{_escape_wifi_value(ssid)};P:{_escape_wifi_value(password)};;"


def setup_wifi_qr_svg(ssid: str, password: str) -> str:
    return setup_url_qr_svg(setup_wifi_payload(ssid, password))


def setup_url_qr_svg(url: str) -> str:
    import qrcode
    import qrcode.image.svg

    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    output = io.BytesIO()
    image.save(output)
    return output.getvalue().decode("utf-8")
