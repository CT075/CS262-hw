# System Design

For persistence, we are choosing to write to a file. Each server will have their own file
keeping track of the state.

For 2-fault tolerance, we settled on a length-3 chain replica setup as shown below,
where C is the client, PS is the primary server, and BS are the backups. We also
number the servers for convenience of discussion.

                        C ----> PS(1) ----> BS(2) ----> BS(3)

We focus on synchronized local correctness and ensure that the client-side understanding
of the state matches the server-side.
To ensure that no messages are dropped and that all servers consistently have the same
worldview as the client, we establish the following ordering of events:

1. Client sends request
2. Primary server forwards the request to backup server (2), and BS(2) forwards the request
to BS(3).
3. Only after we ensure that the backups have written their state, we have PS(1) record its
state. If the primary server dies before the backups are propagated, the client will not be 
under the false impression that the request went through. 

We choose the primary server (leader election) by simply choosing the lowest port number. 
The client chooses the server with the lowest port number to connect to.
We allow servers to have open connections for communication with each other, but since 
the lowest port number is the primary, clients will only connect to the primary.

If the primary server dies, BS(2) becomes the primary. The chain setup with BS(3) remains unchanged.
If BS(3) dies, the primary and the chain setup with PS(1) and BS(2) does not change.
If BS(2) dies, we ensure that PS(1) now connects to BS(3) instead, bypassing the dead backup.

Since we are using asyncio, we do not need to block, as we can simply await for actions to be 
completed.

# Implementation notes

Our original plan was to insert a middleman in the transport layer to forward requests
verbatim to the replicas However, as there are actions that don't necessarily require
an update to persistent state (such as sending a message to a user that is already logged in),
this idea was nixed for bespoke forwarding as required.
