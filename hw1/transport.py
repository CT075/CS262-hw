import struct
import asyncio
from collections import defaultdict
from typing import NewType, DefaultDict, Callable, Awaitable

MsgId = NewType("MsgId", int)

# 4 bytes
MAX_MSG_SIZE = 2 << 32
MAX_ID = 2 << 32

# > = big endian
# l = 4 bytes (size)
# l = 4 bytes (id)
# b = 1 byte (more?)
HEADER_FORMAT = ">llb"
HEADER_SIZE = 4 + 4 + 1


def format_header(*, size: int, id: MsgId, more: bool):
    return struct.pack(HEADER_FORMAT, (size, id, more))


def increment_msgid(id: MsgId) -> MsgId:
    return MsgId((id + 1) % MAX_ID)


class Session:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    curr_id: MsgId
    pending_msgs: DefaultDict[MsgId, bytes]
    handle: Callable[[bytes], Awaitable[None]]

    def __init__(self, reader, writer, handle):
        self.currId = MsgId(0)
        self.reader = reader
        self.writer = writer
        self.pending_msgs = defaultdict(bytes)
        self.handle = handle

    def fresh_id(self) -> MsgId:
        prev = self.currId
        self.curr_id = increment_msgid(self.curr_id)
        return prev

    async def send(self, s: bytes) -> None:
        msg_id = self.fresh_id()

        for i in range(0, len(s), MAX_MSG_SIZE):
            chunk = s[i : i + MAX_MSG_SIZE]
            more = bool(s[i + MAX_MSG_SIZE :])
            header = format_header(size=len(chunk), id=msg_id, more=more)
            packet = header + chunk
            self.writer.write(packet)
            await self.writer.drain()

    async def recv_single(self) -> None:
        header = await self.reader.read(HEADER_SIZE)
        size, id, more = struct.unpack(HEADER_FORMAT, header)
        chunk = await self.reader.read(size)
        id = MsgId(id)
        self.pending_msgs[id] += chunk
        if not more:
            msg = self.pending_msgs[id]
            del self.pending_msgs[id]
            await self.handle(msg)
