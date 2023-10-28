from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import overload

from .http import HTTPResponse, HTTPRequest


class PacketState(StrEnum):
    Receiving = 'receiving'
    Executing = 'executing'
    Executed = 'executed'
    Sent = 'sent'


@dataclass
class PacketStats:
    receiving: float | None = None
    executing: float | None = None
    executed: float | None = None
    sent: float | None = None

    def __str__(self) -> str:
        return (f"{f"{(self.sent - self.receiving) * 1000:.2f}ms" if self.sent is not None else 'N/A'} "
                f"({f"{(self.executed - self.executing) * 1000:.2f}ms" if self.executed is not None else 'N/A'})")


class IP:
    octets: tuple[int, int, int, int]

    @overload
    def __init__(self, octets: tuple[int, int, int, int]) -> None: ...
    @overload
    def __init__(self, int_: int) -> None: ...

    def __init__(self, *args):
        if isinstance(args[0], tuple):
            self.octets = args[0]
        elif isinstance(args[0], int):
            self.octets = tuple(args[0].to_bytes(4))

    def __str__(self) -> str:
        return '.'.join(map(str, self.octets))


@dataclass
class Requester:
    ip: IP
    port: int

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"


BUFFER_SIZE = 4096


@dataclass
class Packet:
    requester: Requester
    connection: socket.socket
    stats: PacketStats = field(default_factory=PacketStats)

    response_http: HTTPResponse | None = None

    _req_http: HTTPRequest | None = None
    _res_body: bytes | None = None
    _req_body: bytes | None = None

    @property
    def request_body(self) -> bytes:
        if self._req_body is None:
            buffer: list[bytes] = []

            while True:
                if data := self.connection.recv(BUFFER_SIZE):
                    buffer.append(data)

                if len(data) < BUFFER_SIZE:
                    break

            self._req_body = bytes([byte for bytes_ in buffer for byte in bytes_])

        return self._req_body

    @property
    def request_http(self) -> HTTPRequest | False:
        if self._req_http is None:
            try:
                self._req_http = HTTPRequest.from_bytes(self.request_body)
            except ValueError:
                self._req_http = False  # TODO set it to a more meaningful thing maybe

        return self._req_http

    @property
    def response_body(self) -> bytes | None:
        if self.response_http is None:
            return None

        if self._res_body is None:
            self._res_body = self.response_http.to_bytes()

        return self._res_body

    def mark(self, state: PacketState) -> None:
        if getattr(self.stats, state) is not None:
            raise RuntimeError("packet was already marked as receiving")

        setattr(self.stats, state, time.perf_counter())

        if state == PacketState.Sent:
            logging.info(f"{self} - {self.stats}")

    def __str__(self) -> str:
        return (f"{self.requester} - "
                f"{f"{self._req_http.method} {self._req_http.path}" if self._req_http is not None and self._req_http is not False else "N/A N/A"} - "
                f"{self.response_http.status if self.response_http is not None else "N/A"}")
