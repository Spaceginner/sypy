from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ._dispatcher import Callback


class Body:
    pass


class Query:
    pass


class Header:
    pass


class Depends:
    dependency: Callback

    def __init__(self, dependency: Callable) -> None:
        from ._dispatcher import Callback

        self.dependency = Callback(dependency)
