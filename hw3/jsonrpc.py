# An implementation of (a subset of) the JSON-RPC 2.0 protocol, as specified
# here:
#   https://www.jsonrpc.org/specification
#
# Simplifying differences:
# - Requests must have a `params` field containing a list; unitary endpoints
#   should be passed an empty list. Keyword arguments are disallowed.
# - The `id` field will never contain a NULL value.
# - Batch requests are disallowed.

import asyncio
import json
from collections.abc import Coroutine
from typing import NewType, Optional, Any, Callable, TypeVar, Generic
from typing_extensions import Protocol

import transport


# It is apparently well-known that mypy cannot express the type of "things that
# can be json-serialized", so we have to write wrapper objects and define
# [to_jsonable_type] ourselves. If this were a real application with performance
# concerns, we'd want to avoid the extra indirection by turning the typechecker
# off at these points.
# TODO: this should live somewhere else
class Jsonable(Protocol):
    def to_jsonable_type(self) -> Any:
        ...


RequestId = NewType("RequestId", int)


# Calculate the next request ID
def increment_requestid(id: RequestId) -> RequestId:
    return RequestId(id + 1)


# JSON-RPC 2.0 Request schema
class Request:
    # Each request has:
    # - id,
    # - a server-side method it is referencing
    # - a list of parameters to that method
    id: Optional[RequestId]
    method: str
    params: list[Jsonable]

    # Initialize the request
    def __init__(self, *, method, params, id):
        self.method = method
        self.params = params
        self.id = id

    # Convert this request to jsonrpc format
    def serialize(self) -> Any:
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


def parse_request(obj) -> Request:
    if "method" not in obj or "params" not in obj:
        raise ValueError
    if "id" in obj:
        id = obj["id"]
    else:
        id = None
    return Request(method=obj["method"], params=obj["params"], id=id)


# All errors that can be reported across the network should inherit from this
# class.
class JsonRpcError(Exception):
    code: int
    message: str
    data: Any

    # Initialize the error
    def __init__(self, *, code, message, data):
        self.code = code
        self.message = message
        self.data = data

    # Convert this error to jsonrpc format
    def to_jsonable_type(self) -> Any:
        t: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }
        return t


# JSON-RPC 2.0 Response schema
class Response:
    # Each response has:
    # - ID
    # - data sent by server
    # - error marker
    id: Optional[RequestId]
    payload: Jsonable
    is_error: bool

    # Initialize response
    def __init__(self, *, id: Optional[RequestId], payload: Jsonable, is_error: bool):
        self.id = id
        self.payload = payload
        self.is_error = is_error

    # Convert this response to jsonrpc format
    def serialize(self) -> str:
        t: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.id,
        }
        # mark payload as error data or result data
        if self.is_error:
            t["error"] = self.payload.to_jsonable_type()
        else:
            t["result"] = self.payload.to_jsonable_type()

        return json.dumps(t)


def parse_response(obj) -> Response:
    if "id" not in obj:
        raise ValueError

    if "result" in obj:
        if "error" in obj:
            raise ValueError
        return Response(id=obj["id"], payload=obj["result"], is_error=False)

    if "error" in obj:
        return Response(id=obj["id"], payload=obj["error"], is_error=True)

    raise ValueError


# Error: the request is badly formed or cannot be handled
class BadRequestError(JsonRpcError):
    message = "bad request"

    def __init__(self, data):
        super().__init__(code=400, message=self.message, data=data)


# Error: client request references nonexistent server-side method
class NoSuchEndpointError(JsonRpcError):
    message = "no such method exists"

    def __init__(self, method):
        super().__init__(code=404, message=self.message, data=method)


# Error: client request does not exist
class NoSuchRequest(JsonRpcError):
    message = "received response to nonexistent request"

    def __init__(self, data):
        # http 402 is technically [payment required] but these aren't real
        # http errors anyway so lol
        super().__init__(code=402, message=self.message, data=data)


class Disconnected(Exception):
    pass


T = TypeVar("T")


# An [Ivar] is a write-once, concurrent [ref]. Initially, when an ivar is
# created it is "empty", and attempting to [read] from it will block until it
# is [fill]ed from another job.
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


# This class is a jsonrpc layer over transport session
class Session:
    session: transport.Session
    curr_id: RequestId
    # In python 3.11, we can use [asyncio.TaskGroup] for this. However, we will
    # do the bookkeeping ourselves for this assignment for ease of portability.
    pending_jobs: set[asyncio.Task]
    pending_requests: dict[RequestId, Ivar[Response]]
    handlers: dict[str, Callable[..., Coroutine[None, None, Jsonable]]]
    is_running: bool

    # Initialize session
    def __init__(self, session):
        self.curr_id = RequestId(0)
        self.session = session
        self.handlers = dict()
        self.pending_jobs = set()
        self.pending_requests = dict()
        self.is_running = False

    def register_handler(
        self,
        method_name: str,
        action: Callable[..., Coroutine[None, None, Jsonable]],
    ):
        self.handlers[method_name] = action

    # Helper: Run a coroutine in the background
    def run_in_background(self, coro: Coroutine[Any, Any, Any]):
        task = asyncio.create_task(coro)
        self.pending_jobs.add(task)
        # discard this task from pending jobs when done
        task.add_done_callback(self.pending_jobs.discard)

    # Send an error response and catch exception
    async def report_error_nofail(self, error: JsonRpcError) -> None:
        resp = Response(id=None, payload=error, is_error=True)
        try:
            # send the message
            await self.session.send(
                # convert response to string and encode
                resp.serialize().encode(encoding=transport.STRING_ENCODING)
            )
        except Exception:
            # in a real application, we would log here
            return

    # Helper: Handle client request and send response
    async def handle_and_respond(self, req: Request) -> None:
        # if no such requested method, send error
        if req.method not in self.handlers:
            await self.report_error_nofail(NoSuchEndpointError(req.method))
            return
        try:
            # attempt to call method with params and get result
            result = await self.handlers[req.method](*req.params)
            success = True
        except JsonRpcError as e:
            # if get an error, we will return this
            result = e
            success = False

        # Notifications do not expect a response
        if req.is_notification():
            return

        # This [id=req.id] is a bit cheeky. The meaning of [None] in [req.id]
        # is different from [None] in [resp.id], but we know that [req.id]
        # isn't None because of the [req.is_notification] guard above, so we
        # can just satisfy the typechecker without unwrapping.
        resp = Response(id=req.id, payload=result, is_error=not success)

        # send the message
        await self.session.send(
            # convert response to string and encode
            resp.serialize().encode(encoding=transport.STRING_ENCODING)
        )

    # This is the function server uses to handle client requests
    def handle(self, req: Request) -> None:
        self.run_in_background(self.handle_and_respond(req))

    # Calculate fresh request ID for this session
    def fresh_id(self) -> RequestId:
        prev = self.curr_id
        self.curr_id = increment_requestid(self.curr_id)
        return prev

    # This is the function used to send requests
    async def request(self, *, method, params, is_notification=False) -> Response:  # type: ignore[return]
        if not self.is_running:
            raise Disconnected()

        # if notification, no response expected
        if is_notification:
            wait_for_resp = False
            id = None
        else:
            # if will be expecting response, mark request as pending
            wait_for_resp = True
            id = self.fresh_id()
            result_box: Ivar[Response] = Ivar()
            self.pending_requests[id] = result_box

        # create the request, convert it to string, encode, and send
        req = Request(method=method, params=params, id=id)
        await self.session.send(req.serialize().encode(transport.STRING_ENCODING))

        # wait for response, read it, and delete pending request
        if wait_for_resp:
            result = await result_box.read()
            # included only to make mypy accept that [wait_for_resp] implies
            # [id is not None]
            assert id is not None
            del self.pending_requests[id]
            return result

    # Loop to handle all events: client requests and server responses
    async def run_event_loop(self) -> None:
        self.is_running = True
        # use the transport session iterator to receive messages
        async for payload in self.session:
            obj = json.loads(payload)
            if isinstance(obj, dict):
                # if there's a field for method, it's a client request
                if "method" in obj:
                    try:
                        req = parse_request(obj)
                        self.handle(req)
                    except (ValueError, TypeError):
                        self.run_in_background(
                            self.report_error_nofail(BadRequestError(obj))
                        )
                # otherwise, if there's a field for id,
                # it's a response to a request
                elif "id" in obj:
                    try:
                        resp = parse_response(obj)
                    except (ValueError, TypeError):
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
                        self.pending_requests[resp.id].fill(resp)
                else:
                    self.run_in_background(
                        self.report_error_nofail(BadRequestError(obj))
                    )
            else:
                self.run_in_background(self.report_error_nofail(BadRequestError(obj)))

        self.is_running = False

        for job in list(self.pending_jobs):
            job.cancel()


# create a session
def spawn_session(reader, writer) -> Session:
    sess = transport.Session(reader, writer)
    return Session(sess)
