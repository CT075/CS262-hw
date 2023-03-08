from multiprocessing import Process, Pipe, connection, Queue
from os import getpid
from datetime import datetime
import random
from collections import namedtuple
import time

# A message is just a tuple of the local logical clock time,
# the sender logical machine id, and the message ID number
Message = namedtuple("Message", ["localTime", "sender", "id"])

# The class representing logical clocks
class Clock:
    ctr: int

    def __init__(self):
        self.ctr = 0

    # increment the clock upon event
    def increment(self):
        self.ctr = self.ctr + 1

    # update the clock upon receiving a message
    def msgRecUpdate(self, received_ctr):
        self.ctr = max(received_ctr, self.ctr) + 1


# The class representing each model machine
class ModelMachine:
    # number of clock ticks per real world second
    clockRate: int
    # logical clock
    clock: Clock

    # network queue for incoming messages
    queue: Queue()
    # another shared queue to communicate queue size
    # since qsize() does not work on some macs
    qsize: Queue()

    # logical machine id: is this m1, m2, or m3?
    lid: int

    # sender process
    sender: Process
    # receiver process
    receiver: Process

    # the next message id
    msgID: int

    # Initialize machine
    # takes a logical id of which number machine this is,
    # and a list of pipes used to send messages to others
    # as well as receive messages
    def __init__(self, lid: int, pipes):
        # Randomly choose clock rate 1-6
        self.clockRate = random.randint(1, 6)

        # Write to log that machine has been initialized
        f = open("log" + str(lid) + ".txt", "w")
        f.write("Started up M" + str(lid) + " with clock rate " + 
                str(self.clockRate) + ".\n")
        f.close()

        # Store inputs
        self.lid = lid

        # init queue and clock
        self.queue = Queue()
        self.qsize = Queue()
        self.clock = Clock()
        self.msgID = 0
        # init size of queue
        self.qsize.put(0)

        # create sender and receiver
        self.sender = Process(
            target=self.runSender, 
            args=[pipes[0], pipes[1], self.queue, self.qsize])
        self.receiver = Process(
            target=self.runReceiver, 
            args=[pipes[0], pipes[1], self.queue, self.qsize])

    # prevent the pickler from pickling 
    # processes inside the ModelMachine object
    # because processes are not picklable
    def __getstate__(self):
        # capture what is normally pickled
        state = self.__dict__.copy()

        # remove unpicklable/problematic variables 
        state['sender'] = None
        state['receiver'] = None
        return state

    # get next fresh message id
    def freshMsgID(self):
        self.msgID = self.msgID + 1
        return self.msgID

    # get current logical clock time
    def locTime(self):
        return self.clock.ctr
    
    # log sent message with msgID and receiver
    def logSend(self, f, msgId, machineId):
        f.write(
            "M"
            + str(self.lid)
            + " sent message " 
            + str(msgId)
            + " to M"
            + str(machineId)
            + ". Global time: "
            + str(datetime.now())
            + ". Logical clock time: "
            + str(self.locTime())
            + ".\n"
        )
    
    # log sent messages with msgIDs and receivers
    def logSendBoth(self, f, msg1, msg2, id1, id2):
        f.write(
            "M"
            + str(self.lid)
            + " sent messages "
            + str(msg1) +
            "," + str(msg2) 
            + " to M"
            + str(id1) + " and M"
            + str(id2)
            + ". Global time: "
            + str(datetime.now())
            + ". Logical clock time: "
            + str(self.locTime())
            + ".\n"
        )

    # log received message and the size of the queue
    def logReceive(self, f, msg, size):
        f.write(
            "Received message " 
            + str(msg.id)
            + " from M"
            + str(msg.sender)
            + ". Global time: "
            + str(datetime.now())
            + ". Queue length: "
            + str(size)
            + ". Logical clock time: "
            + str(self.locTime())
            + ".\n"
        )

    # log internal event
    def logInternal(self, f):
        f.write(
            "Internal event. Global time: "
            + str(datetime.now())
            + ". Logical clock time: "
            + str(self.locTime())
            + ".\n"
        )


    # This process runs in the background
    # listening to both connecting pipes
    # and storing the messages
    def runReceiver(self, pipe1, pipe2, q, qsize):
        while True:
            # check first pipe for messages
            if (pipe1.poll()):
                msg = pipe1.recv()
                q.put(msg)
                oldsize = qsize.get()
                qsize.put(oldsize+1)
            # check second pipe for messages
            if (pipe2.poll()):
                msg = pipe2.recv()
                q.put(msg)
                oldsize = qsize.get()
                qsize.put(oldsize+1)
            

    # This process receives messages, sends messages, 
    # and handles internal events
    def runSender(self, pipe1, pipe2, q, qsize):
        # open log file
        f = open("log" + str(self.lid) + ".txt", "a")

        while True:
            # ensure proper clock rate by sleeping
            time.sleep(1 / self.clockRate)

            # If there is a message in the queue
            if not q.empty():
                # Take message off the queue
                msg = q.get()
                oldsize = qsize.get()
                qsize.put(oldsize-1)
                # Update clock
                self.clock.msgRecUpdate(msg.localTime)
                # Log what happened
                self.logReceive(f, msg, oldsize-1)
                
            else:
                # generate random number 1-10
                rand = random.randint(1,10)

                # who are the other machines?
                others = [x for x in [1,2,3] if (x != self.lid)]

                # We assume there are exactly 3 machines in the system
                # as per assignment specification.
                # In a real system, there may be more.
                if rand == 1:
                    # send message to one machine
                    pipe1.send(
                        Message(self.locTime(), self.lid, self.freshMsgID()))
                    # increment clock
                    self.clock.increment()
                    # log what happened
                    self.logSend(f, self.msgID, others[0])
                    
                elif rand == 2:
                    # send message to other machine
                    pipe2.send(
                        Message(self.locTime(), self.lid, self.freshMsgID()))
                    # increment clock
                    self.clock.increment()
                    # log what happened
                    self.logSend(f, self.msgID, others[1])
                elif rand == 3:
                    # send message to both machines
                    pipe1.send(
                        Message(self.locTime(), self.lid, self.freshMsgID()))
                    pipe2.send(
                        Message(self.locTime(), self.lid, self.freshMsgID()))
                    # increment clock once -- one atomic action here
                    self.clock.increment()
                    # log what happened
                    self.logSendBoth(f, self.msgID-1, self.msgID, others[0], others[1])
                else:
                    # internal event, increment clock
                    self.clock.increment()
                    # log what happened
                    self.logInternal(f)


if __name__ == "__main__":
    # create connection tuples (receive, send)
    twoToOne, oneToTwo = Pipe()
    threeToOne, oneToThree = Pipe()
    threeToTwo, twoToThree = Pipe()

    # initialize machines
    m1 = ModelMachine(1, [oneToTwo, oneToThree])
    m2 = ModelMachine(2, [twoToOne, twoToThree])
    m3 = ModelMachine(3, [threeToOne, threeToTwo])

    # start all processes
    m1.sender.start()
    m2.sender.start()
    m3.sender.start()

    m1.receiver.start()
    m2.receiver.start()
    m3.receiver.start()

    m1.sender.join()
    m2.sender.join()
    m3.sender.join()

    m1.receiver.join()
    m2.receiver.join()
    m3.receiver.join()