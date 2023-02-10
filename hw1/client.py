import socket
from jsonrpc import Session
from typing import Optional, List

class Client:

    # initialize Client
    def __init__(self, host, port):
        # make the connection
        client_socket = socket.socket()
        client_socket.connect((host, port))


    # Log in user
    def login(self, user: str) -> Optional[Session]:
        # check that this user exists
        exists = True
        if not exists: 
            return None

        # if does exist, begin Session


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


    # TODO: Deliver undelivered messages to a particular user
    def deliver_undelivered(self, user: str):
        # check that user is logged in
        # if not, don't do anything? or raise exception?
        # if logged in, retrieve and deliver messages
        return None