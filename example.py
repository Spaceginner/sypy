from typing import Annotated

from sypy import Server
from sypy.parameters import Body


server = Server()


@server.post('/echo')
def echo(stuff: Annotated[str, Body]) -> str:
    return stuff


@server.get('/faulty')
def faulty_callback() -> None:
    0 / 0


if __name__ == '__main__':
    server.start(3000, listen=True)
