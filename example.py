import math
from typing import Annotated

from sypy import Server
from sypy.parameters import Body, Depends, Header

server = Server()


@server.post('/echo')
def echo(stuff: Annotated[str, Body]) -> str:
    return stuff


@server.get('/faulty')
def faulty_callback() -> None:
    0 / 0


THE_EASTER_EGG_VALUE = "fastapi"


def checker(the_thing: Annotated[str, Header]) -> bool:
    return the_thing == THE_EASTER_EGG_VALUE


def circle_area(radius: int = 4) -> float:
    return math.pi * radius*radius


@server.get('/is_it')
def jection(is_it: Annotated[bool, Depends(checker)], area: Annotated[float, Depends(circle_area)]) -> str:
    return f"{"yes, it is actually it" if is_it else "my condolences, it is not"}; btw it is {area:.2f}"


if __name__ == '__main__':
    server.start(3001)
