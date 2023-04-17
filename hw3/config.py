from dataclasses import dataclass
import json
from typing import NewType, Tuple

DEFAULT_CONFIG = "config.json"

Host = NewType("Host", str)
Port = NewType("Port", int)


@dataclass
class Config:
    servers: list[Tuple[Host, Port]]

    def __contains__(self, server: Tuple[Host, Port]):
        return server in self.servers


def load(config=DEFAULT_CONFIG) -> Config:
    with open(config, "r") as f:
        data = json.load(f)

    servers = data["servers"]

    # In a real app, we'd do some validation here
    result = Config(
        [(Host(server["host"]), Port(server["port"])) for server in servers]
    )

    return result
