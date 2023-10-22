from .characters import UNRESERVED


def _encode_char(c: str) -> str:
    # if not isinstance(c, str):
    #     raise TypeError(f"expected an ASCII 1-char long 'str' ('char'), got {type(c).__name__} instead")
    # if not c.isascii():
    #     raise TypeError(f"expected an ASCII 1-char long 'str' ('char'), got non-ASCII instead")
    # if (c_len := len(c)) != 1:
    #     raise TypeError(f"expected an ASCII 1-char long 'str' ('char'), got {c_len}-char long instead")

    return f"%{c:0>2X}"


def encode(s: str) -> str:
    return ''.join(c if c in UNRESERVED else _encode_char(c) for c in s)


def _decode_char(c: str) -> str:
    # if not isinstance(c, str):
    #     raise TypeError(f"expected an ASCII 3-char long 'str' starting with '%' (percent-encoded byte), got {type(c).__name__} instead")
    # if not c.isascii():
    #     raise TypeError(f"expected an ASCII 3-char long 'str' starting with '%' (percent-encoded byte), got non-ASCII instead")
    # if (c_len := len(c)) != 3:
    #     raise TypeError(f"expected an ASCII 3-char long 'str' starting with '%' (percent-encoded byte), got {c_len}-char long instead")
    if not c.startswith('%'):
        raise ValueError(f"expected an ASCII 3-char long 'str' starting with '%' (percent-encoded byte), got starting with '{c[0]}' instead")

    return chr(int(c[1:], base=16))


# TODO dont abuse exception mechanics, rn it is like ~~520%~~ 392% worse than urllib's
def decode(s: str) -> str:
    buffer = ""

    while s:
        try:
            buffer += _decode_char(s[0:3])
            s = s[3:]
        except ValueError:
            buffer += s[0]
            s = s[1:]

    return buffer
