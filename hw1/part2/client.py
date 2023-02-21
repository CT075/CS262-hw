# XXX: In this file, we mostly deal with raw python dictionaries instead of the
# structured objects from [server.py]. Maybe we should introduce some
# code in [jsonrpc.py] to fix that.

import asyncio
import grpc
from aioconsole import ainput

from fnmatch import fnmatch
from typing import Any, Optional

from chat_pb2 import User, Ok, SessionToken, SendRequest, Msg
import chat_pb2_grpc

# Design decision: we do not need a client class,
# because we will simply start up new clients by running the
# file multiple times. Since a client doesn't have much internal
# state (unlike a server), there's no need for a client class.

# Client keeps track of the user that is logged in
client_user: Optional[User] = None
tok: Optional[SessionToken] = None
stub: Any
message_loop: Optional[asyncio.Task] = None


# Connect to server
def connect(host: str, port: int):
    global stub
    # start a session with the server
    chan = grpc.aio.insecure_channel("%s:%s" % (host, port))
    stub = chat_pb2_grpc.ChatSessionStub(chan)


# Send login request to server
async def login_user(user: User):
    global client_user
    global stub
    global tok
    if client_user is not None:
        print("Cannot login more than one user.\n")
        return

    # send the request to server-side login method, with specified parameters
    result = await stub.Login(user)

    # if the result is an error, print error message
    if result.HasField("err"):
        print("Error logging in user " + user.handle + ": " + result.err.msg + ".\n")
        return

    assert result.HasField("ok")

    client_user = user
    print("User " + user.handle + " is now logged in.\n")
    tok = result.ok

    async def run():
        async for msg in stub.IncomingMsgs(tok):
            print(msg.sender.handle + ": " + msg.text + "\n")

    global message_loop
    # we don't need to clean this up because it will run until client exit
    message_loop = asyncio.create_task(run())


# Send a create account request to server
async def create_user(user: User):
    global stub
    # send the request to server-side create_user method, with specified parameters
    result = await stub.Create(user)
    # if server gives error, print it
    if result.HasField("err"):
        print("Error creating user " + user.handle + ": " + result.err.msg + ".\n")
    # if server confirms, display success message
    elif result.HasField("ok"):
        print("New user " + user.handle + " created successfully.\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send list accounts request to server
async def list_accounts(filter: str):
    global stub
    result = await stub.ListUsers(Ok())
    lst = result.users
    filtered = [u if fnmatch(u, filter) else "" for u in lst]
    while "" in filtered:
        filtered.remove("")
    if len(filtered) == 0:
        print("No accounts matching this filter.")
    else:
        print("Accounts matching filter " + filter + ":")
        for name in filtered:
            print(name)


# Send message send request to server
async def send(msg: str, user: User):
    global stub
    global client_user
    global tok

    if tok is None or client_user is None:
        print("You must be logged in to send messages")
        return

    result = await stub.SendMsg(
        SendRequest(msg=Msg(text=msg, sender=client_user, recipient=user), tok=tok)
    )

    # if server gives error, print it
    if result.HasField("err"):
        print("Error sending message: " + result.err.msg + ".\n")
    # if server confirms, display the message that was sent
    elif result.HasField("ok"):
        print(client_user.handle + " to " + user.handle + ": " + msg + "\n")
    else:
        # this should not happen
        print("Something went wrong. Please try again.\n")


# Send delete account request to server
async def delete_user(user: User):
    global stub
    await stub.DeleteUser(user)
    print("User " + user.handle + " successfully deleted.\n")


# Close the socket connection client-side
async def close():
    global writer
    writer.close()
    await writer.wait_closed()


# in main, do the connect and setup and UI
async def main(host: str, port: int) -> None:
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

    # take await ainput from user
    while True:
        inp = await ainput(">>>  ")
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
                await create_user(User(handle=u))
        # logging in a user
        elif action == "login":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                await login_user(User(handle=u))
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
                msgtxt = await ainput("Please input the message below:\n")
                await send(msgtxt, User(handle=u))
        # delete user
        elif action == "delete":
            if len(tokens) < 2:
                print("Missing argument: username.\n")
            else:
                u = tokens[1]
                await delete_user(User(handle=u))
        elif action == "bye":
            await close()
            print("Goodbye!\n")
            break


if __name__ == "__main__":
    asyncio.run(main("localhost", 8888))
