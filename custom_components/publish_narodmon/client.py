"""TCP client for narodmon.ru."""

from __future__ import annotations

import socket

from .const import NARODMON_HOST, NARODMON_PORT, SOCKET_TIMEOUT


def send_payload(payload: str) -> str:
    """Send payload over TCP and return the server reply."""
    with socket.create_connection(
        (NARODMON_HOST, NARODMON_PORT), timeout=SOCKET_TIMEOUT
    ) as sock:
        sock.sendall(payload.encode("utf-8"))
        return sock.recv(1024).decode("utf-8", errors="ignore")
