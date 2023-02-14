import asyncio
from jsonrpc import spawn_session, Session
from typing import Optional, List

class Server:
    session: Optional[Session]
    host: str
    port: int

    # initialize Server
    def __init__(self, host, port) -> None:
        # make the connection
        self.host = host
        self.port = port
        self.session = None

    # Log in user
    def login_user(self, user: str) -> Optional[Session]:
        # check that this user exists
        exists = True
        if not exists:
            return None
        # if does exist, login and deliver undelivered messages

    # Create a new account with a unique user name
    # TODO: return type
    def create(self, user: str):
        # check that the user is unique
        unique = True
        if not unique:
            return None

        # if unique, create user

    # List all accounts or subset
    def list(self, filter) -> List[str]:
        # retrieve and filter the accounts
        accounts = []
        return accounts

    # Send the message to user
    # TODO: return type
    def send(self, msg: str, user: str):
        # if user does not exist, return error
        user_exists = True
        if not user_exists:
            raise ValueError("The user " + user + " does not exist.")

        # if user logged in, deliver immediately
        # if not logged in, queue msg and deliver on demand

    # Delete an account
    def delete(self, user: str):
        # handle undelivered messages
        # delete user
        return None