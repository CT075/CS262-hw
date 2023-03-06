from multiprocessing import Process, Pipe, connection
from os import getpid
from datetime import datetime
import random
from collections import namedtuple
import time

# A message is just a tuple of the local logical clock time,
# the sender logical machine id, and the message ID number
Message = namedtuple("Message", ["localTime", "sender", "id"])


class Clock:
    ctr: int

    def __init__(self):
        self.ctr = 0

    # increment the clock upon event
    def increment(self):
        self.ctr = self.ctr + 1

    # update the clock upon receiving a message
    # TODO: does this work for machines with diff clock rates?
    def msgRecUpdate(self, received_ctr):
        self.ctr = max(received_ctr, self.ctr) + 1


class ModelMachine:
    # number of clock ticks per real world second
    clockRate: int
    # logical clock
    clock: Clock

    # network queue for incoming messages
    queue: list[Message]

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
    # a list of pipes used to send messages to others,
    # and a list of pipes used to receive messages from others
    def __init__(self, lid: int, sendPipes, recvPipes):
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
        self.queue = []
        self.clock = Clock()
        self.msgID = 0

        # create sender and receiver
        self.sender = Process(target=self.runSender, args=sendPipes)
        self.receiver = Process(target=self.runReceiver, args=recvPipes)

    # get next fresh message id
    def freshMsgID(self):
        self.msgID = self.msgID + 1
        return self.msgID

    def locTime(self):
        return self.clock.ctr
    
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
    
    def logSendBoth(self, f, id1, id2):
        f.write(
            "M"
            + str(self.lid)
            + " sent messages to M"
            + str(id1) + " and M"
            + str(id2)
            + ". Global time: "
            + str(datetime.now())
            + ". Logical clock time: "
            + str(self.locTime())
            + ".\n"
        )


    def logReceive(self, f, msg):
        f.write(
            "Received message " 
            + str(msg.id)
            + " from M"
            + str(msg.sender)
            + ". Global time: "
            + str(datetime.now())
            + ". Queue length: "
            + str(len(self.queue))
            + ". Logical clock time: "
            + str(self.locTime())
            + ".\n"
        )

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
    def runReceiver(self, pipe1, pipe2):
        while True:
            if (pipe1.poll()):
                msg = pipe1.recv()
                self.queue.append(msg)
            if (pipe2.poll()):
                msg = pipe2.recv()
                self.queue.append(msg)
            

    def runSender(self, pipe1, pipe2):
        # open log file
        f = open("log" + str(self.lid) + ".txt", "a")

        while True:
            # ensure proper clock rate by sleeping
            time.sleep(1 / self.clockRate)

            # If there is a message in the queue
            if len(self.queue) > 0:
                # Take message off the queue
                msg = self.queue.pop()
                # Update clock
                self.clock.msgRecUpdate(msg.localTime)
                # Log what happened
                self.logReceive(f, msg)
                
            else:
                # generate random number 1-10
                rand = random.randint(1, 10)

                # who are the other machines?
                others = [x for x in [1,2,3] if (x != self.lid)]

                # We assume there are exactly 3 machines in the system
                # as per assignment specification.
                # In a real system, there may be more.
                if rand == 1:
                    # send message to one machine
                    msg = Message(self.locTime(), self.lid, self.freshMsgID())
                    pipe1.send(msg)
                    # increment clock
                    self.clock.increment()
                    # log what happened
                    self.logSend(f, msg.id, others[0])
                    
                elif rand == 2:
                    # send message to other machine
                    msg = Message(self.locTime(), self.lid, self.freshMsgID())
                    pipe2.send(msg)
                    # increment clock
                    self.clock.increment()
                    # log what happened
                    self.logSend(f, msg.id, others[1])
                elif rand == 3:
                    # send message to both machines
                    pipe1.send(
                        Message(self.locTime(), self.lid, self.freshMsgID()))
                    pipe2.send(
                        Message(self.locTime(), self.lid, self.freshMsgID()))
                    # increment clock once -- one atomic action here
                    self.clock.increment()
                    # log what happened
                    self.logSendBoth(f, others[0], others[1])
                else:
                    # internal event, increment clock
                    self.clock.increment()
                    # log what happened
                    self.logInternal(f)


if __name__ == "__main__":
    # create connections
    oneToTwo, twoToOne = Pipe()
    oneToThree, threeToOne = Pipe()
    twoToThree, threeToTwo = Pipe()

    # initialize machines
    m1 = ModelMachine(1, [oneToTwo, oneToThree], [twoToOne, threeToOne])
    m2 = ModelMachine(2, [twoToOne, twoToThree], [oneToTwo, threeToTwo])
    m3 = ModelMachine(3, [threeToOne, threeToTwo], [oneToThree, twoToThree])

    # start all processes
    m1.sender.start()
    m2.sender.start()
    m3.sender.start()

    m1.receiver.start()
    m2.receiver.start()
    m3.receiver.start()

    m1.sender.join()
    m1.receiver.join()
    m2.sender.join()
    m2.receiver.join()
    m3.sender.join()
    m3.receiver.join()