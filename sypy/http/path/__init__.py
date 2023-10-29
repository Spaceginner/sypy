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

    def __init__(self, path: str) -> None:
        self._validate_path(path)
        # TODO remove the inner if-statement at all (ie move the check out)
        self.parts = [part if '%' not in part else decode(part) for part in path.removesuffix('/').removeprefix('/').split('/')]

    def __str__(self) -> str:
        return f"/{'/'.join(self.parts)}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.parts!r})"
