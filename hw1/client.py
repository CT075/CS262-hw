import asyncio
from jsonrpc import spawn_session, Session
from typing import Optional, List


class Client:
    session: Optional[Session]
    host: str
    port: int

    # initialize Client
    def __init__(self, host, port) -> None:
        # make the connection
        self.host = host
        self.port = port
        self.session = None

    # Open connection and start jsonrpc session
    async def connect(self):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        self.session = spawn_session(reader, writer)

    # Send login request to server
    # TODO: this return type seems out of date
    async def login_user(self, user: str) -> Optional[Session]:
        params = [user]
        result = await self.session.request("login_user", params)
        # TODO: is the result just a server Response?
        # could it be anything else? 
        return None

    # Send a create account request to server
    async def create_user(self, user: str):
        params = [user]
        result = await self.session.request("create_user", params)

    # Send list accounts request to server
    async def list_accounts(self, filter) -> List[str]:
        params = [filter]
        result = await self.session.request("list_accounts", params)
        # placeholder
        return []

    # Send message send request to server
    async def send(self, msg: str, user: str):
        params = [msg, user]
        result = await self.session.request("send", params)

    # Send delete account request to server
    async def delete_user(self, user: str):
        params = [user]
        result = await self.session.request("delete_user", params)
