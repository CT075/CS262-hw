import struct
import asyncio
from typing import NewType

MsgId = NewType("MsgId", int)

# 4 bytes
MAX_MSG_SIZE = 2 << 32
MAX_ID = 2 << 32


def format_size(size: int) -> bytes:
    if size > MAX_MSG_SIZE or size < 0:
        raise ValueError
    # little-endian
    return struct.pack("<l", size)


def unformat_size(t: bytes) -> int:
    return struct.unpack("<l", t)[0]  # type: ignore


def increment_msgid(id: MsgId) -> MsgId:
    return MsgId((id + 1) % MAX_ID)


def format_msgid(id: MsgId) -> bytes:
    return struct.pack("<l", id)


def unformat_msgid(t: bytes) -> MsgId:
    return MsgId(struct.unpack("<l", t))[0]  # type: ignore


class Session:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    curr_id: MsgId

    def __init__(self, reader, writer):
        self.currId = MsgId(0)
        self.reader = reader
        self.writer = writer

    def fresh_id(self) -> MsgId:
        prev = self.currId
        self.curr_id = increment_msgid(self.curr_id)

        return prev

    async def send(self, s: bytes):
        msg_id = self.fresh_id()

        async def send_impl(s):
            size = min(len(s), MAX_MSG_SIZE)
            packet = format_size(size) + format_msgid(msg_id) + s[:size]
            self.writer.write(packet)
            await self.writer.drain()

            if size < len(s):
                await send_impl()

        await send_impl(s)
