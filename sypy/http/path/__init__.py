from dataclasses import dataclass
from typing import overload

from .characters import RESERVED, UNRESERVED
from .encoder import decode


class Path:
    parts: list[str]

    @staticmethod
    def _validate_path(path: str) -> None:
        if not path.startswith('/'):
            raise ValueError(f"invalid path, doesn't begin with '/'")

        for c in path:
            if c not in RESERVED + UNRESERVED + '%':
                raise ValueError(f"invalid path, unexpected char: {c}")

    @overload
    def __init__(self, path: str) -> None: ...
    @overload
    def __init__(self, parts: list[str]) -> None: ...

    def __init__(self, *args) -> None:
        self._validate_path(args[0])
        self.parts = [decode(part) for part in args[0].removesuffix('/').removeprefix('/').split('/')] if isinstance(args[0], str) else args[0]

    def __str__(self) -> str:
        return f"/{'/'.join(self.parts)}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.parts!r})"
