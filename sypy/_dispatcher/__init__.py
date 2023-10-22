from __future__ import annotations

from collections import defaultdict
from typing import Callable

from .callback import Callback
from ..http._method import HTTPMethod
from ..http.path import Path


type MethodTable = dict[HTTPMethod, Callback]
type Endpoints = defaultdict[str, Endpoints | MethodTable]


class DispatcherNotFound(LookupError):
    pass


class DispatcherNotAllowed(KeyError):
    pass


class Dispatcher:
    _endpoints: Endpoints

    def __init__(self):
        self._endpoints = defaultdict(defaultdict)

    def _lookup_method_table(self, path_parts: list[str], /, _search: Endpoints | None = None) -> MethodTable:
        search = _search or self._endpoints

        if len(path_parts) == 1:
            return search[path_parts[0]]
        else:
            return self._lookup_method_table(path_parts, _search=search[path_parts.pop(0)])

    def dispatch(self, path: Path, method: HTTPMethod) -> Callback:
        try:
            method_table = self._lookup_method_table(path.parts)
        except KeyError:
            raise DispatcherNotFound(f"method/callback table was not found for {path}") from None
        
        try:
            return method_table[method]
        except KeyError:
            raise DispatcherNotAllowed(f"method '{method}' is not allowed for {path}") from None

    def register_callback(self, path: Path, method: HTTPMethod, callback: Callable, /, __endpoints: Endpoints | None = None) -> None:
        endpoints = __endpoints or self._endpoints

        if len(path.parts) > 1:
            self.register_callback(Path(path.parts[1:]), method, callback, __endpoints=endpoints[path.parts[0]])
        else:
            endpoints[path.parts[0]][method] = Callback(callback)
