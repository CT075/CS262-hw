# XXX: In this file, we mostly deal with raw python dictionaries instead of the
# structured objects from [server.py]. Maybe we should introduce some
# deserialization code in [jsonrpc.py] to fix that.

import asyncio
from typing import Optional, NewType, Any
from jsonrpc import spawn_session, Session
from fnmatch import fnmatch
from server import Message

User = NewType("User", str)

# Design decision: we do not need a client class,
# because we will simply start up new clients by running the
# file multiple times. Since a client doesn't have much internal
# state (unlike a server), there's no need for a client class.

# Client keeps track of the session it has going with server
# and of the user that is logged in
session: Session
client_user: Optional[User] = None
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
    global client_user
    if client_user != None:
        print("Cannot login more than one user.\n")
        return

    # send the request to server-side login method, with specified parameters
    params = [user]
    result = await session.request(method="login", params=params)
    # if the result is an error, print error message
    if result.is_error:
        print(
            "Error logging in user " + user + ": " + result.payload["message"] + ".\n"
        )
    # otherwise, print that user is logged in
    # and display pending messages
    elif isinstance(result.payload, list):
        print("User " + user + " is now logged in.\n")
        client_user = user
        pending = [m["sender"] + ": " + m["content"] for m in result.payload]
        if len(pending) == 0:
            print("You have no messages.\n")
        else:
            print("You have the following messages:\n")
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
        print("Error creating user " + user + ": " + result.payload["message"] + ".\n")
    # if server confirms, display success message
    elif result.payload == "ok":
        print("New user " + user + " created successfully.\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send list accounts request to server
async def list_accounts(filter: str):
    result = await session.request(method="list_users", params=[])
    # if server gives error, print it
    if result.is_error:
        print("Error listing accounts: " + result.payload["message"] + ".\n")
    # if server confirms, print the filtered account names
    elif isinstance(result.payload, list):
        lst = result.payload
        filtered = [u if fnmatch(u, filter) else "" for u in lst]
        while "" in filtered:
            filtered.remove("")
        if len(filtered) == 0:
            print("No accounts matching this filter.")
        else:
            print("Accounts matching filter " + filter + ":")
            for name in filtered:
                print(name)
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send message send request to server
async def send(msg: str, user: User):
    global client_user
    params = [msg, user]
    result = await session.request(method="send", params=params)
    # if server gives error, print it
    if result.is_error:
        print("Error sending message: " + result.payload["message"] + ".\n")
    # if server confirms, display the message that was sent
    elif result.payload == "ok":
        print(client_user + " to " + user + ": " + msg + "\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send delete account request to server
async def delete_user(user: User):
    params = [user]
    result = await session.request(method="delete_user", params=params)
    # if server gives error, print it
    if result.is_error:
        print("Error deleting user " + user + ": " + result.payload["message"] + ".\n")
    # if server confirms, display the message that was sent
    elif result.payload == "ok":
        print("User " + user + " successfully deleted.\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Receive and display messages for user
def receive_message(user: str, m: dict[str, Any]):
    print(m["sender"] + ": " + m["content"] + "\n")


# Set up the event loop and handlers for requests from server
async def setup():
    global session
    # listen for messages from server
    session.register_handler("receive_message", receive_message)
    session.run_in_background(session.run_event_loop())


# Close the socket connection client-side
async def close():
    global writer, session, client_user
    session = None
    client_user = None
    writer.close()
    await writer.wait_closed()


# in main, do the connect and setup and UI
async def main(host: str, port: int):
    global client_user
    print(
        "//////////////////////////////////////////////////////////\n"
        "//                                                      //\n"
        "//                Welcome to the chat!                  //\n"
        "//                                                      //\n"
        "//  The following actions are available to you:         //\n"
        "//                                                      //\n"
        "//  To create a new user with a unique username,        //\n"
        "//    type 'create' followed by the username.           //\n"
        "//                                                      //\n"
        "//  To login a user, type 'login' followed by the       //\n"
        "//    username.                                         //\n"
        "//                                                      //\n"
        "//  To list usernames matching a filter, type 'list'    //\n"
        "//    followed by a string filter where the symbol *    //\n"
        "//    can replace any number of symbols. For example,   //\n"
        "//    ca* will match cat, catherine, and cation, but    //\n"
        "//    not dog.                                          //\n"
        "//                                                      //\n"
        "//  To send a message to a user, type 'send' followed   //\n"
        "//    by the username. This will generate another       //\n"
        "//    prompt where you should type your message.        //\n"
        "//                                                      //\n"
        "//  To delete a user, type 'delete' followed by the     //\n"
        "//    username.                                         //\n"
        "//                                                      //\n"
        "//            That's all! Enjoy responsibly :)          //\n"
        "//                                                      //\n"
        "//////////////////////////////////////////////////////////\n"
    )
    # connect to server
    await connect(host, port)
    print("Connected to server.\n")
    # setup the event loop and handlers
    await setup()

    # take input from user
    while True:
        inp = input(">>>  ")
        tokens = inp.split()

        # if no action specified, loop again
        if len(tokens) < 1:
            print("No action specified.\n")
            continue

        # handle user specified actions below
        action = tokens[0]
        if len(tokens) > 2:
            print("Too many arguments specified.\n")
            continue
        # creating new user
        if action == "create":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                await create_user(User(u))
        # logging in a user
        elif action == "login":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                await login_user(User(u))
        # listing users that match filter
        elif action == "list":
            if len(tokens) < 2:
                # assume they want all accounts listed
                await list_accounts("*")
            else:
                filter = tokens[1]
                await list_accounts(filter)
            print("\n")
        # sending a message to user
        elif action == "send":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                msgtxt = input("Please input the message below:\n")
                await send(msgtxt, User(u))
        # delete user
        elif action == "delete":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                await delete_user(User(u))
        elif action == "bye":
            await close()
            print("Goodbye!\n")
            break


if __name__ == "__main__":
    asyncio.run(main("localhost", 8888))
