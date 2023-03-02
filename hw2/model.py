from multiprocessing import Process, Pipe, connection
from os import getpid
from datetime import datetime
import random
from collections import namedtuple
import time

# A message is just a tuple of the local logical clock time,
# and the sender logical machine id
Message = namedtuple("Message", ["localTime", "sender"])

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


class ModelMachine:
    # number of clock ticks per real world second
    clockRate: int
    # logical clock 
    clock: Clock

    # network queue for incoming messages
    queue: list[Message]

    # logical machine id: is this m1, m2, or m3?
    lid: int
    # process
    process: Process

    # Initialize machine
    # takes a logical id of which number machine this is
    def __init__(self, lid: int, pipes: list[connection.Connection]):
        # Write to log that machine has been initialized
        f = open("log" + str(lid) + ".txt", "w")
        f.write("Started up machine " + str(lid) + ".\n")
        f.close()

        # Store inputs
        self.lid = lid

        # init queue and clock
        self.queue = []
        self.clock = Clock()

        # Randomly choose clock rate 1-6
        self.clockRate = random.randint(1, 6)
        
        # create process
        self.process = Process(target=self.run, args = pipes)
        
        
    # Internal event
    def event(self):
        # update local clock
        self.clock.increment()


    def run(self, pipe1: connection.Connection, pipe2: connection.Connection):
        self.pid = getpid()
        f = open("log" + str(self.lid) + ".txt", "a")

        while(True):
            time.sleep(0.5)
            
            # If there is a message in the queue    
            if (len(self.queue) > 0):
                # Take message off the queue
                msg = self.queue.pop
                # Update clock
                self.clock.msgRecUpdate(msg.localTime)
                # Log what happened
                # logging.info("Received message from model machine " + msg.sender +
                #                 ". Global time: " + str(datetime.now()) + 
                #                 ". Queue length: " + str(len(self.queue)) +
                #                 ". Logical clock time: " + str(self.clock.ctr))
            else:
                # generate random number 1-10
                rand = random.randint(1, 10)
                
                # We assume there are exactly 3 machines in the system
                # as per assignment specification.
                # In a real system, there may be more.
                if (rand == 1):
                    # send message to one machine
                    pipe1.send(Message(self.clock.ctr, self.lid))
                    # increment clock
                    self.clock.increment()
                    # log what happened
                    f.write("Machine " + str(self.lid) + " sent message to model machine " + 
                          ". Global time: " + str(datetime.now()) +
                          ". Logical clock time: " + str(self.clock.ctr) +".\n")
                elif (rand == 2):
                    # send message to other machine
                    pipe2.send(Message(self.clock.ctr, self.lid))
                    # increment clock
                    self.clock.increment()
                    # log what happened
                    f.write("Machine " + str(self.lid) + " sent message to model machine " + 
                          ". Global time: " + str(datetime.now()) +
                          ". Logical clock time: " + str(self.clock.ctr) +".\n")
                elif (rand == 3):
                    # send message to both machines
                    pipe1.send(Message(self.clock.ctr, self.lid))
                    pipe2.send(Message(self.clock.ctr, self.lid))
                    # increment clock once -- one atomic action here
                    self.clock.increment()
                    # log what happened
                    f.write("Machine " + str(self.lid) + " sent message to model machine " +
                          ". Global time: " + str(datetime.now()) +
                          ". Logical clock time: " + str(self.clock.ctr)+".\n")
                else:
                    # internal event
                    # increment clock
                    self.clock.increment()
                    # log what happened



if __name__ == "__main__":
    # create connections
    oneToTwo, twoToOne = Pipe()
    oneToThree, threeToOne = Pipe()
    twoToThree, threeToTwo = Pipe()

    # initialize machines
    m1 = ModelMachine(1, [oneToTwo, oneToThree])
    m2 = ModelMachine(2, [twoToOne, twoToThree])
    m3 = ModelMachine(3, [threeToOne, threeToTwo])

    # start all processes
    m1.process.start()
    m2.process.start()
    m3.process.start()

    m1.process.join()
    m2.process.join()
    m3.process.join()