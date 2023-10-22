from __future__ import annotations
import inspect
import json
from typing import Callable, Any, _AnnotatedAlias, get_args

from ..http import HTTPStatus, Headers, HTTPException
from .._utils import isinstanceorclass, is_in
from ..http import HTTPRequest, HTTPResponse
from ..parameters import Body, Query, Header, Depends


class _Nothing:
    pass


# P: T | Annotated[T, Body | Query | Header | Depends]
class Callback[**T, **P, R: int | str | bytes | dict | list | tuple]:
    query_params: list[tuple[int, str, type, bool, Any]]
    header_params: list[tuple[int, str, type, bool, Any]]
    body_param: tuple[int, type] | None
    dependent_params: list[tuple[int, Callback]]

    callback: Callable[[P], R]
    converter: Callable[[R], bytes]

    def __init__(self, callback: Callable[[P], R]) -> None:
        self.callback = callback

        self.query_params = []
        self.header_params = []
        self.body_param = None
        self.dependent_params = []

        signature = inspect.signature(callback)

        for i, (name, param) in enumerate(signature.parameters.items()):
            if param == param.KEYWORD_ONLY:
                raise TypeError("all arguments in a callback must be addressable by position")

            if isinstance((type_ := param.annotation), _AnnotatedAlias):
                annotated_type = type_.__metadata__[0]

                if isinstanceorclass(annotated_type, Body):
                    if self.body_param is not None:
                        raise TypeError("there can only be one 'Body' parameter")
                    else:
                        self.body_param = i, type_
                elif isinstanceorclass(annotated_type, Query):
                    self.query_params.append((i, param.name, type_, param.default != param.empty, param.default))
                elif isinstanceorclass(annotated_type, Header):
                    self.header_params.append((i, param.name, type_, param.default != param.empty, param.default))
                elif isinstance(annotated_type, Depends):
                    self.dependent_params.append((i, annotated_type.dependency, param.default != param.empty, param.default))
                elif annotated_type is Depends:
                    raise TypeError("on what the hell does it depend on?")
                else:
                    raise TypeError("pls annotated your shit correctly, thanks")
            else:
                self.query_params.append((i, param.name, type_, param.default != param.empty, param.default))

        if signature.return_annotation is int:
            self.converter = lambda n: str(n).encode('ascii')
        elif signature.return_annotation is str:
            self.converter = lambda s: s.encode('utf-8')
        elif signature.return_annotation is bytes:
            self.converter = lambda b: b
        elif is_in(signature.return_annotation, (dict, list, tuple)):
            self.converter = lambda d: json.dumps(d).encode('utf-8')
        else:
            raise TypeError("not supported return buddy, not supported")

    def __call__(self, request: HTTPRequest) -> HTTPResponse:
        total_parameters = len(self.query_params) + len(self.header_params) + len(self.dependent_params) + (self.body_param is not None)
        unprocessed_parameters: list[_Nothing | tuple[str, type | None]] = [_Nothing for _ in range(total_parameters)]

        def do_stuff(magic: tuple[int, str, type, bool, Any], params: dict) -> None:
            nonlocal unprocessed_parameters

            if magic[1] not in params:
                if magic[3]:
                    unprocessed_parameters[magic[0]] = magic[4], get_args(magic[2])[0]
            else:
                unprocessed_parameters[magic[0]] = params[magic[1]], get_args(magic[2])[0]

        for query_param in self.query_params:
            do_stuff(query_param, request.query_params)
        for header_param in self.header_params:
            do_stuff(header_param, request.headers)
        for depends_param in self.dependent_params:
            unprocessed_parameters[depends_param[0]] = depends_param[1](request), None
        if self.body_param is not None:
            unprocessed_parameters[self.body_param[0]] = request.body, get_args(self.body_param[1])[0]

        if _Nothing in unprocessed_parameters:
            raise HTTPException(HTTPStatus.UnprocessableContent, details="you forgor something")

        parameters: list[int | str | bool | None] = []
        for value, type_ in unprocessed_parameters:
            if isinstance(value, bytes):
                value = value.decode('ascii')

            if type_ is None:
                parameters.append(value)
            elif (v := value.strip().lower()) == 'null':
                parameters.append(None)
            elif type_ is int:
                parameters.append(int(v))
            elif type_ is str:
                parameters.append(value)
            elif type_ is bool:
                parameters.append(True if v == 'true' else False if v == 'false' else None)  # TODO raise some kind of exception idk
            elif type_ is bytes:
                parameters.append(value.encode('ascii'))
            else:
                raise TypeError("implement yourself, not supported callback signature paramater's type")

        return HTTPResponse(HTTPStatus.OK, Headers(), self.converter(self.callback(*parameters)))
