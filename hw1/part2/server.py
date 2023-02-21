import asyncio
import logging
import grpc
import chat_pb2_grpc

from collections import abc
from dataclasses import dataclass
from typing import Union

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
@dataclass
class User:
    handle: str

    def __init__(self, user: chat_pb2.User):
        self.handle = user.handle

    def into(self):
        return chat_pb2.User(handle=self.handle)

    def __hash__(self):
        return hash(self.handle)

    def __str__(self):
        return self.handle


@dataclass
class SessionToken:
    tok: int

    def __init__(self, tok: Union[chat_pb2.SessionToken, int]):
        if isinstance(tok, chat_pb2.SessionToken):
            self.tok = tok.tok
        elif isinstance(tok, int):
            self.tok = tok
        else:
            assert False

    def into(self):
        return chat_pb2.SessionToken(tok=self.tok)

    def __hash__(self):
        return hash(self.tok)

    def __str__(self):
        return str(self.tok)


# In a real app, we'd use a database, but for this app, we'll use in-memory
# structures for logins, messages, etc.


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


class BadToken(UserError):
    message = "no session has token %s"

    def __init__(self, tok):
        super().__init__(code=305, msg=(self.message % tok))


# This class holds the details of any particular client connection (namely, the
# username of the user it corresponds to).


class Session:
    username: User
    pending_msgs: asyncio.Queue[Union[Msg, list[Msg]]]

    def __init__(self, username: User):
        self.username = username
        self.pending_msgs = asyncio.Queue()

    def __aiter__(self) -> abc.AsyncIterator[Union[Msg, list[Msg]]]:
        return self

    async def __anext__(self) -> Union[Msg, list[Msg]]:
        return await self.pending_msgs.get()

    async def receive_msgs(self, msgs: list[Msg]) -> None:
        await self.pending_msgs.put(msgs)

    async def receive_msg(self, text: str, sender: User) -> None:
        await self.pending_msgs.put(Msg(text=text, sender=sender.into()))

    def cleanup(self):
        if self.username is not None:
            self.logout_handler(self.username)


@dataclass
class LoggedIn:
    session: Session


@dataclass
class LoggedOut:
    pending_msgs: list[Msg]


class State(ChatSessionServicer):
    curr_tok: SessionToken
    sessions: dict[SessionToken, Session]
    known_users: dict[User, Union[LoggedIn, LoggedOut]]

    def __init__(self):
        self.curr_tok = SessionToken(tok=1)
        self.sessions = dict()
        self.known_users = dict()

    # XXX: In a real application, we'd use a dedicated session token generator
    # instead of simply incrementing a counter..
    def fresh_token(self) -> SessionToken:
        prev = self.curr_tok
        self.curr_tok = SessionToken(((prev.tok + 1) % MAX_TOKEN) + 1)
        return prev

    def lookup_session(self, tok: SessionToken) -> Session:
        if tok not in self.sessions:
            raise BadToken(tok)

        return self.sessions[tok]

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

        # It is important that the [await] happens _after_ we set the user to
        # [LoggedIn]. If we don't, then the scheduler may attempt to send
        # more messages to the session while we are enqueuing the local
        # [pending_msgs], which will be appended to [known_users[user].pending_msgs]
        # and promptly dropped on the floor.
        self.known_users[user] = LoggedIn(session)
        await session.receive_msgs(pending_msgs)

        return tok

    async def handle_send_message(
        self, text: str, *, sender: User, recipient: User
    ) -> Ok:
        # Send the message to user
        if recipient not in self.known_users:
            raise NoSuchUser(recipient)

        login_status = self.known_users[recipient]

        if isinstance(login_status, LoggedIn):
            await login_status.session.receive_msg(text, sender)
        elif isinstance(login_status, LoggedOut):
            login_status.pending_msgs.append(
                Msg(text=text, sender=sender.into(), recipient=recipient.into())
            )
        else:
            assert False

        return Ok()

    def create_user(self, user: User) -> Ok:
        if user in self.known_users:
            raise UserAlreadyExists(user)

        self.known_users[user] = LoggedOut([])

        return Ok()

    def delete_user(self, user: User) -> Ok:
        if user in self.known_users:
            del self.known_users[user]

        # If it's not there, oh well. The point of [delete_user] is to produce
        # a server state in which the desired user no longer exists, so if that
        # user didn't exist in the first place, cool.
        return Ok()

    # gRPC methods

    async def Create(self, req, _ctx) -> OkOrError:
        try:
            # See the comment above [User].
            user = User(req)
            return OkOrError(ok=self.create_user(user))
        except UserError as e:
            return OkOrError(err=e.into())

    async def ListUsers(self, _req, _ctx) -> UserList:
        result = list(user.into() for user in self.known_users.keys())
        return UserList(users=result)

    async def DeleteUser(self, req, _ctx) -> Ok:
        return self.delete_user(User(req))

    async def Login(self, req, _ctx) -> SessionTokenOrError:
        try:
            user = User(req)
            result = await self.handle_login(user)
            tok = SessionTokenOrError(ok=result.into())
            return tok
        except UserError as e:
            return SessionTokenOrError(err=e.into())

    async def SendMsg(self, req, _ctx) -> OkOrError:
        try:
            tok = req.tok
            sess = self.lookup_session(SessionToken(tok))

            sender = sess.username

            text = req.msg.text
            # We ignore [req.msg.sender] here, as it is inferred from the session.
            recipient = req.msg.recipient

            return OkOrError(
                ok=await self.handle_send_message(
                    text, sender=sender, recipient=User(recipient)
                )
            )
        except UserError as e:
            return OkOrError(err=e.into())

    async def IncomingMsgs(self, req, _ctx):
        tok = SessionToken(req)
        try:
            sess = self.lookup_session(tok)
            try:
                async for item in sess:
                    if isinstance(item, list):
                        for msg in item:
                            yield msg
                    else:
                        yield item
            finally:
                self.known_users[sess.username] = LoggedOut([])
                del self.sessions[tok]
        except UserError:
            # protobuf has no way to say "stream or error", so i guess we just
            # throw the error on the floor and die
            return


async def main(host: str, port: int):
    server = grpc.aio.server()

    chat_pb2_grpc.add_ChatSessionServicer_to_server(State(), server)
    addr = "%s:%s" % (host, port)

    server.add_insecure_port(addr)
    logging.info("starting server on %s", addr)
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main("localhost", 8888))
