import asyncio
import json
import random

# Library for writing and reading files

# Read the 3 port numbers for all existing servers 
def read_ports():
    file = open('portnums.txt', 'r')
    ports = [int(x) for x in file.readline().split()]
    return ports

# Generate server port numbers and write to file, 
# return the list for convenience
def write_ports():
    file = open('portnums.txt', 'w')
    ports = random.sample(range(8000, 8999), 3)
    file.write(str(ports[0]) + " " + 
               str(ports[1]) + " " + 
               str(ports[2]) + " ")
    return ports

# writes a single object to file
# we will json.dump the server's known-users dict into this
async def write_obj(filename: str, obj: str):
    # open the file and write object
    with open(filename, "w") as outfile:
        json.dump(obj, outfile)

# reads a single object from file
async def read_obj(filename: str):
    with open(filename, 'r') as openfile:
        return json.load(openfile)