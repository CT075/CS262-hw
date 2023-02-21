# Unfortunately, mypy doesn't play nicely with protobuf at all

from dataclasses import dataclass
from typing import Optional, Union
from collections.abc import Coroutine
from asyncio import Queue

from common import UserError

import chat_pb2
from chat_pb2 import (
    Ok,
    OkOrError,
    UserList,
    Msg,
    SessionTokenOrError,
)
from chat_pb2_grpc import ChatSessionServicer

MAX_TOKEN = 1 << 32

# This is an awful, awful hack that is necessary because protobuf-generated
# types aren't hashable.
class User(chat_pb2.User):
    def __hash__(self):
        return hash(self.handle)


class SessionToken(chat_pb2.SessionToken):
    def __hash__(self):
        return hash(self.tok)


# In a real app, we'd use a database, but for this app, we'll use in-memory
# structures for logins, messages, etc.


@dataclass
class Message:
    sender: User
    recipient: User
    content: str

    def to_jsonable_type(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
        }


# See notes on [jsonrpc.Jsonable] for why these wrappers are necessary.
@dataclass
class MessageList:
    data: list[Message]

    def to_jsonable_type(self):
        return [msg.to_jsonable_type() for msg in self.data]

    def append(self, msg: Message):
        self.data.append(msg)

    def __iter__(self):
        return self.data.__iter__()


class NoSuchUser(UserError):
    message = "no such user: %s"

    def __init__(self, s):
        super().__init__(code=301, msg=(self.message % s))


class AlreadyLoggedIn(UserError):
    message = "user %s is already logged in"

    def __init__(self, s):
        super().__init__(code=302, msg=(self.message % s))


class UserAlreadyExists(UserError):
    message = "user %s already exists"

    def __init__(self, s):
        super().__init__(code=303, msg=(self.message % s))


class NotLoggedIn:
    message = "you must be logged in to send messages"

    def __init__(self):
        super().__init__(code=304, msg=self.message)


# This class holds the details of any particular client connection (namely, the
# username of the user it corresponds to).


class Session:
    username: User
    pending_msgs: Queue[Msg]

    def __init__(self, username: User):
        self.username = username

    async def send_message(self, text: str, recipient: User) -> Ok:
        if self.username is None:
            raise NotLoggedIn()

        return await self.message_handler(Message(self.username, recipient, text))

    async def receive_message(self, msg: Message) -> Ok:
        await self.owner.request(
            method="receive_message",
            params=[msg.to_jsonable_type()],
            is_notification=True,
        )
        return Ok()

    async def __aiter__(self):
        return self

    async def __anext__(self) -> Msg:
        return await self.pending_msgs.get()

    async def receive_msg(self, text: str, sender: User) -> None:
        await self.pending_msgs.put(Msg(text=text, sender=sender))

    def cleanup(self):
        if self.username is not None:
            self.logout_handler(self.username)


@dataclass
class LoggedIn:
    session: Session


@dataclass
class LoggedOut:
    pending_msgs: MessageList


class State(ChatSessionServicer):
    curr_tok: SessionToken
    sessions: dict[SessionToken, Optional[Session]]
    known_users: dict[User, Union[LoggedIn, LoggedOut]]

    def __init__(self):
        self.curr_tok = SessionToken(tok=0)
        self.known_users = dict()

    # XXX: In a real application, we'd use a dedicated session token generator
    # instead of simply incrementing a counter..
    def fresh_token(self) -> SessionToken:
        prev = self.curr_tok
        self.curr_tok = SessionToken(tok=(prev.tok + 1 % MAX_TOKEN))
        return prev

    def initialize_session(self) -> SessionToken:
        tok = self.fresh_token()
        self.sessions[tok] = None
        return tok

    async def handle_login(self, user: User) -> SessionToken:
        if user not in self.known_users:
            raise NoSuchUser(user)

        login_status = self.known_users[user]

        if isinstance(login_status, LoggedIn):
            raise AlreadyLoggedIn(user)

        assert isinstance(login_status, LoggedOut)
        pending_msgs = login_status.pending_msgs

        tok = self.fresh_token()
        session = Session(user)
        self.sessions[tok] = session

        self.known_users[user] = LoggedIn(session)

        return tok

    def handle_logout(self, user: User) -> None:
        self.known_users[user] = LoggedOut(MessageList([]))

    async def handle_send_message(self, msg: Message) -> Ok:
        # Send the message to user
        if msg.recipient not in self.known_users:
            raise NoSuchUser(msg.recipient)

        login_status = self.known_users[msg.recipient]

        if isinstance(login_status, LoggedIn):
            await login_status.session.receive_message(msg)
        elif isinstance(login_status, LoggedOut):
            login_status.pending_msgs.append(msg)
        else:
            assert False

        return Ok()

    def create_user(self, user: User) -> Ok:
        if user in self.known_users:
            raise UserAlreadyExists(user)

        self.known_users[user] = LoggedOut(MessageList([]))

        return Ok()

    def delete_user(self, user: User) -> Ok:
        if user in self.known_users:
            del self.known_users[user]

        # If it's not there, oh well. The point of [delete_user] is to produce
        # a server state in which the desired user no longer exists, so if that
        # user didn't exist in the first place, cool.
        return Ok()

    async def Create(self, req, _ctx) -> OkOrError:
        try:
            # See the comment above [User].
            req.__class__ = User
            return OkOrError(ok=self.create_user(req))
        except UserError as e:
            return OkOrError(err=e)

    async def ListUsers(self, _req, _ctx) -> UserList:
        return UserList(users=list(self.known_users.keys()))

    async def DeleteUser(self, req, _ctx) -> Ok:
        req.__class__ = User
        return self.delete_user(req)

    async def Login(self, req, _ctx) -> SessionTokenOrError:
        # TODO
        pass

    # TODO: the difference between [session] and [user_session] is confusing,
    # come up with better names
    async def handle_incoming(self, reader, writer) -> None:
        session = jsonrpc.spawn_session(reader, writer)
        user_session = Session(
            session, self.handle_login, self.handle_logout, self.handle_send_message
        )

        # TODO: the rest of the handlers
        session.register_handler("login", user_session.login)
        session.register_handler("create_user", self.create_user)
        session.register_handler("list_users", self.list_users)
        session.register_handler("delete_user", self.delete_user)
        session.register_handler("send", user_session.send_message)

        await session.run_event_loop()
        user_session.cleanup()


async def main(host: str, port: int):
    state = State()
    server = await asyncio.start_server(state.handle_incoming, host, port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main("10.250.159.96", 8888))
