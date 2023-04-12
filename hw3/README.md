# Running the program

The program can be run via

```bash
# Optional
$ source path/to/virtualenv/bin/activate
$ pip install -r requirements.txt

$ python3 main.py [client|server] [hostname] [port]
```

# General design notes

The system was designed to use async-await-based concurrency, reducing the
need for locks.

## Client architecture

The client is a straightforward CLI wrapper over a series of RPC calls. It
does, however, require registering a handler against the server asynchronously
sending messages from other clients. User list filtering is done client-side.

## Server architecture

The primary state held by the server is the user list, which is implemented as
a mapping from username to `LoggedIn | LoggedOut`, where

- `LoggedIn` holds a reference to that user's session
- `LoggedOut` holds any pending messages sent to that user

Beyond that, individual state (such as the current user associated with a
given login session) is held locally to each job spawned by the default
`asyncio` session manager. In this way, we avoid needing to do, e.g.,
token-based session management. See the RPC endpoints for detailed semantics.

## Protocol

The RPC protocol is [JSON-RPC 2.0](https://www.jsonrpc.org/specification) over
a custom wire protocol.

The wire protocol is implemented in [transport.py](transport.py) and the
JSON-RPC layer is implemented in [jsonrpc.py](jsonrpc.py), with
implementation-specific notes in the comments thereof.

### Wire format

Packets are structured as in the following table. All numeric values are big
endian.

| Index | Length | Description                |
|-------|--------|----------------------------|
| 0     | 4      | Payload size               |
| 4     | 4      | Message ID                 |
| 8     | 1      | More packets with this ID? |
| 9     | var    | Payload                    |

The header always takes eactly 9 bytes, so a packet with an empty payload will
take exactly 9 bytes.

In the case that a message is longer than `2**32` bytes, it should be divided
into maximal-length segments, then sent in order with the relevant
`more packets` entry set.

In theory, the system can fail disastrously if message IDs are not unique. In
a 2-party system, however, a simple incrementing scheme (in which message ids
are incremented after each send) will only fail if a particular message ID is
still pending after `2**32` new messages have been sent, which should not
happen (barring a software bug) without a major network failure.

### JSON-RPC minutiae

JSON strings are encoded via UTF-8 and sent via the above format.

To simplify the implementation, we also enforce the following requirements:

- Requests must have a `params` field containing a list; unitary endpoints
  should be passed an empty list. Keyword arguments are disallowed.
- The `id` field will never contain a NULL value.
- Batch requests are disallowed.

# Endpoints

The client and server expose the following RPC endpoints:

| Modality         | Name          |
|------------------|---------------|
| Client to server | `login`       |
| Client to server | `create_user` |
| Client to server | `list_users`  |
| Client to server | `delete_user` |
| Client to server | `send_msg`    |
| Server to client | `receive_msg` |

The particular semantics of each procedure are detailed below. In all cases,
`User` is equivalent to `string` and `ok` is the literal string `"ok"`. Type
parameters may not correspond precisely to what is sent over the wire.

## `login`

| Parameters       | Response                    |
|------------------|-----------------------------|
| `User`           | `(str, User) list` or error |

Attempt to log in as the given user for this session and return the list of
pending messages. If the user does not exist or this session is already
associated with a user, an error is returned.

Due to the toy nature of this app, we perform no authentication.

## `create_user`

| Parameters     | Response      |
|----------------|---------------|
| `User`         | `ok` or error |

Attempt to create a user. If the user already exists, an error is returned.

## `list_users`

| Parameters | Response    |
|------------|-------------|
| none       | `User` list |

Returns the list of all known users. This cannot fail.

## `delete_user`

| Parameters     | Response      |
|----------------|---------------|
| `User`         | `ok`          |

Delete a user, silently deleting any pending messages as well. If the user does
not exist, silently do nothing.

## `recieve_msg`

| Parameters     | Response   |
|----------------|------------|
| `(str, User)`  | `ok`       |

The server invokes this client-side method when the user associated with that
client's login session receives a message. It should not fail.
