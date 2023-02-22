import asyncio

import client
import server

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="chat server demo", description="cs262 design 1"
    )
    parser.add_argument("command", choices=["client", "server"])
    parser.add_argument("host")
    parser.add_argument("port")

    args = parser.parse_args()

    if args.command == "client":
        asyncio.run(client.main(args.host, args.port))
    elif args.command == "server":
        asyncio.run(server.main(args.host, args.port))
    else:
        assert False
