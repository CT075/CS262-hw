import asyncio
from typing import Optional, List, NewType

from jsonrpc import spawn_session, Session

User = NewType("User", str)

# client has to know what user is logged in
# client wants to know what session with server



class Client:
    session: Optional[Session]
    host: str
    port: int

    # initialize Client
    # connect to socket
    # start session
    # main takes the host and port
    def __init__(self, host, port) -> None:
        # make the connection
        self.host = host
        self.port = port
        self.session = None

    # Open connection and start jsonrpc session
    async def connect(self):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        self.session = spawn_session(reader, writer)
        # start event loop

    # Send login request to server
    # TODO: this return type seems out of date
    async def login_user(self, user: str):
        params = [user]
        result = await self.session.request("login", params)
        # check if instance of response
        # if we have error: print error
        # if instance of ok: print user is logged in
        # nvm: u actually get list of pending messages if ok
        # print them

    # Send a create account request to server
    async def create_user(self, user: str):
        params = [user]
        result = await self.session.request("create_user", params)
        # check if instance of response
        # if we have error: print error
        # if instance of ok: print user is logged in

    # Send list accounts request to server
    async def list_accounts(self, filter):
        params = [filter]
        result = await self.session.request("list_accounts", params)
        # check if instance of response
        # if we have error: print error
        # if instance of ok: filter ca* -> cameron, cat, not ana,
        # print accts


    # Send message send request to server
    async def send(self, msg: str, user: str):
        params = [msg, user]
        result = await self.session.request("send", params)
        # check if instance of response
        # if we have error: print error
        # if instance of ok: print user is logged in

    # Send delete account request to server
    async def delete_user(self, user: str):
        params = [user]
        result = await self.session.request("delete_user", params)
        # check if instance of response
        # if we have error: print error
        # if instance of ok: print user is logged in

    # getting message while you're logged in
    def receive_message(user: str, m: str):
        return None
    
    async def setup(self):
        self.session.register_handler("receive_message", self.delete_user)
        await self.session.run_event_loop()

    # in main, just connect and setup