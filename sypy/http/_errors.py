from __future__ import annotations

import json
from dataclasses import dataclass

from ._status import HTTPStatus
from ._frames.parts import Headers


class HTTPException(RuntimeError):
    status_code: HTTPStatus
    headers: Headers | None

    _message: str | bytes | None
    _json_key: str | None

    _body: bytes | None = None

    def __init__(self, status_code: HTTPStatus, message: str | bytes | None = None, headers: Headers | None = None, /, json_key: str | None = None) -> None:
        if isinstance(message, bytes) and json_key is not None:
            raise TypeError("you can't pack binary into json")

        self.status_code = status_code
        self.headers = headers
        self._message = message
        self._json_key = json_key

    @property
    def body(self):
        if self._body is None:
            if self._message is None:
                self._body = bytes()
            else:
                if isinstance(self._message, bytes):
                    self._body = self._message
                else:
                    if self._json_key is not None:
                        self._body = json.dumps({self._json_key: self._message}).encode('utf-8')
                    else:
                        self._body = self._message.encode('utf-8')

        return self._body

    def __str__(self) -> str:
        return f"{str(self.status_code)} - {self._message}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.status_code!r}, message={self._message!r}, json_key={self._json_key!r})"


class InvalidHTTPPacket(RuntimeError):
    pass


@dataclass
class InvalidPath(InvalidHTTPPacket):
    path: str

    def __str__(self) -> str:
        return f"invalid path - {self.path}"


@dataclass
class InvalidMethod(InvalidHTTPPacket):
    method: str

    def __str__(self) -> str:
        return f"invalid method - {self.method}"


@dataclass
class EmptyPacket(InvalidHTTPPacket):
    def __str__(self) -> str:
        return "packet is empty"
