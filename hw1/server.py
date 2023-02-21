import asyncio
from dataclasses import dataclass
from typing import Optional, Union, Callable, NewType, Awaitable

import jsonrpc

User = NewType("User", str)

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


# TODO: should this live somewhere common?
class Ok:
    def to_jsonable_type(self):
        return "ok"


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


@dataclass
class UserList:
    data: list[User]

    def to_jsonable_type(self):
        return self.data


class NoSuchUser(jsonrpc.JsonRpcError):
    message = "no such user"

    def __init__(self, s):
        super().__init__(code=301, message=self.message, data=s)


class AlreadyLoggedIn(jsonrpc.JsonRpcError):
    message = "user is already logged in"

    def __init__(self, s):
        super().__init__(code=302, message=self.message, data=s)


class UserAlreadyExists(jsonrpc.JsonRpcError):
    message = "user already exists"

    def __init__(self, s):
        super().__init__(code=303, message=self.message, data=s)


class NotLoggedIn(jsonrpc.JsonRpcError):
    message = "you must be logged in to send messages"

    def __init__(self):
        super().__init__(code=304, message=self.message, data=[])


# This class holds the details of any particular client connection (namely, the
# username of the user it corresponds to). We indirect [login_handler] and
# [logout_handler] through this object because they need both connection-local
# state (e.g. "set/get the currently-logged-in user) and global state (the
# overall user database).
class Session:
    owner: jsonrpc.Session
    username: Optional[User]
    # [login_handler] will raise one of the above exceptions on failure.
    login_handler: Callable[["Session", User], MessageList]
    # logging out is idempotent, so [logout_handler] should not fail.
    logout_handler: Callable[[User], None]
    message_handler: Callable[[Message], Awaitable[Ok]]

    def __init__(
        self,
        owner: jsonrpc.Session,
        login_handler: Callable[["Session", User], MessageList],
        logout_handler: Callable[[User], None],
        message_handler: Callable[[Message], Awaitable[Ok]],
    ):
        self.owner = owner
        self.username = None
        self.login_handler = login_handler
        self.logout_handler = logout_handler
        self.message_handler = message_handler

    async def login(self, username: User) -> MessageList:
        self.username = username
        return self.login_handler(self, username)

    async def send_message(self, text: str, recipient: User) -> Ok:
        if self.username is None:
            raise NotLoggedIn()

        return await self.message_handler(Message(self.username, recipient, text))

    async def receive_message(self, msg: Message) -> Ok:
        await self.owner.request(
            method="receive_message", params=[msg.to_jsonable_type()], is_notification=True
        )
        return Ok()

    def cleanup(self):
        if self.username is not None:
            self.logout_handler(self.username)


@dataclass
class LoggedIn:
    session: Session


@dataclass
class LoggedOut:
    pending_msgs: MessageList


# We can avoid locks here due to the guarantees of async-await programming.
# In particular, job interleaving can only happen across an [await] boundary,
# so as long as we do all our modifications of [known_users] in one "breath",
# there should be no issues with another thread seeing an intermediate state.
class State:
    known_users: dict[User, Union[LoggedIn, LoggedOut]]

    def __init__(self):
        self.known_users = dict()
        self.sessions = set() #TODO: is this needed?

    def handle_login(self, session: Session, user: User) -> MessageList:
        if user not in self.known_users:
            raise NoSuchUser(user)

        login_status = self.known_users[user]

        if isinstance(login_status, LoggedIn):
            raise AlreadyLoggedIn(user)

        assert isinstance(login_status, LoggedOut)
        pending_msgs = login_status.pending_msgs

        self.known_users[user] = LoggedIn(session)

        return pending_msgs

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

    async def create_user(self, name: User) -> Ok:
        if name in self.known_users:
            raise UserAlreadyExists(name)

        self.known_users[name] = LoggedOut(MessageList([]))

        return Ok()

    async def list_users(self, *args) -> UserList:
        return UserList(list(self.known_users.keys()))

    async def delete_user(self, user: User) -> Ok:
        if user in self.known_users:
            del self.known_users[user]

        # If it's not there, oh well. The point of [delete_user] is to produce
        # a server state in which the desired user no longer exists, so if that
        # user didn't exist in the first place, cool.
        return Ok()

    # TODO: the difference between [session] and [user_session] is confusing,
    # come up with better names
    async def handle_incoming(self, reader, writer) -> None:
        session = jsonrpc.spawn_session(reader, writer)
        user_session = Session(
            session, self.handle_login, self.handle_logout, self.handle_send_message
        )

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
    asyncio.run(main("localhost", 8888))
