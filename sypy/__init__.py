from __future__ import annotations

from dataclasses import dataclass, field
import os
import queue
import threading
import socket
import time
import logging
import uuid
from enum import StrEnum
from typing import overload

from ._dispatcher import Dispatcher, DispatcherNotAllowed, DispatcherNotFound
from ._utils import autofilling_split
from .http import HTTPRequest, HTTPResponse, HTTPStatus, HTTPException, Headers


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
class _Requester:
    ip: IP
    port: int

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"


@dataclass
class _PacketStats:
    is_finished: bool = False

    receiving: float | None = None
    balancing: float | None = None
    decoding: float | None = None
    dispatching: float | None = None
    executing: float | None = None
    encoding: float | None = None
    sending: float | None = None
    sent: float | None = None

    def __str__(self) -> str:
        return f"{f"{self.sent - self.receiving:.1f}ms" if self.is_finished else 'N/A'} ({f"{self.balancing - self.receiving:.1f}ms" if self.balancing is not None else 'N/A'} {f"{self.decoding - self.balancing:.1f}ms" if self.decoding is not None else 'N/A'} {f"{self.dispatching - self.decoding:.1f}ms" if self.dispatching is not None else 'N/A'} {f"{self.executing - self.dispatching:.1f}ms" if self.executing is not None else 'N/A'} {f"{self.encoding - self.executing:.1f}ms" if self.encoding is not None else 'N/A'} {f"{self.sending - self.encoding:.1f}ms" if self.sending is not None else 'N/A'} {f"{self.sent - self.sending:.1f}ms" if self.sent is not None else 'N/A'})"


class _PacketState(StrEnum):
    Receiving = 'receiving'
    Balancing = 'balancing'
    Decoding = 'decoding'
    Dispatching = 'dispatching'
    Executing = 'executing'
    Encoding = 'encoding'
    Sending = 'sending'
    Sent = 'sent'


BUFFER_SIZE = 4096


@dataclass
class _Packet:
    requester: _Requester
    connection: socket.socket
    stats: _PacketStats = field(default_factory=_PacketStats)

    id_: uuid.UUID = field(default_factory=uuid.uuid4)

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
            self.mark(_PacketState.Decoding)
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
            self.mark(_PacketState.Encoding)
            self._res_body = self.response_http.to_bytes()

        return self._res_body

    def mark(self, state: _PacketState) -> None:
        if getattr(self.stats, state) is not None:
            raise ValueError(f"packet was already marked as {state}")
        else:
            setattr(self.stats, state, time.perf_counter())
            logging.debug(f"{state} {self}")

        if state == _PacketState.Sent:
            self.stats.is_finished = True
            logging.info(f"packet {self} was processed in {self.stats}")

    def __str__(self) -> str:
        return f"{self.id_} ({self.requester}) ({f"{self._req_http.method} {self._req_http.path}" if self._req_http is not None and self._req_http is not False else "N/A N/A"})"


class _Processor:
    _shut_down: threading.Event

    _dispatcher: Dispatcher

    incoming_queue: queue.Queue[_Packet]
    _processed_queue: queue.Queue[_Packet]

    _sending_thread: threading.Thread
    _processing_thread: threading.Thread

    def __init__(self, shut_down: threading.Event, dispatcher: Dispatcher) -> None:
        self._shut_down = shut_down
        self._dispatcher = dispatcher

        self.incoming_queue = queue.Queue()
        self._processed_queue = queue.Queue()

        self._sending_thread = threading.Thread(target=self._sending_worker)
        self._processing_thread = threading.Thread(target=self._processing_worker)

        # TODO separate into a separate separation
        self._sending_thread.start()
        self._processing_thread.start()

    def _sending_worker(self) -> None:
        for processed_packet in iter(self._processed_queue.get, None):
            data = processed_packet.response_body

            processed_packet.mark(_PacketState.Sending)
            with processed_packet.connection as conn:
                conn.sendall(data)

            processed_packet.mark(_PacketState.Sent)

    def _processing_worker(self) -> None:
        for incoming_packet in iter(self.incoming_queue.get, None):
            http_req = incoming_packet.request_http

            if http_req is False:
                logging.warning(f"{incoming_packet} is invalid")
                continue

            incoming_packet.mark(_PacketState.Dispatching)
            try:
                try:
                    callback = self._dispatcher.dispatch(http_req.path, http_req.method)
                except DispatcherNotFound:
                    raise HTTPException(HTTPStatus.NotFound) from None
                except DispatcherNotAllowed:
                    raise HTTPException(HTTPStatus.MethodNotAllowed) from None

                incoming_packet.mark(_PacketState.Executing)
                incoming_packet.response_http = callback(incoming_packet.request_http)
            except HTTPException as http_exc:
                incoming_packet.response_http = HTTPResponse(http_exc.status_code, Headers(), http_exc.body)
            finally:
                self._processed_queue.put(incoming_packet)


class _Executor:
    _shut_down: threading.Event

    _dispatcher: Dispatcher

    _processors: list[_Processor]
    _last_worked_worker: int
    _worker_count: int

    def __init__(self, shut_down: threading.Event, dispatcher: Dispatcher, workers_count: int) -> None:
        self._shut_down = shut_down
        self._worker_count = workers_count
        self._dispatcher = dispatcher

        self._last_worked_worker = 0

        self._processors = [_Processor(self._shut_down, self._dispatcher) for _ in range(workers_count)]

    def execute(self, packet: _Packet):
        packet.mark(_PacketState.Balancing)
        self._processors[self._last_worked_worker].incoming_queue.put(packet)
        self._last_worked_worker = (self._last_worked_worker + 1) % self._worker_count


class _Socket:
    _shut_down: threading.Event

    _executor: _Executor

    _socket: socket.socket
    _socket_thread: threading.Thread

    _packet_queue: queue.Queue[_Packet]
    _queue_thread: threading.Thread

    def __init__(self, shut_down: threading.Event, executor: _Executor, port: int, listen: bool) -> None:
        self._shut_down = shut_down
        self._executor = executor

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._packet_queue = queue.Queue()

        self._socket_thread = threading.Thread(target=self._socket_worker, args=(port, listen))
        self._queue_thread = threading.Thread(target=self._queue_worker)

    def start_the_machine(self):
        self._socket_thread.start()
        self._queue_thread.start()

    def _socket_worker(self, port: int, listen: bool) -> None:
        with self._socket as s:
            s.bind(('0.0.0.0' if listen else '127.0.0.1', port))
            s.listen(True)

            while not self._shut_down.is_set():
                conn, addr = s.accept()
                (p := _Packet(_Requester(IP(tuple(map(int, addr[0].split('.')))), addr[1]), conn)).mark(_PacketState.Receiving)
                self._packet_queue.put(p)

    def _queue_worker(self) -> None:
        for packet in iter(self._packet_queue.get, None):
            self._executor.execute(packet)


class Server:
    dispatcher: Dispatcher

    _shut_down: threading.Event

    _socket: _Socket | None = None
    _executor: _Executor | None = None

    def __init__(self) -> None:
        self._shut_down = threading.Event()
        self.dispatcher = Dispatcher()

        self._socket = None
        self._executor = None

    @property
    def is_working(self) -> bool:
        raise NotImplementedError("idfk")

    def start(self, port: int, /, debug: bool = False, listen: bool = False, workers: int = os.cpu_count() or 1) -> None:
        logging.basicConfig(level='DEBUG' if debug else 'INFO')

        self._executor = _Executor(self._shut_down, self.dispatcher, workers)

        self._socket = _Socket(self._shut_down, self._executor, port, listen)
        self._socket.start_the_machine()

    def stop(self) -> None:
        raise NotImplementedError("you cant stop it")
