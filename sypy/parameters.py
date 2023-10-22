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


@dataclass
class Depends:
    dependency: Callback
