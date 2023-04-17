from dataclasses import dataclass
import json

from common import Host, Port, Address

DEFAULT_CONFIG = "config.json"


@dataclass
class Config:
    servers: list[Address]

    def __contains__(self, server: Address):
        return server in self.servers

    def __getitem__(self, idx: int):
        return self.servers[idx]

    def am_i_primary(self, addr: Address) -> bool:
        host, port = addr
        return self.servers[0] == (host, port)

    def preceding(self, addr: Address) -> list[Address]:
        my_idx = self.servers.index(addr)
        return self.servers[:my_idx]

    def following(self, addr: Address) -> list[Address]:
        my_idx = self.servers.index(addr)
        return self.servers[my_idx + 1 :]


def load(config=DEFAULT_CONFIG) -> Config:
    with open(config, "r") as f:
        data = json.load(f)

    servers = data["servers"]

    # In a real app, we'd do some validation here
    result = Config(
        [(Host(server["host"]), Port(server["port"])) for server in servers]
    )

    return result
