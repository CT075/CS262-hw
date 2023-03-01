from multiprocessing import Process, Pipe, connection
from os import getpid
from datetime import datetime
import random
import logging
from collections import namedtuple
import time

# A message is just a tuple of the local logical clock time
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
    # logger for this machine
    log: logging.Logger

    # Initialize machine
    # takes a logical id of which number machine this is
    def __init__(self, lid: int, pipes: list[connection.Connection], log):
        # Store inputs
        self.lid = lid
        self.log = log

        # init queue and clock
        self.queue = []
        self.clock = Clock()

        # Randomly choose clock rate 1-6
        self.clockRate = random.randint(1, 6)
        
        # create process
        self.process = Process(target=self.run, args = pipes)
        self.process.start()
        self.process.join()
        
        
    # Send message to model machine with logical number id
    def send(self, p: connection.Connection, msg: Message):
        # send the message
        p.send(msg)
        # update local clock
        self.clock.increment()
        # Update log
        self.log.warning("Sent message to model machine " + str(id) +
                          ". Global time: " + str(datetime.now()) +
                          ". Logical clock time: " + str(self.clock.ctr))
        
    def event(self):
        # update local clock
        self.clock.increment()
        # Update log
        # self.log.warning("Local event took place. Global time: " + str(datetime.now()) +
        #                  ". Logical clock time: " + str(self.clock.ctr))


    def run(self, pipe1: connection.Connection, pipe2: connection.Connection):
        self.pid = getpid()

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
                    self.send(pipe1, Message(self.clock.ctr, self.lid))
                elif (rand == 2):
                    # send message to other machine
                    self.send(pipe2, Message(self.clock.ctr, self.lid))
                elif (rand == 3):
                    # send message to both machines
                    self.send(pipe1, Message(self.clock.ctr, self.lid))
                    self.send(pipe2, Message(self.clock.ctr, self.lid))
                else:
                    # internal event
                    self.event()

        
def setup_logger(logger_name, log_file):
    l = logging.getLogger(logger_name)
    logging.basicConfig(level=logging.INFO)
    fileHandler = logging.FileHandler(log_file, mode='w')
    l.addHandler(fileHandler)
    l.info(logger_name + " initialized.")


if __name__ == "__main__":
    # create connections
    oneToTwo, twoToOne = Pipe()
    oneToThree, threeToOne = Pipe()
    twoToThree, threeToTwo = Pipe()

    
    setup_logger("Log1", "log1.txt")
    setup_logger("Log2", "log2.txt")
    setup_logger("Log3", "log3.txt")

    log1 = logging.getLogger("Log1")
    log2 = logging.getLogger("Log2")
    log3 = logging.getLogger("Log3")

    m1 = ModelMachine(1, [oneToTwo, oneToThree], log1)
    m2 = ModelMachine(2, [twoToOne, twoToThree], log2)
    m3 = ModelMachine(3, [threeToOne, threeToTwo], log3)