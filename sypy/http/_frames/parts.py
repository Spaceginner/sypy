from __future__ import annotations
import string

from ..path.encoder import encode
from ..._utils import autofilling_split


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
