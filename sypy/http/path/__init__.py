from dataclasses import dataclass
from typing import overload

from .characters import RESERVED, UNRESERVED
from .encoder import decode


class Path:
    parts: list[str]

    @staticmethod
    def _validate_path(path: str) -> None:
        # TODO add check for `/` in the beginning

        for c in path:
            if c not in RESERVED + UNRESERVED + '%':
                raise ValueError(f"invalid path, unexpected char: {c}")

    def __init__(self, path: str | list[str]) -> None:
        path_parts = path.removesuffix('/').removeprefix('/').split('/') if isinstance(path, str) else path

        # TODO combine 2 for-loops
        for part in path_parts:
            self._validate_path(part)

        # TODO remove the inner if-statement at all (ie move the check out)
        self.parts = [part if '%' not in part else decode(part) for part in path_parts]

    def __str__(self) -> str:
        return f"/{'/'.join(self.parts)}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.parts!r})"
