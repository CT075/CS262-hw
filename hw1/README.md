
# General design notes

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

| Modality         | Name  |
|------------------|-------|
| Client to server | login |

The particular semantics of each procedure are detailed below.
