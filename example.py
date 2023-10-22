from typing import Annotated

from sypy import Server
from sypy.http import HTTPMethod
from sypy.http.path import Path
from sypy.parameters import Body


server = Server()


def echo(stuff: Annotated[str, Body]) -> str:
    return stuff


server.dispatcher.register_callback(Path('/echo'), HTTPMethod.POST, echo)


if __name__ == '__main__':
    server.start(3014, listen=True, workers=4)
