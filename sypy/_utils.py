from typing import Iterable, Sequence


def autofilling_split(s: str, split_char: str, count: int, default: str = "") -> list[str]:
    return [*(temp := s.split(split_char, count))] + [default for _ in range((count + 1) - len(temp))]


def fillingin[T](seq: Sequence[T], min_: int, filler: T) -> list[T]:
    return [*seq] + [filler for _ in range(max(0, min_ - len(seq)))]


def isinstanceorclass(obj: object, class_: type) -> bool:
    return isinstance(obj, class_) or obj is class_


def is_in(obj, iterable: Iterable) -> bool:
    return any(obj in item for item in iterable)
