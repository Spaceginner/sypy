import math
from typing import Annotated, NoReturn

from sypy import Server, RunConfig
from sypy.http import HTTPException, HTTPStatus, Headers
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


LOCATIONS = {
    'google': "https://www.google.com/",
    'youtube': "https://www.youtube.com/",
    'arcos': "https://www.izk-arcos.nl/",
}


@server.get('/redirect')
def headers(where: str) -> NoReturn:
    try:
        raise HTTPException(
            HTTPStatus.PermanentRedirect,
            "follow that way, traveller", 
            Headers(location=LOCATIONS[where])
        )
    except KeyError:
        raise HTTPException(
            HTTPStatus.NotFound,
            "the place is unkown for me, traveller"
        ) from None


@server.get('/redirect/loop')
def looping() -> NoReturn:
    raise HTTPException(
        HTTPStatus.MovedPermanently,
        "this is definetely not a trap",
        Headers(location='/redirect/loop')
    )


if __name__ == '__main__':
    server.start(RunConfig(3000))
