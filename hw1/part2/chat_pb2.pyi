from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Error(_message.Message):
    __slots__ = ["code", "msg"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    code: int
    msg: str
    def __init__(self, code: _Optional[int] = ..., msg: _Optional[str] = ...) -> None: ...

class LoginRequest(_message.Message):
    __slots__ = ["tok", "user"]
    TOK_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    tok: SessionToken
    user: User
    def __init__(self, user: _Optional[_Union[User, _Mapping]] = ..., tok: _Optional[_Union[SessionToken, _Mapping]] = ...) -> None: ...

class Msg(_message.Message):
    __slots__ = ["sender", "text"]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    sender: User
    text: str
    def __init__(self, text: _Optional[str] = ..., sender: _Optional[_Union[User, _Mapping]] = ...) -> None: ...

class Ok(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class OkOrError(_message.Message):
    __slots__ = ["err", "ok"]
    ERR_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    err: Error
    ok: Ok
    def __init__(self, ok: _Optional[_Union[Ok, _Mapping]] = ..., err: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class SendRequest(_message.Message):
    __slots__ = ["msg", "tok"]
    MSG_FIELD_NUMBER: _ClassVar[int]
    TOK_FIELD_NUMBER: _ClassVar[int]
    msg: Msg
    tok: SessionToken
    def __init__(self, msg: _Optional[_Union[Msg, _Mapping]] = ..., tok: _Optional[_Union[SessionToken, _Mapping]] = ...) -> None: ...

class SessionToken(_message.Message):
    __slots__ = ["tok"]
    TOK_FIELD_NUMBER: _ClassVar[int]
    tok: int
    def __init__(self, tok: _Optional[int] = ...) -> None: ...

class SessionTokenOrError(_message.Message):
    __slots__ = ["err", "ok"]
    ERR_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    err: Error
    ok: SessionToken
    def __init__(self, ok: _Optional[_Union[SessionToken, _Mapping]] = ..., err: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ["handle"]
    HANDLE_FIELD_NUMBER: _ClassVar[int]
    handle: str
    def __init__(self, handle: _Optional[str] = ...) -> None: ...

class UserList(_message.Message):
    __slots__ = ["users"]
    USERS_FIELD_NUMBER: _ClassVar[int]
    users: _containers.RepeatedCompositeFieldContainer[User]
    def __init__(self, users: _Optional[_Iterable[_Union[User, _Mapping]]] = ...) -> None: ...
