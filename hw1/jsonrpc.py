# An implementation of the JSON-RPC 2.0 protocol, as specified here:
#   https://www.jsonrpc.org/specification

import asyncio
from typing import NewType

RequestId = NewType("RequestId", int)


class Session:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    currId: RequestId
    pending_requests: dict[RequestId, None]

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.currId = RequestId(0)
        self.reader = reader
        self.writer = writer

    async def run_event_loop(self):
        pass
