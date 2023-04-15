import asyncio
import json

# Library for writing and reading files

# writes a single object to file
async def write_obj(filename: str, obj: str):
    # open the file and write object
    with open(filename, "w") as outfile:
        json.dump(obj, outfile)

# reads a single object from file
async def read_obj(filename: str):
    with open(filename, 'r') as openfile:
        return json.load(openfile)
    
# TODO: adjust the above so that the file is a json structure
# with multiple objects.
