from collections import defaultdict
from typing import Iterable, Sequence


def autofilling_split(s: str, split_char: str, count: int, default: str = "") -> list[str]:
    return [*(temp := s.split(split_char, count))] + [default for _ in range((count + 1) - len(temp))]


def fillingin[T](seq: Sequence[T], min_: int, filler: T) -> list[T]:
    return [*seq] + [filler for _ in range(max(0, min_ - len(seq)))]


def isinstanceorclass(obj: object, class_: type) -> bool:
    return isinstance(obj, class_) or obj is class_


def is_in(obj, iterable: Iterable) -> bool:
    return any(obj is item for item in iterable)


def defaultdict_of_defaultdicts_factory[K, V]() -> defaultdict[K, V]:
    return defaultdict(defaultdict_of_defaultdicts_factory)


def dataclass_from_dict[T](dataclass: type[T], dict_: dict) -> T:
    try:
        fieldtypes = dataclass.__annotations__  # TODO make use of something else then annotations for fields
        return dataclass(**{f: dataclass_from_dict(fieldtypes[f], dict_[f]) for f in dict_})
    except AttributeError:
        if isinstance(dict_, (tuple, list)):
            return [dataclass_from_dict(dataclass.__args__[0], f) for f in dict_]
        return dict_
