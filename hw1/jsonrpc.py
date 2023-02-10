# An implementation of (a subset of) the JSON-RPC 2.0 protocol, as specified
# here:
#   https://www.jsonrpc.org/specification
#
# Simplifying differences:
#  - The parameter list is required

import asyncio
import json
from typing import NewType, Optional, Any, Callable, Awaitable
from typing_extensions import Protocol

import transport

# TODO: this should live somewhere else
class Serializeable(Protocol):
    def serialize(self) -> str:
        ...


RequestId = NewType("RequestId", int)


def increment_requestid(id: RequestId) -> RequestId:
    return RequestId(id + 1)


class Request:
    method: str
    params: list[str]
    id: Optional[int]

    def __init__(self, *, method, params=None, id=None):
        self.method = method
        self.params = params
        self.id = id

    def serialize(self) -> str:
        t: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
        }
        if self.id is not None:
            t["id"] = self.id
        return json.dumps(t)

    def is_notification(self) -> bool:
        return self.id is None


class JsonRpcError:
    code: int
    message: str
    data: Any

    def __init__(self, *, code, message, data):
        self.code = code
        self.message = message
        self.data = data

    def serialize(self) -> str:
        t: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }
        return json.dumps(t)


class Response:
    id: Optional[RequestId]
    payload: Serializeable
    is_error: bool

    def __init__(self, *, id: RequestId, payload: Serializeable, is_error: bool):
        self.id = id
        self.payload = payload
        self.is_error = is_error

    def serialize(self) -> str:
        t: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.id,
        }
        if self.is_error:
            t["error"] = self.payload.serialize()
        else:
            t["result"] = self.payload.serialize()

        return json.dumps(t)


class BadRequestError(JsonRpcError):
    message = "bad request"

    def __init__(self, data):
        super().__init__(code=400, message=self.message, data=data)


class Session:
    session: transport.Session
    currId: RequestId
    # In python 3.11, we can use [asyncio.TaskGroup] for this. However, we will
    # do the bookkeeping ourselves for this assignment for ease of portability.
    pending_jobs: set[asyncio.Task]
    handlers: dict[str, Callable[..., Awaitable[Any]]]

    def __init__(self, session):
        self.currId = RequestId(0)
        self.session = session

    async def handle(self, req: Request) -> Awaitable[None]:
        if req.method not in self.handlers:
            # TODO
            pass
        # TODO: mypy complains about this; figure out why
        task = asyncio.create_task(self.handlers[req.method](*req.params))
        self.pending_jobs.add(task)
        task.add_done_callback(self.pending_jobs.discard)

    async def run_event_loop(self) -> None:
        async for payload in self.session:
            obj = json.loads(payload)
            if isinstance(obj, dict):
                req = Request(**obj)
                await self.handle(req)
            else:
                # TODO
                pass
