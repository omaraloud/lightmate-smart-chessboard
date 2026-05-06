from __future__ import annotations

import subprocess
import time
from typing import Callable


CommandRunner = Callable[[list[str]], str]


def default_runner(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


class WifiManager:
    setup_ssid = "ChessBoard-Setup"
    setup_password = "chessboard"
    setup_url = "http://10.42.0.1:8000"
    wifi_interface = "wlan0"
    hotspot_connection_names = ("ChessBoard-Setup", "Hotspot")

    def __init__(self, runner: CommandRunner = default_runner, status_cache_seconds: float = 3):
        self.runner = runner
        self.status_cache_seconds = status_cache_seconds
        self._status_cache: tuple[float, dict[str, object]] | None = None

    def _status_payload(
        self,
        *,
        available: bool,
        connected: bool,
        ssid: str | None,
        interface: str | None,
        ip: str | None,
        mode: str,
        signal: int | None = None,
    ) -> dict[str, object]:
        return {
            "available": available,
            "connected": connected,
            "ssid": ssid,
            "interface": interface,
            "ip": ip,
            "mode": mode,
            "signal": signal,
            "setupSsid": self.setup_ssid,
            "setupPassword": self.setup_password,
            "setupUrl": self.setup_url,
        }

    def status(self) -> dict[str, object]:
        cached = self._cached_status()
        if cached is not None:
            return cached

        status = self._read_status()
        self._status_cache = (time.monotonic(), status)
        return status

    def _cached_status(self) -> dict[str, object] | None:
        if self.status_cache_seconds <= 0 or self._status_cache is None:
            return None
        cached_at, status = self._status_cache
        if time.monotonic() - cached_at <= self.status_cache_seconds:
            return dict(status)
        return None

    def _invalidate_status_cache(self) -> None:
        self._status_cache = None

    def _read_status(self) -> dict[str, object]:
        wifi_status = self._wifi_status_from_device_status()
        if wifi_status and wifi_status["mode"] == "client":
            return wifi_status

        wired_status = self._wired_status()
        if wired_status is not None:
            return wired_status

        if wifi_status is not None:
            return wifi_status

        try:
            output = self.runner([
                "nmcli",
                "-t",
                "-f",
                "active,ssid,device,state,ip4.address",
                "dev",
                "wifi",
            ])
        except Exception:
            return self._status_payload(
                available=False,
                connected=False,
                ssid=None,
                interface=None,
                ip=None,
                mode="unavailable",
            )

        wifi_status = None
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) >= 5 and parts[0] == "yes":
                wifi_status = self._status_payload(
                    available=True,
                    connected=parts[3] == "connected",
                    ssid=parts[1] or None,
                    interface=parts[2] or None,
                    ip=parts[4].split("/")[0] if parts[4] else None,
                    mode="setup" if parts[1] == self.setup_ssid else "client",
                )
                break
            if len(parts) >= 4 and parts[2] == "connected":
                wifi_status = self._status_payload(
                    available=True,
                    connected=True,
                    ssid=parts[0] or None,
                    interface=parts[1] or None,
                    ip=parts[3].split("/")[0] if parts[3] else None,
                    mode="setup" if parts[0] == self.setup_ssid else "client",
                )
                break

        if wifi_status is not None:
            return wifi_status

        return self._status_payload(
            available=True,
            connected=False,
            ssid=None,
            interface=None,
            ip=None,
            mode="disconnected",
        )

    def _wifi_status_from_device_status(self) -> dict[str, object] | None:
        try:
            output = self.runner([
                "nmcli",
                "-t",
                "-f",
                "device,type,state,connection",
                "dev",
                "status",
            ])
        except Exception:
            return None

        saw_wifi = False
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) < 4 or parts[1] != "wifi":
                continue
            saw_wifi = True
            device = parts[0] or None
            connection = parts[3] or None
            if parts[2] == "connected":
                return self._status_payload(
                    available=True,
                    connected=True,
                    ssid=connection,
                    interface=device,
                    ip=self._device_ip(device),
                    mode="setup" if connection == self.setup_ssid else "client",
                    signal=self._connected_wifi_signal(connection),
                )

        if saw_wifi:
            return self._status_payload(
                available=True,
                connected=False,
                ssid=None,
                interface=self.wifi_interface,
                ip=None,
                mode="disconnected",
            )
        return None

    def _wired_status(self) -> dict[str, object] | None:
        try:
            output = self.runner([
                "nmcli",
                "-t",
                "-f",
                "device,type,state,connection",
                "dev",
                "status",
            ])
        except Exception:
            return None

        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[1] == "ethernet" and parts[2] == "connected":
                device = parts[0] or None
                return self._status_payload(
                    available=True,
                    connected=True,
                    ssid=parts[3] or None,
                    interface=device,
                    ip=self._device_ip(device),
                    mode="wired",
                )
        return None

    def _connected_wifi_signal(self, ssid: str | None) -> int | None:
        if not ssid:
            return None
        try:
            output = self.runner([
                "nmcli",
                "-t",
                "-f",
                "in-use,ssid,signal",
                "dev",
                "wifi",
                "list",
                "ifname",
                self.wifi_interface,
            ])
        except Exception:
            return None
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] == "*" and parts[1] == ssid:
                try:
                    return int(parts[2])
                except ValueError:
                    return None
        return None

    def _device_ip(self, device: str | None) -> str | None:
        if not device:
            return None
        try:
            output = self.runner(["nmcli", "-t", "-f", "ip4.address", "dev", "show", device])
        except Exception:
            return None
        for line in output.splitlines():
            value = line.split(":", 1)[-1]
            if value:
                return value.split("/")[0]
        return None

    def scan(self) -> list[dict[str, object]]:
        self._invalidate_status_cache()
        self.enable_wifi()
        self.stop_hotspot()
        self.rescan()
        try:
            output = self.runner([
                "nmcli",
                "-t",
                "-f",
                "ssid,signal,security",
                "dev",
                "wifi",
                "list",
                "ifname",
                self.wifi_interface,
                "--rescan",
                "yes",
            ])
        except Exception:
            output = ""
        networks = self._parse_nmcli_networks(output)
        if networks:
            return networks
        return self._scan_with_iw()

    def _parse_nmcli_networks(self, output: str) -> list[dict[str, object]]:
        networks: list[dict[str, object]] = []
        seen = set()
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) < 3 or not parts[0] or parts[0] in seen:
                continue
            seen.add(parts[0])
            networks.append({
                "ssid": parts[0],
                "signal": int(parts[1] or 0),
                "security": parts[2],
            })
        return networks

    def _scan_with_iw(self) -> list[dict[str, object]]:
        try:
            output = self.runner(["iw", "dev", self.wifi_interface, "scan"])
        except Exception:
            return []

        networks = []
        seen = set()
        current: dict[str, object] | None = None
        privacy = False
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("BSS "):
                if current and current.get("ssid") and current["ssid"] not in seen:
                    current["security"] = "WPA/WPA2" if privacy else ""
                    networks.append(current)
                    seen.add(current["ssid"])
                current = {"ssid": None, "signal": 0, "security": ""}
                privacy = False
            elif current is not None and stripped.startswith("SSID:"):
                current["ssid"] = stripped.split("SSID:", 1)[1].strip()
            elif current is not None and stripped.startswith("signal:"):
                value = stripped.split("signal:", 1)[1].strip().split()[0]
                current["signal"] = _dbm_to_percent(float(value))
            elif current is not None and "Privacy" in stripped:
                privacy = True

        if current and current.get("ssid") and current["ssid"] not in seen:
            current["security"] = "WPA/WPA2" if privacy else ""
            networks.append(current)
        return networks

    def stop_hotspot(self) -> None:
        self._invalidate_status_cache()
        for connection_name in self.hotspot_connection_names:
            try:
                self.runner(["nmcli", "connection", "down", connection_name])
            except Exception:
                pass
            self._disable_hotspot_autoconnect(connection_name)

    def _disable_hotspot_autoconnect(self, connection_name: str) -> None:
        try:
            self.runner([
                "nmcli",
                "connection",
                "modify",
                connection_name,
                "connection.autoconnect",
                "no",
                "connection.autoconnect-priority",
                "-999",
            ])
        except Exception:
            pass

    def enable_wifi(self) -> None:
        self._invalidate_status_cache()
        try:
            self.runner(["nmcli", "radio", "wifi", "on"])
        except Exception:
            pass
        try:
            self.runner(["rfkill", "unblock", "wifi"])
        except Exception:
            pass

    def rescan(self) -> None:
        self._invalidate_status_cache()
        try:
            self.runner(["nmcli", "dev", "wifi", "rescan", "ifname", self.wifi_interface])
        except Exception:
            pass

    def saved_wifi_connections(self) -> list[str]:
        try:
            output = self.runner([
                "nmcli",
                "-t",
                "-f",
                "name,type,autoconnect",
                "connection",
                "show",
            ])
        except Exception:
            return []

        connections: list[str] = []
        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) < 3:
                continue
            name, connection_type, autoconnect = parts[:3]
            if name in self.hotspot_connection_names:
                continue
            if connection_type != "802-11-wireless":
                continue
            if autoconnect != "yes":
                continue
            connections.append(name)
        return connections

    def reconnect_saved_wifi(
        self,
        wait_seconds: float = 20,
        poll_interval: float = 2,
    ) -> dict[str, object]:
        self._invalidate_status_cache()
        self.enable_wifi()
        self.stop_hotspot()
        self.rescan()
        try:
            self.runner(["nmcli", "device", "connect", self.wifi_interface])
        except Exception:
            pass
        for connection_name in self.saved_wifi_connections():
            try:
                self.runner([
                    "nmcli",
                    "connection",
                    "up",
                    connection_name,
                    "ifname",
                    self.wifi_interface,
                ])
            except Exception:
                pass

        deadline = time.monotonic() + wait_seconds
        last_status = self.status()
        while time.monotonic() < deadline:
            if last_status["connected"] and last_status["mode"] in {"client", "wired"}:
                return last_status
            time.sleep(poll_interval)
            last_status = self.status()
        return last_status

    def connect(self, ssid: str, password: str) -> None:
        self._invalidate_status_cache()
        self.enable_wifi()
        self.stop_hotspot()
        command = [
            "nmcli",
            "dev",
            "wifi",
            "connect",
            ssid,
        ]
        if password:
            command.extend(["password", password])
        command.extend([
            "ifname",
            self.wifi_interface,
        ])
        self.runner(command)

    def start_hotspot(self, ifname: str = "wlan0") -> None:
        self._invalidate_status_cache()
        self.runner([
            "nmcli",
            "dev",
            "wifi",
            "hotspot",
            "ifname",
            ifname,
            "con-name",
            self.setup_ssid,
            "ssid",
            self.setup_ssid,
            "password",
            self.setup_password,
        ])
        self._disable_hotspot_autoconnect(self.setup_ssid)


def _dbm_to_percent(dbm: float) -> int:
    if dbm <= -90:
        return 0
    if dbm >= -50:
        return 100
    return int(round(100 * (dbm + 90) / 40))
