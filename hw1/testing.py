import unittest
import asyncio
from server import State, UserAlreadyExists, UserList, User, MessageList, LoggedIn, NoSuchUser, AlreadyLoggedIn, LoggedOut, Message
import jsonrpc

#python3 -m unittest testing.py

class TestChat(unittest.IsolatedAsyncioTestCase):

    async def setup(self):
        state = State()
        serv = await asyncio.start_server(state.handle_incoming, 'localhost', 8888)
        return (state, serv)
    
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

    ### USER LOGIN

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


    ### FUN COMBINATIONS
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

    ################## TESTING CLIENT ##################