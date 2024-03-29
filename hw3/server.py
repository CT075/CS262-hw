# XXX - Organizationally, this could do with some splitting; we currently mix a
# lot of domain-level concerns with the details of replication, etc.

import asyncio
import json
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, NoReturn, Any, Union
import os.path

from common import User, Ok, Host, Port, Address
import config
import jsonrpc

SERVER_DB_FORMAT = "{host}-{port}-db.json"

pending_jobs: set[asyncio.Task] = set()


async def ping() -> Ok:
    return Ok()


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
        if len(self.data) > 0:
            if isinstance(self.data[0], dict):
                return self.data

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


class AlreadyLoggedInSession(jsonrpc.JsonRpcError):
    message = "this session has already logged in"

    def __init__(self, s):
        super().__init__(code=306, message=self.message, data={"current_user": s})


class ImABackup(jsonrpc.JsonRpcError):
    message = "I am a backup, please connect to a primary server"

    def __init__(self):
        super().__init__(code=500, message=self.message, data=[])


class ImPrimary(jsonrpc.JsonRpcError):
    message = "I am currently acting as primary, we do not support hot restarts"

    def __init__(self):
        super().__init__(code=501, message=self.message, data=[])


@dataclass
class DbUpdate:
    db: dict[User, MessageList]
    mtime: Optional[float]

    def to_jsonable_type(self):
        return {
            "db": {user: msgs.to_jsonable_type() for user, msgs in self.db.items()},
            "mtime": self.mtime,
        }


# This class holds the details of any particular client connection (namely, the
# username of the user it corresponds to). We indirect [login_handler] and
# [logout_handler] through this object because they need both connection-local
# state (e.g. "set/get the currently-logged-in user) and global state (the
# overall user database).
class UserSession:
    owner: jsonrpc.Session
    username: Optional[User]
    # [login_handler] will raise one of the above exceptions on failure.
    login_handler: Callable[["UserSession", User], Awaitable[MessageList]]
    # logging out is idempotent, so [logout_handler] should not fail.
    logout_handler: Callable[[User], None]
    message_handler: Callable[[Message], Awaitable[Ok]]

    def __init__(
        self,
        owner: jsonrpc.Session,
        login_handler: Callable[["UserSession", User], Awaitable[MessageList]],
        logout_handler: Callable[[User], None],
        message_handler: Callable[[Message], Awaitable[Ok]],
    ):
        self.owner = owner
        self.username = None
        self.login_handler = login_handler
        self.logout_handler = logout_handler
        self.message_handler = message_handler

    async def login(self, username: User) -> MessageList:
        if self.username is not None:
            raise AlreadyLoggedInSession(self.username)

        self.username = username
        return await self.login_handler(self, username)

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

    def cleanup(self):
        if self.username is not None:
            self.logout_handler(self.username)


def wrap_message_lists(d: dict[User, list[Message]]):
    return {user: MessageList(messages) for user, messages in d.items()}


@dataclass
class Db:
    d: dict[User, MessageList]
    store_path: str

    def __init__(self, d, store_path):
        self.d = wrap_message_lists(d)
        self.store_path = store_path

    def __getitem__(self, item: User) -> MessageList:
        return self.d[item]

    def fetch_pending_msgs(self, user: User):
        result = self.d[user]
        self.d[user] = MessageList([])

        return MessageList(result) if isinstance(result, list) else result

    def __contains__(self, user: User):
        return user in self.d

    def keys(self):
        return self.d.keys()

    def append_to(self, user, msg):
        self.d[user].append(msg)
        self.commit()

    def get(self, user: User) -> Optional[MessageList]:
        return self.d.get(user)

    def to_jsonable_type(self):
        return {
            k: [
                item.to_jsonable_type() if isinstance(item, Message) else item
                for item in v
            ]
            if isinstance(v, list)
            else v.to_jsonable_type()
            for k, v in self.d.items()
        }

    def commit(self) -> None:
        try:
            with open(self.store_path, "w") as f:
                json.dump(self.to_jsonable_type(), f)
                print("wrote file")
        except IOError as e:
            print("couldn't write file", e)
            # in a real app, we'd log
            pass

    def __setitem__(self, k: User, v: MessageList):
        self.d[k] = v
        self.commit()

    def __delitem__(self, user: User):
        del self.d[user]
        self.commit()


class ReplicaSession:
    is_connected: bool
    update_db_handler: Callable[[Db, Optional[float]], Awaitable[Ok]]

    def __init__(self, update_db_handler):
        self.is_connected = False
        self.update_db_handler = update_db_handler

    async def accept(self, db: Db, mtime: Optional[float]) -> Ok:
        print("accepted connection from upstream")
        self.is_connected = True
        return await self.update_db_handler(db, mtime)


@dataclass
class ReplicaInfo:
    next: Optional[jsonrpc.Session]
    tail: list[Address]

    async def forward(self, method: str, *args):
        if self.next is None:
            return
        if not self.next.is_running:
            if len(self.tail) == 0:
                return
            next_addr, *self.tail = self.tail
            next_conn = await asyncio.open_connection(*next_addr)
            self.next = jsonrpc.spawn_session(*next_conn)
            self.next.run_in_background(self.next.run_event_loop())
            await self.next.request(method="register_replica_source", params=[{}, -1])
            return await self.forward(method, *args)
        assert self.next is not None
        await self.next.request(method=method, params=args)


# XXX: This is copy-pasted from [jsonrpc.py].
def run_in_background(pending_jobs, coro: Coroutine[Any, Any, Any]):
    task = asyncio.create_task(coro)
    pending_jobs.add(task)
    # discard this task from pending jobs when done
    task.add_done_callback(pending_jobs.discard)


# We can avoid locks here due to the guarantees of async-await programming.
# In particular, job interleaving can only happen across an [await] boundary,
# so as long as we do all our modifications of [db] in one "breath", there
# should be no issues with another thread seeing an intermediate state.
class State:
    db: Db
    # Invariant: [logins.keys()] is a subset of [db.keys()]
    logins: dict[User, UserSession]
    is_primary: bool
    replica_info: ReplicaInfo
    cfg: config.Config
    addr: Address
    mtime: Optional[float]

    def __init__(
        self,
        cfg: config.Config,
        addr: Address,
        db: Db,
        is_primary: bool,
        replica_info: ReplicaInfo,
        mtime: Optional[float],
    ):
        self.db = db
        self.logins = dict()
        self.is_primary = is_primary
        self.replica_info = replica_info
        self.cfg = cfg
        self.addr = addr
        self.mtime = mtime

    async def forward(self, method: str, *args):
        await self.replica_info.forward(method, *args)

    async def retrieve_pending(self, user: User) -> MessageList:
        await self.forward("retrieve_pending", user)
        return self.db.fetch_pending_msgs(user)

    async def handle_login(self, session: UserSession, user: User) -> MessageList:
        if user not in self.db:
            raise NoSuchUser(user)

        if user in self.logins:
            raise AlreadyLoggedIn(user)

        self.logins[user] = session

        return await self.retrieve_pending(user)

    def handle_logout(self, user: User) -> None:
        del self.logins[user]

    async def store_msg(self, msg) -> Ok:
        if not isinstance(msg, Message):
            msg = Message(msg["sender"], msg["recipient"], msg["content"])
        self.db.append_to(msg.recipient, msg)
        await self.forward("store_msg", msg.to_jsonable_type())

        return Ok()

    async def handle_send_message(self, msg: Message) -> Ok:
        # Send the message to user
        if msg.recipient not in self.db:
            raise NoSuchUser(msg.recipient)

        recipient_session = self.logins.get(msg.recipient)

        if recipient_session is None:
            await self.store_msg(msg)
        else:
            await recipient_session.receive_message(msg)

        return Ok()

    async def create_user(self, name: User) -> Ok:
        if name in self.db:
            raise UserAlreadyExists(name)

        self.db[name] = MessageList([])
        await self.forward("create_user", name)

        return Ok()

    async def list_users(self, *args) -> UserList:
        return UserList(list(self.db.keys()))

    async def delete_user(self, user: User) -> Ok:
        if user in self.db:
            del self.db[user]
        await self.forward("delete_user", user)

        # If it's not there, oh well. The point of [delete_user] is to produce
        # a server state in which the desired user no longer exists, so if that
        # user didn't exist in the first place, cool.
        return Ok()

    async def accept_client(self) -> Ok:
        return Ok()

    async def reject_client(self) -> NoReturn:
        raise ImABackup()

    async def reject_replica_source(self, *args, **kwargs) -> NoReturn:
        raise ImPrimary()

    async def update_db(self, db, mtime: Optional[float]) -> Union[Ok, DbUpdate]:
        if (self.mtime or -1) < (mtime or -1):
            print("upstream reported newer db, updating")
            self.mtime = mtime
            self.db.d = db
            self.db.commit()
            await self.forward("update_db", self.db.d, self.mtime)
            return Ok()
        else:
            print("current db is newer than upstram")
            return DbUpdate(self.db.d, self.mtime)

    async def elect_leader(self) -> None:
        # Ping every server in the up-line. If any responds, that server is the
        # new primary, not us.
        for addr in self.cfg.preceding(self.addr):
            print(f"checking server: {addr}")
            try:
                conn = await asyncio.open_connection(*addr)
                sess = jsonrpc.spawn_session(*conn)
                sess.run_in_background(sess.run_event_loop())
                resp = await sess.request(method="ping", params=[])
                conn[1].close()
                if not resp.is_error:
                    print("got ping, continuing to act as backup")
                    return
            except:  # type: ignore
                pass

        # Only if all preceding servers fail to respond do we become primary.
        print("now acting as primary")
        self.is_primary = True

    async def handle_as_backup(self, session: jsonrpc.Session) -> None:
        replica_session = ReplicaSession(self.update_db)

        session.register_handler("register_replica_source", replica_session.accept)
        session.register_handler("update_db", self.update_db)
        session.register_handler("register_client", self.reject_client)
        session.register_handler("retrieve_pending", self.retrieve_pending)
        session.register_handler("create_user", self.create_user)
        session.register_handler("delete_user", self.delete_user)
        session.register_handler("store_msg", self.store_msg)

        await session.run_event_loop()

        if replica_session.is_connected:
            print("upstream connection lost, checking precedents")
            await self.elect_leader()

    # TODO: the difference between [session] and [user_session] is confusing,
    # come up with better names
    async def handle_as_primary(self, session: jsonrpc.Session) -> None:
        user_session = UserSession(
            session, self.handle_login, self.handle_logout, self.handle_send_message
        )

        session.register_handler("register_replica_source", self.reject_replica_source)
        session.register_handler("register_client", self.accept_client)
        session.register_handler("login", user_session.login)
        session.register_handler("create_user", self.create_user)
        session.register_handler("list_users", self.list_users)
        session.register_handler("delete_user", self.delete_user)
        session.register_handler("send", user_session.send_message)

        await session.run_event_loop()
        user_session.cleanup()

    async def handle_incoming(self, reader, writer) -> None:
        session = jsonrpc.spawn_session(reader, writer)
        session.register_handler("ping", ping)

        if self.is_primary:
            await self.handle_as_primary(session)
        else:
            await self.handle_as_backup(session)


async def main(host: str, port: int):
    cfg = config.load()

    addr = (Host(host), Port(port))

    if addr not in cfg:
        raise ValueError(
            f"refusing to bind to address {host}:{port} not listed in config.json"
        )

    try:
        db_path = SERVER_DB_FORMAT.format(host=host, port=port)
        with open(db_path, "r") as f:
            db, mtime = json.load(f), os.path.getmtime(db_path)
    except FileNotFoundError:
        db, mtime = {}, None

    is_primary = cfg.am_i_primary(addr)
    backups = cfg.following(addr)

    if len(backups) == 0:
        next = None
        tail = []
    else:
        first_backup_addr, *tail = backups
        backup_host, backup_port = first_backup_addr
        next_conn = await asyncio.open_connection(*first_backup_addr)
        next = jsonrpc.spawn_session(*next_conn)
        run_in_background(pending_jobs, next.run_event_loop())
        resp = await next.request(method="register_replica_source", params=[db, mtime])
        if resp.payload != "ok":
            db = resp.payload["db"]  # type: ignore
            mtime = resp.payload["mtime"]  # type: ignore

    db_ = Db(
        db,
        SERVER_DB_FORMAT.format(host=host, port=port),
    )

    db_.commit()

    state = State(
        cfg,
        addr,
        db_,
        is_primary,
        ReplicaInfo(next=next, tail=tail),
        mtime,
    )

    server = await asyncio.start_server(state.handle_incoming, host, port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    # asyncio.run(main("10.250.159.96", 8888))
    asyncio.run(main("localhost", 15251))
