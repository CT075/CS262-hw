import asyncio
from typing import Optional, List, NewType
from jsonrpc import spawn_session, Session
from server import Response, MessageList, Ok, UserList, Message
import jsonrpc
from fnmatch import fnmatch

User = NewType("User", str)

# Design decision: we do not need a client class,
# because we will simply start up new clients by running the 
# file multiple times. Since a client doesn't have much internal 
# state (unlike a server), there's no need for a client class.

# Client keeps track of the session it has going with server
# and of the user that is logged in
session: Session
client_user: Optional[User]


# Connect to server
async def connect(self, host: str, port: int):
    # connect to the socket and start a session with the server
    reader, writer = await asyncio.open_connection(self.host, self.port)
    self.session = spawn_session(reader, writer)
        

# Send login request to server
async def login_user(self, user: User):
    # send the request to server-side login method, with specified parameters
    params = [user]
    result = await self.session.request("login", params)
    # if the result is an error, print error message
    if (result.is_error):
        print("Error logging in user " + user + ".\n")
    # otherwise, print that user is logged in
    # and display pending messages
    elif isinstance(result.payload, MessageList):
        print("User " + user + " is now logged in.\n")
        pending = [m.sender + ": " + m.content for m in result.payload]
        for msg in pending:
            print(msg + "\n")
    else:
        # this should not happen
        print("Cannot display pending messages.\n")


# Send a create account request to server
async def create_user(self, user: User):
    # send the request to server-side create_user method, with specified parameters
    params = [user]
    result = await self.session.request("create_user", params)
    # if server gives error, print it
    if (result.is_error):
        print("Error creating user" + user + ".\n")
    # if server confirms, display success message
    elif isinstance(result.payload, Ok):
        print("New user " + user + " created successfully.\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send list accounts request to server
async def list_accounts(self, filter: str):
    result = await self.session.request("list_users", [])
    # if server gives error, print it
    if (result.is_error):
        print("Error listing accounts.\n")
    # if server confirms, print the filtered account names
    elif isinstance(result.payload, UserList):
        print("Accounts matching filter " + filter + ":\n")
        filtered = [u if fnmatch(u, filter) else "" for u in result.payload]
        for name in filtered:
            print(name + "\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send message send request to server
async def send(self, msg: Message, user: User):
    params = [msg, user]
    result = await self.session.request("send", params)
    # if server gives error, print it
    if (result.is_error):
        print("Error sending message.\n")
    # if server confirms, display the message that was sent
    elif isinstance(result.payload, Ok):
        print(client_user + " to " + user + ": " + msg + "\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")

# Send delete account request to server
async def delete_user(self, user: User):
    params = [user]
    result = await self.session.request("delete_user", params)
    # if server gives error, print it
    if (result.is_error):
        print("Error deleting user " + user + ".\n")
    # if server confirms, display the message that was sent
    elif isinstance(result.payload, Ok):
        print("User " + user + " successfully deleted.\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Receive and display messages for user
def receive_message(user: str, m: Message):
    print(m.sender + ": " + m.content + "\n")
    

async def setup(self):
    # listen for messages from server
    self.session.register_handler("receive_message", self.receive_message)
    await self.session.run_event_loop()


# in main, do the connect and setup and UI
# TODO