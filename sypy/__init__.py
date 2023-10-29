from __future__ import annotations

import os
import queue
import threading
import socket
import logging
from dataclasses import dataclass
from typing import Callable

from ._dispatcher.callback import Calls
from ._packet import Packet, PacketState
from ._dispatcher import Dispatcher, DispatcherNotAllowed, DispatcherNotFound
from ._packet import Packet, PacketState, Requester, IP
from ._utils import autofilling_split
from .http import HTTPRequest, HTTPResponse, HTTPStatus, HTTPException, Headers, Path, HTTPMethod, InvalidMethod, InvalidPath, EmptyPacket


@dataclass
class RunConfig:
    port: int
    workers: int = os.cpu_count() or 1
    debug: bool = False
    listen: bool = False
    exposing: bool = True


class _Processor:
    _shut_down: threading.Event

    _dispatcher: Dispatcher

    incoming_queue: queue.Queue[Packet]
    _processed_queue: queue.Queue[Packet]

    _sending_thread: threading.Thread
    _processing_thread: threading.Thread

    _run_config: RunConfig

    def __init__(self, run_config: RunConfig, shut_down: threading.Event, dispatcher: Dispatcher) -> None:
        self._run_config = run_config
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

            with processed_packet.connection as conn:
                conn.sendall(data)

            processed_packet.mark(PacketState.Sent)

    def _processing_worker(self) -> None:
        for incoming_packet in iter(self.incoming_queue.get, None):
            try:
                request_http = incoming_packet.request_http
            except (InvalidPath, InvalidMethod) as exc:
                logging.warning(f"{incoming_packet} - {exc}")
            except EmptyPacket:
                pass  # silence
            else:
                try:
                    try:
                        callback = self._dispatcher.dispatch(request_http.path, request_http.method)
                    except DispatcherNotFound:
                        raise HTTPException(HTTPStatus.NotFound) from None
                    except DispatcherNotAllowed:
                        raise HTTPException(HTTPStatus.MethodNotAllowed) from None
                    else:
                        try:
                            response_http = callback(request_http, Calls(lambda: incoming_packet.mark(PacketState.Executing), lambda: incoming_packet.mark(PacketState.Executed)))
                        except Exception as exc:
                            # ignore HTTPExceptions
                            if isinstance(exc, HTTPException):
                                raise exc from exc.__context__

                            raise HTTPException(HTTPStatus.InternalServerError, f"{type(exc).__name__}: {exc}" if self._run_config.exposing else "contact administration pls") from None
                        else:
                            incoming_packet.response_http = response_http
                except HTTPException as http_exc:
                    incoming_packet.response_http = HTTPResponse(http_exc.status_code, Headers(), http_exc.body)
                else:
                    self._processed_queue.put(incoming_packet)


class _Executor:
    _run_config: RunConfig
    _shut_down: threading.Event

    _dispatcher: Dispatcher

    _processors: list[_Processor]
    _last_worked_worker: int

    def __init__(self, run_config: RunConfig, shut_down: threading.Event, dispatcher: Dispatcher) -> None:
        self._shut_down = shut_down
        self._dispatcher = dispatcher
        self._run_config = run_config

        self._last_worked_worker = 0

        self._processors = [_Processor(self._run_config, self._shut_down, self._dispatcher) for _ in range(self._run_config.workers)]

    def execute(self, packet: Packet):
        self._processors[self._last_worked_worker].incoming_queue.put(packet)
        self._last_worked_worker = (self._last_worked_worker + 1) % self._run_config.workers


class _Socket:
    _run_config: RunConfig
    _shut_down: threading.Event

    _executor: _Executor

    _socket: socket.socket
    _socket_thread: threading.Thread

    _packet_queue: queue.Queue[Packet]
    _queue_thread: threading.Thread

    def __init__(self, _run_config: RunConfig, shut_down: threading.Event, executor: _Executor) -> None:
        self._run_config = _run_config
        self._shut_down = shut_down
        self._executor = executor

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._packet_queue = queue.Queue()

        self._socket_thread = threading.Thread(target=self._socket_worker)
        self._queue_thread = threading.Thread(target=self._queue_worker)

    def start_the_machine(self):
        self._socket_thread.start()
        self._queue_thread.start()

    def _socket_worker(self) -> None:
        host = ('0.0.0.0' if self._run_config.listen else '127.0.0.1', self._run_config.port)

        logging.info(f"launching socket worker on {':'.join(map(str, host))}")
        with self._socket as s:
            s.bind(host)
            s.listen(True)

            while not self._shut_down.is_set():
                conn, addr = s.accept()
                (p := Packet(Requester(IP(tuple(map(int, addr[0].split('.')))), addr[1]), conn)).mark(PacketState.Receiving)
                self._packet_queue.put(p)

    def _queue_worker(self) -> None:
        for packet in iter(self._packet_queue.get, None):
            self._executor.execute(packet)


class Server:
    dispatcher: Dispatcher

    _run_config: RunConfig
    _shut_down: threading.Event

    _socket: _Socket | None = None
    _executor: _Executor | None = None

    def __init__(self) -> None:
        self._shut_down = threading.Event()
        self.dispatcher = Dispatcher()

    @property
    def is_working(self) -> bool:
        raise NotImplementedError("idfk")

    def start(self, run_config: RunConfig) -> None:
        self._run_config = run_config

        logging.basicConfig(
            format="%(asctime)s %(levelname)s - %(message)s",
            level=logging.DEBUG if self._run_config.debug else logging.INFO
        )

        self._executor = _Executor(self._run_config, self._shut_down, self.dispatcher)

        self._socket = _Socket(self._run_config, self._shut_down, self._executor)
        self._socket.start_the_machine()

    def stop(self) -> None:
        raise NotImplementedError("you cant stop it")

    @staticmethod
    def _callback_register(method: HTTPMethod) -> Callable[[str], Callable[[Callable], Callable]]:
        def decorator(self, path: str) -> Callable[[Callable], Callable]:
            nonlocal method

            def register(callback: Callable) -> Callable:
                nonlocal path, self, method

                self.dispatcher.register_callback(Path(path), method, callback)

                return callback

            return register

        return decorator

    get = _callback_register(HTTPMethod.GET)
    head = _callback_register(HTTPMethod.HEAD)
    post = _callback_register(HTTPMethod.POST)
    put = _callback_register(HTTPMethod.PUT)
    delete = _callback_register(HTTPMethod.DELETE)
    connect = _callback_register(HTTPMethod.CONNECT)
    options = _callback_register(HTTPMethod.OPTIONS)
    trace = _callback_register(HTTPMethod.TRACE)
    patch = _callback_register(HTTPMethod.PATCH)
