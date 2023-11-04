from __future__ import annotations
from dataclasses import dataclass

from .parts import Headers, QueryParams
from .._method import HTTPMethod
from .._errors import HTTPException, InvalidPath, InvalidMethod, EmptyPacket
from .._status import HTTPStatus
from ..path import Path
from ..path.encoder import encode
from ..._utils import autofilling_split, fillingin


@dataclass
class HTTPRequest:
    path: Path
    method: HTTPMethod
    headers: Headers
    query_params: QueryParams
    body: bytes

    @staticmethod
    def from_bytes(raw: bytes) -> HTTPRequest:
        if not raw:
            raise EmptyPacket()

        buff = ""
        endseq_combo = 0
        for b in raw:
            buff += chr(b)

            if endseq_combo == 0 and b == ord('\r'):
                endseq_combo = 1
            elif endseq_combo == 1 and b == ord('\n'):
                endseq_combo = 2
            elif endseq_combo == 2 and b == ord('\r'):
                endseq_combo = 3
            elif endseq_combo == 3 and b == ord('\n'):
                break
            else:
                endseq_combo = 0

        magic, *headers_raw = fillingin(buff.splitlines(), 2, "")
        headers_raw.pop()

        method_raw, path_unparsed, version = magic.split(' ', 2)

        if version != 'HTTP/1.1':
            raise HTTPException(HTTPStatus.HTTPVersionNotSupported, f"nuh uh, not supported: {version}")

        path_raw, query_params_raw = autofilling_split(path_unparsed, '?', 1)

        try:
            path = Path(path_raw)
        except ValueError:
            raise InvalidPath(path_raw) from None

        try:
            method = HTTPMethod(method_raw)
        except ValueError:
            raise InvalidMethod(method_raw) from None

        return HTTPRequest(path, method, Headers.from_string(headers_raw), QueryParams.from_string(query_params_raw), raw[len(buff):])


@dataclass
class HTTPResponse:
    status: HTTPStatus
    headers: Headers
    body: bytes

    def to_bytes(self) -> bytes:
        return f"HTTP/1.1 {self.status}\r\n{self.headers.to_string()}\r\n\r\n".encode('ascii') + self.body
