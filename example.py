from typing import Annotated

from sypy import Server
from sypy.http import HTTPMethod
from sypy.http.path import Path
from sypy.parameters import Body


server = Server()


def echo(stuff: Annotated[str, Body]) -> str:
    return stuff


def faulty_callback() -> None:
    0 / 0


server.dispatcher.register_callback(Path('/echo'), HTTPMethod.POST, echo)
server.dispatcher.register_callback(Path('/faulty'), HTTPMethod.GET, faulty_callback)


if __name__ == '__main__':
    server.start(3001, listen=True, workers=4)
