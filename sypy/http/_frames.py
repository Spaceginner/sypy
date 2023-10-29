from __future__ import annotations
from dataclasses import dataclass
import string

from ._method import HTTPMethod
from ._errors import HTTPException, InvalidPath, InvalidMethod, EmptyPacket
from ._status import HTTPStatus
from .path import Path
from .path.encoder import encode
from .._utils import autofilling_split, fillingin


class Headers(dict[str, str]):
    @staticmethod
    def _process_index(index: str) -> str:
        return index.lower().replace('_', '-')

    @staticmethod
    def _prepare_index(index: str) -> str:
        return string.capwords(index, '-')

    def __setitem__(self, key: str, value):
        return super().__setitem__(self._process_index(key), value)

    def __getitem__(self, item):
        return super().__getitem__(self._process_index(item))

    def __contains__(self, item):
        return super().__contains__(self._process_index(item))

    @staticmethod
    def from_string(s: str) -> Headers:
        return Headers({Headers._process_index(field): value.strip() for field, value in map(lambda h_raw: h_raw.split(':', 1), s)})

    def to_string(self) -> str:
        return '\r\n'.join(f"{self._prepare_index(field)}: {value}" for field, value in self.items())


class QueryParams(dict[str, str]):
    @staticmethod
    def from_string(s: str) -> QueryParams:
        return QueryParams({param: value for param, value in map(lambda h_raw: autofilling_split(h_raw, '=', 1), s.removeprefix('&').split('&')) if param})

    def to_string(self) -> str:
        return '&'.join(f"{encode(field)}={encode(value)}" for field, value in self.items())


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
        return f"HTTP/1.1 {self.status}\r\n{self.headers.to_string()}\r\n".encode('ascii') + self.body
