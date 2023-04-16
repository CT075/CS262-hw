import unittest
import asyncio
from server import State, UserAlreadyExists, UserList, User, MessageList, LoggedIn, NoSuchUser, AlreadyLoggedIn, LoggedOut, Message
import jsonrpc
import client
import warnings
from contextlib import redirect_stdout
import io
import filelib
import json

#python3 -m unittest testing.py

class TestChat(unittest.IsolatedAsyncioTestCase):

    async def setup(self):
        warnings.simplefilter('ignore', category=ResourceWarning)
        state = State()
        serv = await asyncio.start_server(state.handle_incoming, 'localhost', 8877)
        return (state, serv)
    

    ################ TESTING PERSISTENCE & 2-FAULT TOLERANCE ################

    async def test_write_ports(self):
        ports = await filelib.write_ports()
        ports2 = await filelib.read_ports()
        self.assertEqual(ports, ports2)

    async def test_file_write(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        ok = await state.create_user("cam")

        ana = User("ana")
        state.handle_login(None, ana)
        
        result = await state.handle_send_message(Message(ana, User("cam"), "Hello!"))
        self.assertEqual(result.to_jsonable_type(), "ok")
        self.assertEqual(state.known_users.get(User("cam")), LoggedOut(MessageList([Message(ana, User("cam"),"Hello!")])))


        await filelib.write_obj("testdump.txt", 
                                json.dumps(state.to_jsonable_type()))
        dc = await filelib.read_obj("testdump.txt")

        serv.close()
        await serv.wait_closed()


    
    ################## TESTING SERVER ##################

    ### USER CREATION

    async def test_create_user(self):
        state, serv = await self.setup()
        
        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        serv.close()
        await serv.wait_closed()

    
    async def test_create_user_already_exists(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")
        try:
            notok = await state.create_user("ana")
        except jsonrpc.JsonRpcError as e:
            self.assertTrue(isinstance(e, UserAlreadyExists))
            
        serv.close()
        await serv.wait_closed()

    # ### USER LOGIN

    async def test_login_user(self):
        state, serv = await self.setup()
        
        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        result = state.handle_login(None, ana)

        self.assertEqual(result, MessageList([]))
        self.assertEqual(state.known_users.get(ana), LoggedIn(None))

        serv.close()
        await serv.wait_closed()

    async def test_login_nonexistent_user(self):
        state, serv = await self.setup()

        ana = User("ana")
        try:
            state.handle_login(None, ana)
        except jsonrpc.JsonRpcError as e:
            self.assertTrue(isinstance(e, NoSuchUser))

        serv.close()
        await serv.wait_closed()

    async def test_login_user_twice(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        state.handle_login(None, ana)

        try:
            state.handle_login(None, ana)
        except jsonrpc.JsonRpcError as e:
            self.assertTrue(isinstance(e, AlreadyLoggedIn))

        serv.close()
        await serv.wait_closed()

    async def test_login_multiple_users(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ok = await state.create_user("cam")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        state.handle_login(None, ana)
        self.assertEqual(state.known_users.get(ana), LoggedIn(None))

        cam = User("cam")
        state.handle_login(None, cam)
        self.assertEqual(state.known_users.get(cam), LoggedIn(None))

        serv.close()
        await serv.wait_closed()

    ### USER LOGOUT

    async def test_logout(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        state.handle_login(None, ana)
        self.assertEqual(state.known_users.get(ana), LoggedIn(None))

        state.handle_logout(ana)
        self.assertEqual(state.known_users.get(ana), LoggedOut(MessageList([])))

        serv.close()
        await serv.wait_closed()

    async def test_logout_not_logged_in(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        state.handle_logout(ana)
        self.assertEqual(state.known_users.get(ana), LoggedOut(MessageList([])))

        serv.close()
        await serv.wait_closed()

    async def test_login_logout_login(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        state.handle_login(None, ana)
        state.handle_logout(ana)
        state.handle_login(None, ana)
        self.assertEqual(state.known_users.get(ana), LoggedIn(None))

        serv.close()
        await serv.wait_closed()


    ### LIST USERS

    async def test_list_users(self):
        state, serv = await self.setup()
        
        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ok = await state.create_user("cam")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ok = await state.create_user("cat")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        lst = await state.list_users()
        self.assertEqual(lst, UserList(data=['ana', 'cam', 'cat']))
        
        serv.close()
        await serv.wait_closed()

    async def test_list_users_empty(self):
        state, serv = await self.setup()

        lst = await state.list_users()
        self.assertEqual(lst, UserList(data=[]))
        
        serv.close()
        await serv.wait_closed()

    async def test_create_delete_list(self):
        state, serv = await self.setup()
        
        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")
        self.assertTrue("ana" in state.known_users)
        
        okdel = await state.delete_user("ana")
        self.assertEqual(okdel.to_jsonable_type(), "ok")
        self.assertTrue("ana" not in state.known_users)

        lst = await state.list_users()
        self.assertEqual(lst, UserList(data=[]))
        
        serv.close()
        await serv.wait_closed()


    ### USER DELETION

    async def test_delete_user(self):
        state, serv = await self.setup()
        
        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")
        self.assertTrue("ana" in state.known_users)
        
        okdel = await state.delete_user("ana")
        self.assertEqual(okdel.to_jsonable_type(), "ok")
        self.assertTrue("ana" not in state.known_users)

        serv.close()
        await serv.wait_closed()

    async def test_delete_nonexisting_user(self):
        state, serv = await self.setup()
        
        okdel = await state.delete_user("ana")
        self.assertEqual(okdel.to_jsonable_type(), "ok")
        self.assertTrue("ana" not in state.known_users)

        serv.close()
        await serv.wait_closed()

    ### SENDING MESSAGES

    async def test_send_msg_to_nonexisting_user(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        self.assertEqual(ok.to_jsonable_type(), "ok")

        ana = User("ana")
        state.handle_login(None, ana)
        
        try:
            await state.handle_send_message(Message(ana, User("cam"), "Hello!"))
        except jsonrpc.JsonRpcError as e:
            self.assertTrue(isinstance(e, NoSuchUser))

        serv.close()
        await serv.wait_closed()

    async def test_send_msg_to_logged_out_user(self):
        state, serv = await self.setup()

        ok = await state.create_user("ana")
        ok = await state.create_user("cam")

        ana = User("ana")
        state.handle_login(None, ana)
        
        result = await state.handle_send_message(Message(ana, User("cam"), "Hello!"))
        self.assertEqual(result.to_jsonable_type(), "ok")
        self.assertEqual(state.known_users.get(User("cam")), LoggedOut(MessageList([Message(ana, User("cam"),"Hello!")])))

        serv.close()
        await serv.wait_closed()


    ################## TESTING CLIENT ##################

    ### CONNECT AND SETUP

    async def setup_client(self):
        # setup client
        await client.connect('localhost', 8877)
        await client.setup()


    async def test_client_connect_setup(self):
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        self.assertNotEqual(client.session, None)
        self.assertEqual(client.client_user, None)

        await client.close()
        serv.close()
        await serv.wait_closed()

    ### CREATE USER

    async def test_client_create_user(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")
        self.assertIn("successfully", buf.getvalue())

        buf.close()
        
        await client.close()
        serv.close()
        await serv.wait_closed()
    
    async def test_client_create_multiple(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")
        self.assertIn("successfully", buf.getvalue())

        # creating multiple users
        buf.truncate(0)
        with redirect_stdout(buf):
            await client.create_user("cam")
        self.assertIn("successfully", buf.getvalue())

        buf.close()
        
        await client.close()
        serv.close()
        await serv.wait_closed()

    async def test_client_create_existing(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")
        self.assertIn("successfully", buf.getvalue())

        # already existing user
        buf.truncate(0)
        with redirect_stdout(buf):
            await client.create_user("ana")
        self.assertIn("Error", buf.getvalue())

        buf.close()
        
        await client.close()
        serv.close()
        await serv.wait_closed()

    ### LOGIN USER

    async def test_client_login_user(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")

        buf.truncate(0)
        with redirect_stdout(buf):
            await client.login_user("ana")
        self.assertIn("logged in", buf.getvalue())
        
        buf.close()

        await client.close()
        serv.close()
        await serv.wait_closed()

    async def test_client_login_nonexisting(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.login_user("ana")
        self.assertIn("Error", buf.getvalue())
        
        buf.close()
        
        await client.close()
        serv.close()
        await serv.wait_closed()

    ### LIST USERS

    async def test_client_list_users(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")
            await client.create_user("cam")
            await client.create_user("cat")

        buf.truncate(0)
        with redirect_stdout(buf):
            await client.list_accounts("ca*")
        self.assertIn("cat", buf.getvalue())
        self.assertIn("cam", buf.getvalue())
        self.assertNotIn("ana", buf.getvalue())

        buf.close()

        await client.close()
        serv.close()
        await serv.wait_closed()

    async def test_client_list_all(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")
            await client.create_user("cam")
            await client.create_user("cat")

        buf.truncate(0)
        with redirect_stdout(buf):
            await client.list_accounts("*")
        self.assertIn("cat", buf.getvalue())
        self.assertIn("cam", buf.getvalue())
        self.assertIn("ana", buf.getvalue())

        buf.close()

        await client.close()
        serv.close()
        await serv.wait_closed()

    ### DELETE USER

    async def test_client_delete_user(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.create_user("ana")

        buf.truncate(0)
        with redirect_stdout(buf):
            await client.delete_user("ana")
        self.assertIn("successfully", buf.getvalue())

        buf.close()

        await client.close()
        serv.close()
        await serv.wait_closed()

    async def test_client_delete_nonexisting(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.delete_user("ana")
        self.assertIn("successfully", buf.getvalue())
        
        buf.close()

        await client.close()
        serv.close()
        await serv.wait_closed()

    ### SEND MESSAGES

    async def test_client_send_message(self):
        
        # setup server
        state, serv = await self.setup()
        await self.setup_client()

        await state.create_user("ana")
        await state.create_user("cam")

        buf = io.StringIO()
        with redirect_stdout(buf):
            await client.login_user("ana")
        self.assertIn("logged in", buf.getvalue())

        buf.truncate(0)
        with redirect_stdout(buf):
            await client.send("Hello!", "cam")
        self.assertIn("ana to cam: Hello!", buf.getvalue())

        buf.close()

        await client.close()
        serv.close()
        await serv.wait_closed()