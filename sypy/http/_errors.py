from __future__ import annotations

import json
from typing import overload

from ._status import HTTPStatus


class HTTPException(RuntimeError):
    status_code: HTTPStatus
    body: bytes
    only_details: bool

    @overload
    def __init__(self, status_code: HTTPStatus, /, details: str | None = None) -> None: ...
    @overload
    def __init__(self, status_code: HTTPStatus, /, body: str | bytes | None = None) -> None: ...

    def __init__(self, status_code: HTTPStatus, /, details: str | None = None, body: str | bytes | None = None) -> None:
        if details and body:
            # maybe there is a better fitting error?
            raise TypeError(f"only details or body must be provided")

        self.status_code = status_code

        if body is not None:
            if isinstance(body, str):
                self.body = body.encode('utf-8')
            elif isinstance(body, bytes):
                self.body = body
            else:
                raise TypeError(f"expected 'body' to be 'str' or 'bytes', got '{type(body).__name__}' instead")

            self.only_details = False
        elif details is not None:
            if isinstance(details, str):
                self.body = json.dumps({'details': details}).encode('utf-8')
            else:
                raise TypeError(f"expected 'details' to be 'str', got '{type(details).__name__}' instead")

            self.only_details = True
        else:
            self.body = bytes()

    def __str__(self) -> str:
        return f"{str(self.status_code)} - {json.loads(self.body.decode('utf-8'))['details'] if self.only_details else self.body}"


class InvalidHTTPPacket(RuntimeError):
    pass
