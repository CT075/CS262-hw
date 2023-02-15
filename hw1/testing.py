import unittest
import asyncio
from transport import Session, MsgId

#class TestTransport(unittest.IsolatedAsyncioTestCase):

    #async def test_session_fresh_id(self):
        # make a writer directly instead of open connection
        # ses = Session(reader, writer)
        # self.assertEqual(ses.curr_id, MsgId(0))
        # self.assertEqual(ses.fresh_id, MsgId(1))