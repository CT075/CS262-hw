# An implementation of (a subset of) the JSON-RPC 2.0 protocol, as specified
# here:
#   https://www.jsonrpc.org/specification
#
# Simplifying differences:
#  - The parameter list is required

import asyncio
import json
from collections.abc import Coroutine
from typing import NewType, Optional, Any, Callable, TypeVar, Generic
from typing_extensions import Protocol

import transport


# TODO: this should live somewhere else
class Serializeable(Protocol):
    def serialize(self) -> str:
        ...


RequestId = NewType("RequestId", int)

# Calculate the next request ID
def increment_requestid(id: RequestId) -> RequestId:
    return RequestId(id + 1)

# This class formats each client request as a string,
# according to jsonrpc format
class Request:
    # Each request has an id,
    # a server-side method it is referencing,
    # and a list of parameters to that method
    id: Optional[RequestId]
    method: str
    params: list[Serializeable]

    # Initialize the request
    def __init__(self, *, method, params=[], id=None):
        self.method = method
        self.params = params
        self.id = id

    # Convert this request to jsonrpc format
    def serialize(self) -> str:
        # first, collect the data into a dictionary
        t: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
        }
        # set the request ID if it exists
        if self.id is not None:
            t["id"] = self.id
        # then, convert the dictionary to a string
        return json.dumps(t)

    # Is this request a notification?
    # (notifications do not have IDs)
    def is_notification(self) -> bool:
        return self.id is None

# This class formats exceptions as a string,
# according to jsonrpc format
class JsonRpcError(Exception):
    # TODO: Each error has a code ...
    code: int
    message: str
    data: Any

    # Initialize the error
    def __init__(self, *, code, message, data):
        self.code = code
        self.message = message
        self.data = data

    # Convert this error to jsonrpc format 
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

    def __init__(
        self, *, id: Optional[RequestId], payload: Serializeable, is_error: bool
    ):
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


class NoSuchEndpointError(JsonRpcError):
    message = "no such method exists"

    def __init__(self, method):
        super().__init__(code=404, message=self.message, data=method)


class NoSuchRequest(JsonRpcError):
    message = "received response to nonexistent request"

    def __init__(self, data):
        # http 402 is technically [payment required] but these aren't real
        # http errors anyway so lol
        super().__init__(code=402, message=self.message, data=data)


T = TypeVar("T")


# XXX: This probably shouldn't live here.
# asyncio sucks for not having this builtin
class Ivar(Generic[T]):
    ev: asyncio.Event
    t: T

    def __init__(self):
        self.ev = asyncio.Event()
        # We explicitly do not set [self.t] here; it should be set by [fill]
        # only.

    async def read(self) -> T:
        await self.ev.wait()
        return self.t

    def fill(self, val: T):
        self.t = val
        self.ev.set()

    # This is technically wrong -- if [T] is itself an [Optional], the caller
    # can't distinguish "unfilled" from "filled with None". However, as this is
    # not a general-purpose library, whatever.
    def peek(self) -> Optional[T]:
        if self.ev.is_set():
            return self.t
        return None


class Session:
    session: transport.Session
    currId: RequestId
    # In python 3.11, we can use [asyncio.TaskGroup] for this. However, we will
    # do the bookkeeping ourselves for this assignment for ease of portability.
    pending_jobs: set[asyncio.Task]
    pending_requests: dict[RequestId, Ivar]
    handlers: dict[str, Callable[..., Coroutine[None, None, Serializeable]]]

    def __init__(self, session):
        self.currId = RequestId(0)
        self.session = session

    def run_in_background(self, coro: Coroutine[..., ..., ...]):
        task = asyncio.create_task(coro)
        self.pending_jobs.add(task)
        task.add_done_callback(self.pending_jobs.discard)

    async def report_error_nofail(self, error: JsonRpcError) -> None:
        resp = Response(id=None, payload=error, is_error=True)
        try:
            await self.session.send(
                resp.serialize().encode(encoding=transport.STRING_ENCODING)
            )
        except Exception:
            # in a real application, we would log here
            return

    async def handle_and_respond(self, req: Request) -> None:
        if req.method not in self.handlers:
            await self.report_error_nofail(NoSuchEndpointError(req.method))
            return
        try:
            result = await self.handlers[req.method](*req.params)
            success = True
        except JsonRpcError as e:
            result = e
            success = False

        if req.is_notification():
            return

        # This [id=req.id] is a bit cheeky. The meaning of [None] in [req.id]
        # is different from [None] in [resp.id], but we know that [req.id]
        # isn't None because of the [req.is_notification] guard above, so we
        # can just satisfy the typechecker without unwrapping.
        resp = Response(id=req.id, payload=result, is_error=not success)
        await self.session.send(
            resp.serialize().encode(encoding=transport.STRING_ENCODING)
        )

    def handle(self, req: Request) -> None:
        self.run_in_background(self.handle_and_respond(req))

    def fresh_id(self) -> RequestId:
        prev = self.currId
        self.currId = increment_requestid(self.currId)
        return prev

    async def request(self, *, method, params, is_notification=False) -> Any:
        if is_notification:
            wait_for_resp = False
            id = None
        else:
            wait_for_resp = True
            id = self.fresh_id()
            result_box: Ivar[Any] = Ivar()
            self.pending_requests[id] = result_box

        req = Request(method=method, params=params, id=id)
        await self.session.send(req.serialize().encode(transport.STRING_ENCODING))

        if wait_for_resp:
            result = await result_box.read()
            # included only to make mypy accept that [wait_for_resp] implies
            # [id is not None]
            assert id is not None
            del self.pending_requests[id]
            return result

    async def run_event_loop(self) -> None:
        async for payload in self.session:
            obj = json.loads(payload)
            if isinstance(obj, dict):
                if "method" in obj:
                    try:
                        req = Request(**obj)
                        self.handle(req)
                    except ValueError:
                        self.run_in_background(
                            self.report_error_nofail(BadRequestError(obj))
                        )
                elif "id" in obj:
                    try:
                        resp = Response(**obj)
                    except ValueError:
                        self.run_in_background(
                            self.report_error_nofail(BadRequestError(obj))
                        )
                    else:
                        if resp.id is None:
                            # in a real app: log
                            continue
                        if resp.id not in self.pending_requests:
                            self.run_in_background(
                                self.report_error_nofail(NoSuchRequest(obj))
                            )
                            continue
            else:
                self.run_in_background(self.report_error_nofail(BadRequestError(obj)))


def spawn_session(reader, writer) -> Session:
    sess = transport.Session(reader, writer)
    return Session(sess)
