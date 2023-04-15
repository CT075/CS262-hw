import asyncio
import client
import server
import argparse
import filelib


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="chat server demo", description="cs262 design 1"
    )
    parser.add_argument("command", choices=["client", "server"])
    parser.add_argument("host")
    # parser.add_argument("port")

    args = parser.parse_args()

    if args.command == "server":
        # Set up three servers with random port #s in a 
        # certain range, and record the ports in a file
        asyncio.run(server.main(args.host, args.port))
    elif args.command == "client":
        # Read the ports from file and pass to client 
        # main, which will connect to the primary
        ports = filelib.read_ports()
        asyncio.run(client.main(args.host, ports))
    else:
        assert False
