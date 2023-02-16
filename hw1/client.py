import asyncio
from typing import Optional, List, NewType
from jsonrpc import spawn_session, Session, Response
from server import MessageList, UserList, Message
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
writer: asyncio.StreamWriter


# Connect to server
async def connect(host: str, port: int):
    global session
    global writer
    # connect to the socket and start a session with the server
    reader, writer = await asyncio.open_connection(host, port)
    session = spawn_session(reader, writer)


# Send login request to server
async def login_user(user: User):
    # send the request to server-side login method, with specified parameters
    params = [user]
    result = await session.request("login", params)
    # if the result is an error, print error message
    if result.is_error:
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
async def create_user(user: User):
    # send the request to server-side create_user method, with specified parameters
    params = [user]
    result = await session.request(method="create_user", params=params)
    # if server gives error, print it
    if result.is_error:
        print("Error creating user" + user + ".\n")
    # if server confirms, display success message
    elif result.payload == "ok":
        print("New user " + user + " created successfully.\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send list accounts request to server
async def list_accounts(filter: str):
    result = await session.request("list_users", [])
    # if server gives error, print it
    if result.is_error:
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
async def send(msg: Message, user: User):
    params = [msg, user]
    result = await session.request("send", params)
    # if server gives error, print it
    if result.is_error:
        print("Error sending message.\n")
    # if server confirms, display the message that was sent
    elif result.payload == "ok":
        print(client_user + " to " + user + ": " + msg + "\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send delete account request to server
async def delete_user(user: User):
    params = [user]
    result = await session.request("delete_user", params)
    # if server gives error, print it
    if result.is_error:
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


# Set up the event loop and handlers for requests from server
async def setup():
    global session
    # listen for messages from server
    session.register_handler("receive_message", receive_message)
    session.run_in_background(session.run_event_loop())


# Close the socket connection client-side
async def close():
    writer.close()
    await writer.wait_closed()


# in main, do the connect and setup and UI
async def main(host: str, port: int):
    print("Welcome to the chat!\n")
    # connect to server
    await connect(host, port)
    print("Connected to server.\n")
    # setup the event loop and handlers
    await setup()

    # take input from user
    while True:
        inp = input("Enter action below:\n")
        tokens = inp.split()

        # if no action specified, loop again
        if len(tokens) < 1:
            print("No action specified.\n")
            continue

        # handle user specified actions
        action = tokens[0]
        if action == "create":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                await create_user(User(u))
        if action == "bye":
            close()


if __name__ == "__main__":
    asyncio.run(main("localhost", 8888))
