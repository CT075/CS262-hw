
## Sketch

Tentative steps:

- get client-server tutorial working on a single machine
- modify the client and server to meet the assignment specification
- modify to work when client and server are on different machines
- rewrite using gRPC

Base protocol: json-rpc, probably

https://www.jsonrpc.org/

Client request types:

login: string -> session option // returns None if no such user; no authentication for now
create: string -> unit option // returns None if user already exists
list: filter -> string list
send: string * string -> unit option
delete: string -> unit // deletion is idempotent, so client doesn’t need to know if success or failure

Because only one server, can assume that the server sees one linear order of events

Server state: map from usernames -> undelivered messages

Easy to turn requests into json strings, how to get strings across the socket?

Idea 1: read from socket until `NUL` byte

- Bad: memory leak, also what if user sends a message with a `NUL` byte (don't do that?)

Idea 2: Send length of payload, then send payload

- Problem: Length of payload needs to be fixed at n bits, what if payload is bigger than 2^n bytes long

Idea 3: Tag each message with ID

- How to know if message is complete?

Idea 4: Add field to mark whether this is the last packet or not for a given message

- We went with this
- 4 byte ids and 4 byte payload size was picked arbitrarily

```
Client (abstract method call) -> json-rpc (string) -> wire (bytes) -> socket
socket -> wire (bytes) -> json-rpc (string) -> Server (abstract method call)
[and then in reverse for responses]
```

## Testing story

test components individually with a unit testing framework (stdlib `unittest`
seems fine)

run end-to-end tests manually

## Implementation notes

Original plan for transport layer: At initialization time, include a callback
that is called when a message is fully received.

Decided not to because that makes the interface very annoying

Instead, exposed async iterator so consumers can just write `async for message in session`.

## Response types

Python doesn't have a convenient type to send to signal [ok], but luckily there
are no endpoints sending a single string, so we can repurpose the string `"ok"`.

## Server state

Originally planned to have `known_users: set(str)` and `pending_msgs: dict(str, list(str))`

Is actually redundant, can instead keep a single dictionary mapping users to
`LOGGED_IN of session | LOGGED_OUT of pending_messages`

## gRPC

gRPC's model is different from ours, so it will take nontrivial re-architecting
to handle the new style of session management

thoughts: Protobuffers aren't expressive enough to slot into the existing
design; it feels like we are engineering around gRPC implementation details
rather than naturally designing a system from the ground up (see: session
management)

Returning structured errors is difficult with protobuf because it's hard to
attach arbitrary data as a field, so the server must do formatting instead

debugging protobuf code might be up there with the most miserable coding
experiences i've ever had

The code is in fact more complex, and I don't notice any perf differences.

The size of the buffers is smaller because protobuf is a bit-optimized format
vs json strings.
